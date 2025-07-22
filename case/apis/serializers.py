from venv import logger
import ast

from Tools.scripts.generate_token import update_file
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
import os

from icecream import ic
from rest_framework.generics import get_object_or_404
from dynamicflow.models import Field
from dynamicflow.services.api_trigger_service import APITriggerService

from case.models import Case, MapperExecutionLog, MapperFieldRule, MapperTarget, CaseMapper, ApprovalRecord
from conditional_approval.apis.serializers import NoteSerializer, ActionBasicSerializer
from conditional_approval.models import ApprovalStep, Action, ActionStep # Ensure ActionStep is imported
from dynamicflow.utils.dynamicflow_helper import DynamicFlowHelper
from dynamicflow.utils.dynamicflow_validator_helper import DynamicFlowValidator
from urllib.parse import unquote
from rest_framework import serializers
from lookup.models import Lookup
from django.core.files.storage import default_storage


class LightActionStepSerializer(serializers.ModelSerializer):
    action_name = serializers.CharField(source='action.name', read_only=True)
    action_code = serializers.CharField(source='action.code', read_only=True)
    to_status_name = serializers.CharField(source='to_status.name', read_only=True)
    sub_status_name = serializers.CharField(source='sub_status.name', read_only=True)
    notes_mandatory = serializers.BooleanField(source='action.notes_mandatory', read_only=True)

    class Meta:
        model = ActionStep
        fields = [
            'id', 'action_name', 'action_code', 'to_status_name',
            'sub_status_name', 'notes_mandatory'
        ]


class CaseSerializer(serializers.ModelSerializer):
    applicant = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False, allow_null=True)
    applicant_type = serializers.PrimaryKeyRelatedField(
        queryset=Lookup.objects.filter(parent_lookup__name='Applicant Type'))
    case_type = serializers.PrimaryKeyRelatedField(
        queryset=Lookup.objects.filter(parent_lookup__name='Service'))
    status = serializers.PrimaryKeyRelatedField(
        queryset=Lookup.objects.filter(parent_lookup__name='Case Status'),
        required=False, allow_null=True)
    sub_status = serializers.PrimaryKeyRelatedField(
        queryset=Lookup.objects.filter(
            parent_lookup__name='Case Sub Status'), required=False, allow_null=True)
    assigned_group = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), required=False, allow_null=True)
    assigned_emp = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False, allow_null=True)
    current_approval_step = serializers.PrimaryKeyRelatedField(
        queryset=ApprovalStep.objects.all(), required=False, allow_null=True)
    last_action = serializers.PrimaryKeyRelatedField(
        queryset=Action.objects.all(), required=False, allow_null=True)
    created_by = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False, allow_null=True)
    updated_by = serializers.PrimaryKeyRelatedField(
        queryset=get_user_model().objects.all(), required=False, allow_null=True)

    files = serializers.ListField(child=serializers.FileField(),
                                  write_only=True, required=False)
    file_types = serializers.ListField(child=serializers.CharField(),
                                       write_only=True, required=False)
    # This will handle JSON data properly
    case_data = serializers.JSONField(required=False)
    notes = NoteSerializer(many=True, read_only=True)

    available_applicant_actions = serializers.SerializerMethodField()

    class Meta:
        model = Case
        fields = '__all__'
        read_only_fields = (
            'applicant', 'status', 'sub_status', 'assigned_group',
            'serial_number', 'created_at', 'updated_at', 'created_by',
            'assigned_emp', 'last_action', 'current_approval_step', 'updated_by',
            'available_applicant_actions')

    def get_available_applicant_actions(self, obj):
        """
        Determines the actions an applicant can take on their own case.
        Only shows actions that are specifically meant for applicants.
        """
        available_actions_list = []

        # Get the current user from the serializer context
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return []

        user = request.user

        # IMPORTANT: Only the case owner (applicant) can see/take actions
        if obj.applicant != user:
            return []

        # If there's no current approval step, no actions are available
        if not obj.current_approval_step:
            return []

        approval_step = obj.current_approval_step
        user_groups = user.groups.all()

        # Check if the user has already taken an action at this step
        existing_action = ApprovalRecord.objects.filter(
            case=obj,
            approval_step=approval_step,
            approved_by=user
        ).first()

        # If user already took an action at this step, no more actions available
        if existing_action:
            return []

        # Get action steps available at the current approval step
        action_steps = approval_step.actions.filter(
            active_ind=True,
            action__active_ind=True,
        ).select_related('action', 'to_status', 'sub_status')

        for step in action_steps:
            action = step.action
            if not action:
                continue

            # Check if the action is meant for applicants
            # This checks if the action's groups include any of the user's groups
            # Typically, applicant actions would be assigned to a "Public User" or "Applicant" group
            action_groups = action.groups.all()

            # If no groups are specified, skip (this is likely an employee-only action)
            # Or if the action has groups, check if user has any of those groups
            if action_groups.exists():
                if action_groups.intersection(user_groups).exists():
                    # Add the action with additional metadata
                    action_data = ActionBasicSerializer(action).data
                    action_data['action_step_id'] = step.id
                    action_data['to_status'] = step.to_status.name if step.to_status else None
                    action_data['sub_status'] = step.sub_status.name if step.sub_status else None
                    available_actions_list.append(action_data)

        return available_actions_list

    def validate(self, data):
        # Retrieve service flow dynamically (adjust based on your query fetching logic)
        query = [data["case_type"].code]
        service_flow = DynamicFlowHelper(query).get_flow()

        # case_obj = get_object_or_404(Case, pk=self.instance.pk)
        case_obj = Case.objects.filter(pk=self.instance.pk).first() if self.instance else None

        # Initialize and apply the validator
        # Pass the service flow to the validator
        validator = DynamicFlowValidator(service_flow, case_obj, data)
        # Perform the full validation
        validation_results = validator.validate()

        # Add validation results to the validated data
        data["is_valid"] = validation_results["is_valid"]
        data["extra_keys"] = validation_results["extra_keys"]
        data["missing_keys"] = validation_results["missing_keys"]
        data["field_errors"] = validation_results["field_errors"]

        if not validation_results["is_valid"]:
            raise serializers.ValidationError(
                {"errors": validation_results["field_errors"]})

        return data

    def remove_invalid_data(self, validated_data, case_data=None):
        for key in validated_data["extra_keys"]:
            self.validated_data["case_data"].pop(key, None)
            if case_data:
                case_data.pop(key, None)
        return validated_data

    def validate_file_types(self, file_types):
        """
        Validate that each file type corresponds to a valid document type from Lookup.
        """
        valid_document_types = Lookup.objects.filter(
            parent_lookup__name='Document Type')
        valid_codes = valid_document_types.values_list(
            'code', flat=True)

        for file_type in file_types:
            if file_type not in valid_codes:
                raise serializers.ValidationError(
                    f"'{file_type}' is not a valid document type.")
        return file_types

    def rename_files(self, created_case, case_data, datetime_str):
        # Now, update the file names with the actual serial_number
        if created_case.serial_number != 'unknown_case_number':
            # Loop through the uploaded files
            # and rename them with the actual serial number
            for file_entry in case_data.get('uploaded_files', []):
                old_url = file_entry['file_url']
                # Extract the file name from the URL
                old_file_name = os.path.basename(old_url)
                # Ensure old file path is relative to 'uploads/'
                old_file_path = os.path.join('uploads', old_file_name)

                # Capture the original file name (before upload)
                # Get the part after case type and serial number
                original_file_name = (
                    old_file_name.split('-', 2))[-1]

                # Generate the new file name with the
                # actual serial number and original file name
                new_file_name = (f"{created_case.case_type.code}_"
                                 f"{created_case.serial_number}-"
                                 f"{datetime_str}_{original_file_name}")
                new_file_path = os.path.join(
                    'uploads', new_file_name)  # New path relative to 'uploads/'

                # Check if the file exists before renaming
                if default_storage.exists(old_file_path):
                    # Copy the file to the new location
                    with default_storage.open(old_file_path, 'rb') as old_file:
                        default_storage.save(new_file_path, old_file)

                    # Delete the old file
                    default_storage.delete(old_file_path)

                    # Update the file entry with the new URL
                    new_file_url = default_storage.url(new_file_path)
                    file_entry['file_url'] = new_file_url

            # Update case data with the new file URLs
            if "uploaded_files" in case_data:
                created_case.case_data['uploaded_files'] = case_data['uploaded_files']
            created_case.save()  # Save the case again with updated file URLs
        return created_case

    def create_file_entries_handler(self, files, file_types, validated_data, datetime_str):
        # Process files and their types together
        file_entries = []

        for file_obj, file_type in zip(files, file_types):
            # Ensure the file type corresponds to a valid Lookup entry
            document_type = Lookup.objects.get(
                parent_lookup__name='Document Type', code=file_type)

            # Retrieve case type and serial number
            case_type = validated_data.get('case_type')
            case_number = validated_data.get('serial_number', 'unknown_case_number')


            # Capture the original file name (before upload) for each file
            # This is the original file name from the device
            original_file_name = file_obj.name

            # Generate the custom file name
            # format using the original file name
            file_extension = file_obj.name.split(
                '.')[-1]  # Extract file extension
            if case_number == 'unknown_case_number':
                # Use the case type and timestamp for
                # the file name if the case number is unknown
                new_file_name = f"{case_type.code}-{datetime_str}_{original_file_name}"
            else:
                # Use the case type, serial number, and timestamp for the file name
                new_file_name = (f"{case_type.code}_{case_number}-"
                                 f"{datetime_str}_{original_file_name}")

            # Ensure the final file name is unique by checking if it already exists
            file_path = os.path.join('uploads', new_file_name)
            file_name = file_path
            counter = 1
            while default_storage.exists(file_name):
                # Append a suffix to make the file name unique if needed
                file_name = file_path.replace(
                    f'.{file_extension}',
                    f'_{counter}.{file_extension}')
                counter += 1

            # Save the file with the unique name
            file_name = default_storage.save(file_name, file_obj)
            file_url = default_storage.url(file_name)

            file_entries.append({
                'file_url': file_url,
                # Use the name or any field you want from the Lookup model
                'type': document_type.name
            })
        return file_entries

    def update_file_entries_handler(self, files,
                                    file_types,
                                    validated_data,
                                    existing_files,
                                    instance,
                                    case_data,
                                    datetime_str):
        updated_files = []
        case_type = validated_data.get('case_type', instance.case_type)
        case_number = instance.serial_number

        for file_obj, file_type in zip(files, file_types):
            document_type = Lookup.objects.get(
                parent_lookup__name='Document Type', code=file_type)
            original_file_name = file_obj.name

            # file_extension = file_obj.name.split('.')[-1]
            new_file_name = (
                f"{case_type.code}_{case_number}-{datetime_str}_"
                f"{original_file_name}"
            )

            file_path = os.path.join('uploads', new_file_name)
            file_name = default_storage.save(file_path, file_obj)
            file_url = default_storage.url(file_name)
            for existing_file in existing_files:
                old_url = existing_file['file_url']
                old_file_name = os.path.basename(old_url)
                decoded_file_name = unquote(old_file_name)
                old_file_path = os.path.join('uploads', decoded_file_name)

                file_prefix = f"{case_type.code}_{case_number}"

                if decoded_file_name.startswith(
                        file_prefix
                ) and existing_file['type'] == document_type.name:
                    try:
                        if default_storage.exists(old_file_path):
                            logger.debug(f"Deleting file: {old_file_path}")
                            default_storage.delete(old_file_path)

                            # Remove the old entry from existing_files
                            case_data['uploaded_files'].remove(existing_file)
                    except Exception as e:
                        logger.error(f"Error deleting file {old_file_path}: {e}")
            updated_files.append({
                'file_url': file_url,
                'type': document_type.name
            })
        return updated_files


    def create(self, validated_data):
        ic(validated_data)
        validated_data = self.remove_invalid_data(validated_data)

        if not validated_data.get("is_valid", False):
            raise serializers.ValidationError(
                {"error": validated_data.get("field_errors", "Unknown error")})

        files = validated_data.pop('files', [])
        file_types = validated_data.pop('file_types', [])

        user = self.context['request'].user
        validated_data['created_by'] = user
        validated_data['updated_by'] = user
        validated_data['applicant'] = user
        validated_data['status'] = Lookup.objects.get(
            parent_lookup__name='Case Status', name='Draft')
        validated_data['assigned_group'] = Group.objects.filter(
            name='Public User').first()
        approval_step = ApprovalStep.objects.filter(
            service_type=Lookup.objects.filter(
                parent_lookup__name='Service').first()).order_by('seq').first()
        validated_data['current_approval_step'] = approval_step

        logger.debug(f"Files received: {files}")
        logger.debug(f"File types received: {file_types}")

        # Handle case_data JSON field
        case_data = validated_data.get('case_data', {})
        # Retrieve the current datetime in the desired format
        datetime_str = timezone.now().strftime('%Y-%m-%d_%H-%M-%S')
        file_entries = self.create_file_entries_handler(files, file_types, validated_data, datetime_str)
        if file_entries:
            case_data['uploaded_files'] = file_entries

        validated_data['case_data'] = case_data

        # ====== ADD THIS SECTION: Pre-save API Calls ======
        # Fetch fields that have API calls configured AND are present in case_data
        fields_with_api_calls = Field.objects.filter(
            _api_call_config__isnull=False,
            _field_name__in=case_data.keys()  # Only fields present in case_data
        ).exclude(_api_call_config=[])

        for field in fields_with_api_calls:
            APITriggerService.trigger_api_calls(
                field=field,
                event="pre_save",
                case_data=case_data,
                instance=None  # No instance yet for create
            )
        # ====== END OF PRE-SAVE API CALLS ======

        # Custom handling of the create method
        # where we don't pass `is_valid`, `missing_keys`, etc.
        # Remove invalid fields that are not part of the model
        valid_fields = [field.name for field in Case._meta.fields]
        validated_data = {
            key: value
            for key, value in validated_data.items()
            if key in valid_fields
        }

        created_case = super(CaseSerializer, self).create(validated_data)

        # ====== ADD THIS SECTION: Post-save API Calls ======
        for field in fields_with_api_calls:
            APITriggerService.trigger_api_calls(
                field=field,
                event="post_save",
                case_data=created_case.case_data,
                instance=created_case
            )
        # ====== END OF POST-SAVE API CALLS ======

        created_case = self.rename_files(created_case, case_data, datetime_str)
        return created_case

    def update(self, instance, validated_data):
        print("validated_data")
        ic(validated_data)

        # ====== ADD THIS LINE: Store old data for 'on_change' triggers ======
        old_case_data = instance.case_data.copy() if instance.case_data else {}
        # ====== END ======

        case_data = instance.case_data or {}
        validated_data = self.remove_invalid_data(validated_data, case_data)
        ic(validated_data)
        # Perform the validation before processing the data
        validation_results = self.validate(validated_data)
        ic(validation_results)
        if not validation_results["is_valid"]:
            raise serializers.ValidationError(validation_results["field_errors"])

        files = validated_data.pop('files', [])
        file_types = validated_data.pop('file_types', [])
        keys_to_remove_str = self.context['request'].data.get('keys_to_remove', [])
        keys_to_remove = ast.literal_eval(
            keys_to_remove_str) if keys_to_remove_str else []

        user = self.context['request'].user
        validated_data['updated_by'] = user

        # ====== ADD THIS SECTION: Get new case_data and Pre-save API Calls ======
        # Get the new case_data that will be saved
        new_case_data = validated_data.get('case_data', {})

        # Pre-save API Calls
        fields_with_api_calls = Field.objects.filter(
            _api_call_config__isnull=False,
            _field_name__in=list(old_case_data.keys()) + list(new_case_data.keys())
        ).exclude(_api_call_config=[])

        for field in fields_with_api_calls:
            APITriggerService.trigger_api_calls(
                field=field,
                event="pre_save",
                case_data=new_case_data,
                instance=instance,
                old_case_data=old_case_data
            )
        # ====== END OF PRE-SAVE API CALLS ======

        # Handle case_data JSON field
        updated_files = []
        # ... rest of your existing code for file handling ...

        # ... existing code continues until instance.save() ...

        instance.save()

        # ====== ADD THIS SECTION: On-change and Post-save API Calls ======
        # On-change API Calls
        for field in fields_with_api_calls:
            field_name = field._field_name
            old_value = old_case_data.get(field_name)
            new_value = instance.case_data.get(field_name)

            if old_value != new_value:
                APITriggerService.trigger_on_change_for_field(
                    field=field,
                    old_value=old_value,
                    new_value=new_value,
                    full_old_data=old_case_data,
                    full_new_data=instance.case_data,
                    instance=instance
                )

        # Post-save API Calls
        for field in fields_with_api_calls:
            APITriggerService.trigger_api_calls(
                field=field,
                event="post_save",
                case_data=instance.case_data,
                instance=instance,
                old_case_data=old_case_data
            )
        # ====== END OF API CALLS ======

        logger.debug(
            f"Updated case with ID {instance.id}"
            f", files: {case_data.get('uploaded_files', [])}")
        return instance

class ApprovalRecordSerializer(serializers.ModelSerializer):
    action_notes = NoteSerializer(many=True, read_only=True)

    class Meta:
        model = ApprovalRecord
        fields = [
            'id',
            'case',
            'approval_step',
            'action_taken',
            'approved_by',
            'approved_at',
            'action_notes'
        ]
        read_only_fields = ['id', 'approved_at']

class MapperExecutionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapperExecutionLog
        fields = '__all__'

class RunMapperInputSerializer(serializers.Serializer):
    case_id = serializers.IntegerField()
    mapper_target_id = serializers.IntegerField()

class DryRunMapperInputSerializer(serializers.Serializer):
    case_id = serializers.IntegerField()
    mapper_target_id = serializers.IntegerField()


class MapperFieldRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MapperFieldRule
        fields = '__all__'

class MapperTargetSerializer(serializers.ModelSerializer):
    field_rules = MapperFieldRuleSerializer(many=True, read_only=True)

    class Meta:
        model = MapperTarget
        fields = '__all__'

class CaseMapperSerializer(serializers.ModelSerializer):
    targets = MapperTargetSerializer(many=True, read_only=True)

    class Meta:
        model = CaseMapper
        fields = '__all__'


class ApplicantActionInputSerializer(serializers.Serializer):
    action_id = serializers.IntegerField(
        help_text="Code of the action to be performed (e.g., 'PAY', 'UPLOAD_DOCS')"
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional notes for the action"
    )

    def validate(self, data):
        # Basic validation: ensure action_code is not empty
        if not data.get('action_id'):
            raise serializers.ValidationError("Action code is required.")
        return data
