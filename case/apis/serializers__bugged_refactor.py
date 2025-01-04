from venv import logger
import ast
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
import os

from icecream import ic
from rest_framework.generics import get_object_or_404

from case.models import Case
from conditional_approval.models import ApprovalStep, Action
from dynamicflow.utils.dynamicflow_helper import DynamicFlowHelper
from dynamicflow.utils.dynamicflow_validator_helper import DynamicFlowValidator
from urllib.parse import unquote
from rest_framework import serializers
from lookup.models import Lookup
from django.core.files.storage import default_storage


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
    case_data = serializers.JSONField(required=False)

    class Meta:
        model = Case
        fields = '__all__'
        read_only_fields = (
            'applicant', 'status', 'sub_status', 'assigned_group',
            'serial_number', 'created_at', 'updated_at', 'created_by',
            'assigned_emp', 'last_action', 'current_approval_step', 'updated_by')

    def validate(self, data):
        query = [data["case_type"].code]
        service_flow = DynamicFlowHelper(query).get_flow()

        case_obj = Case.objects.filter(pk=self.instance.pk).first() if self.instance else None

        validator = DynamicFlowValidator(service_flow, case_obj, data)
        validation_results = validator.validate()

        data["is_valid"] = validation_results["is_valid"]
        data["extra_keys"] = validation_results["extra_keys"]
        data["missing_keys"] = validation_results["missing_keys"]
        data["field_errors"] = validation_results["field_errors"]

        if not validation_results["is_valid"]:
            raise serializers.ValidationError({"errors": validation_results["field_errors"]})

        return data

    def remove_invalid_data(self, validated_data):
        for key in validated_data["extra_keys"]:
            validated_data["case_data"].pop(key, None)
        return validated_data

    def handle_files(self, files, file_types, case_type_code, case_number):
        """
        Handle file uploads, generate unique names, and save them.
        """
        datetime_str = timezone.now().strftime('%Y-%m-%d_%H-%M-%S')
        file_entries = []

        for file_obj, file_type in zip(files, file_types):
            document_type = Lookup.objects.get(
                parent_lookup__name='Document Type', code=file_type)

            original_file_name = file_obj.name
            new_file_name = (f"{case_type_code}_{case_number}-"
                             f"{datetime_str}_{original_file_name}")
            file_path = os.path.join('uploads', new_file_name)
            file_name = default_storage.save(file_path, file_obj)
            file_url = default_storage.url(file_name)

            file_entries.append({
                'file_url': file_url,
                'type': document_type.name
            })

        return file_entries

    def delete_old_files(self, case_data, case_type_code, case_number, document_type_name):
        """
        Delete old files matching the case type and number.
        """
        existing_files = case_data.get('uploaded_files', [])
        updated_files = []

        for existing_file in existing_files:
            old_url = existing_file['file_url']
            old_file_name = os.path.basename(old_url)
            decoded_file_name = unquote(old_file_name)
            old_file_path = os.path.join('uploads', decoded_file_name)

            file_prefix = f"{case_type_code}_{case_number}"

            if decoded_file_name.startswith(file_prefix) and existing_file['type'] == document_type_name:
                if default_storage.exists(old_file_path):
                    default_storage.delete(old_file_path)
            else:
                updated_files.append(existing_file)

        return updated_files

    def create(self, validated_data):
        validated_data = self.remove_invalid_data(validated_data)

        if not validated_data.get("is_valid", False):
            raise serializers.ValidationError({"error": validated_data.get("field_errors", "Unknown error")})

        files = validated_data.pop('files', [])
        file_types = validated_data.pop('file_types', [])

        user = self.context['request'].user
        validated_data.update({
            'created_by': user,
            'updated_by': user,
            'applicant': user,
            'status': Lookup.objects.get(parent_lookup__name='Case Status', name='Draft'),
            'assigned_group': Group.objects.filter(name='Public User').first(),
            'current_approval_step': ApprovalStep.objects.filter(service_type=validated_data['case_type']).order_by('seq').first()
        })

        case_number = validated_data.get('serial_number', 'unknown_case_number')
        case_type_code = validated_data['case_type'].code

        file_entries = self.handle_files(files, file_types, case_type_code, case_number)

        if file_entries:
            validated_data.setdefault('case_data', {})['uploaded_files'] = file_entries

        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data = self.remove_invalid_data(validated_data)

        if not validated_data.get("is_valid", False):
            raise serializers.ValidationError(validated_data.get("field_errors", "Unknown error"))

        files = validated_data.pop('files', [])
        file_types = validated_data.pop('file_types', [])
        keys_to_remove_str = self.context['request'].data.get('keys_to_remove', [])
        keys_to_remove = ast.literal_eval(keys_to_remove_str) if keys_to_remove_str else []

        user = self.context['request'].user
        validated_data['updated_by'] = user

        case_data = instance.case_data or {}

        case_number = instance.serial_number
        case_type_code = validated_data.get('case_type', instance.case_type).code

        for file_obj, file_type in zip(files, file_types):
            document_type = Lookup.objects.get(parent_lookup__name='Document Type', code=file_type)
            updated_files = self.delete_old_files(case_data, case_type_code, case_number, document_type.name)
            new_file_entries = self.handle_files([file_obj], [file_type], case_type_code, case_number)
            updated_files.extend(new_file_entries)
            case_data['uploaded_files'] = updated_files

        for key in keys_to_remove:
            case_data.pop(key, None)

        instance.case_data = case_data

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
