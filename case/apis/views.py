import json

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, views, generics
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from case.models import Case, ApprovalRecord, MapperTarget, MapperExecutionLog, CaseMapper, MapperFieldRule, Note
from conditional_approval.apis.serializers import ActionBasicSerializer, NoteSerializer
from conditional_approval.models import Action, ApprovalStep, ActionStep, ParallelApprovalGroup
from dynamicflow.models import Field
from dynamicflow.services.api_trigger_service import APITriggerService
from dynamicflow.utils.dynamicflow_validator_helper import DynamicFlowValidator
from lookup.models import Lookup
from utils.conditional_approval import evaluate_conditions
from dynamicflow.utils.dynamicflow_helper import DynamicFlowHelper
from .serializers import CaseSerializer, RunMapperInputSerializer, DryRunMapperInputSerializer, \
    MapperExecutionLogSerializer, CaseMapperSerializer, MapperTargetSerializer, MapperFieldRuleSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action

from ..plugins.default_plugin import process_records, dry_run


class CaseViewSet(viewsets.ModelViewSet):
    queryset = Case.objects.all()
    serializer_class = CaseSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]  # Enable file upload parsers

    def get_queryset(self):
        """
        Optionally restrict the returned cases to the current user.
        """
        queryset = Case.objects.all().order_by("created_at")
        user = self.request.user
        # You can modify this to filter by the current user or based on other conditions
        return queryset.filter(applicant=user)  # Showcases only for the logged-in user

    @action(detail=True, methods=['get'])
    def serial_number(self, request):
        """
        Custom action to get the serial number of a specific case.
        """
        case = self.get_object()
        return Response({'serial_number': case.serial_number})


class SubmitApplication(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, *args, **kwargs):
        # Fetch case object and verify user ownership
        case_obj = get_object_or_404(Case, pk=kwargs["pk"])

        if request.user != case_obj.applicant:
            return Response(
                {
                    "detail": "You don't have permission to perform this action",
                    "detail_ara": "ليس لديك الصلاحية لتنفيذ هذا الأمر"
                },
                status=status.HTTP_403_FORBIDDEN
            )

        # Get the stored case data
        stored_case_data = case_obj.case_data or {}

        # Get the request body data (if any)
        request_body = request.data.get('case_data', {})

        # Handle stringified JSON
        if isinstance(request_body, str):
            try:
                request_body = json.loads(request_body)
            except json.JSONDecodeError:
                return Response(
                    {
                        "detail": "'case_data' string could not be parsed as valid JSON.",
                        "received_type": str(type(request_body))
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Ensure it's now a dict
        if not isinstance(request_body, dict):
            return Response(
                {
                    "detail": "'case_data' must be a dictionary.",
                    "received_type": str(type(request_body))
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Merge stored case data with request body (override stored values with request body values)
        merged_data = stored_case_data.copy()
        print("under copy")
        merged_data.update(request_body)

        # Retrieve service flow dynamically using the case type
        query = [case_obj.case_type.code]
        service_flow = DynamicFlowHelper(query).get_flow()

        # Initialize and apply the validator
        validator = DynamicFlowValidator(service_flow, case_obj, request_body, submit=True)
        validation_results = validator.validate()

        if not validation_results["is_valid"]:
            return Response(
                {
                    "detail": "Validation failed.",
                    "errors": validation_results["field_errors"],
                    "missing_keys": validation_results["missing_keys"],
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch the Submit action
        submit_action = Action.objects.filter(name="Submit").first()
        if not submit_action:
            return Response(
                {"detail": "Submit action not found."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch the corresponding approval step
        approval_step = ApprovalStep.objects.filter(
            service_type=case_obj.case_type,
            group=case_obj.assigned_group
        ).first()

        if not approval_step:
            return Response(
                {"detail": "No valid approval step found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get the next action step based on the submit action
        next_step = ActionStep.objects.filter(
            approval_step=approval_step,
            action=submit_action
        ).first()

        if not next_step:
            return Response(
                {"detail": "No action step found for the submit action."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Dynamically fetch the "Submitted" case status from the Lookup model
        case_status = Lookup.objects.filter(
            parent_lookup__name='Case Status',
            name='Submitted'
        ).first()
        if not case_status:
            return Response(
                {"detail": "Submitted status not found in Lookup model"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update the case status and assigned group
        case_obj.status = case_status
        next_approval_step = ApprovalStep.objects.filter(
            service_type=case_obj.case_type,
            status=next_step.to_status
        ).first()

        if not next_approval_step:
            return Response(
                {"detail": "Next approval step not found for the given status."},
                status=status.HTTP_400_BAD_REQUEST
            )

        case_obj.assigned_group = next_approval_step.group
        case_obj.last_action = submit_action
        case_obj.current_approval_step = next_approval_step

        # Save the case object with updated details
        case_obj.save()

        return Response({"detail": "Success"}, status=status.HTTP_200_OK)


class TriggerFieldAPIView(APIView):
    """
    Enhanced endpoint for frontend to trigger field API calls.
    Now supports URL path parameters.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """
        Trigger integrations for a specific field.

        Expected payload:
        {
            "case_id": 123,
            "field_id": 456,
            "field_value": "new value",
            "old_value": "old value",  // optional, for on_change
            "case_data": {...},  // current form data
            "trigger_event": "on_change"  // optional, defaults to on_change
        }
        """
        case_id = request.data.get('case_id')
        field_id = request.data.get('field_id')
        field_value = request.data.get('field_value')
        old_value = request.data.get('old_value')
        case_data = request.data.get('case_data', {})
        trigger_event = request.data.get('trigger_event', 'on_change')

        # Validate required fields
        if not all([case_id, field_id]):
            return Response(
                {"error": "case_id and field_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            case = Case.objects.get(id=case_id)
            field = Field.objects.get(id=field_id)

            # Ensure the field value is in case_data
            if field._field_name not in case_data:
                case_data[field._field_name] = field_value

            # Get integrations for this field and event
            integrations = field.field_integrations.filter(
                trigger_event=trigger_event,
                active=True
            ).order_by('order')

            if not integrations.exists():
                return Response({
                    "status": "success",
                    "message": "No integrations configured for this field and event",
                    "integrations_executed": 0
                })

            # Execute integrations
            executed = []
            failed = []

            with transaction.atomic():
                for field_integration in integrations:
                    try:
                        # Check if integration should execute
                        if not field_integration.should_execute(field_value, case_data):
                            continue

                        # Prepare request data including path parameters
                        payload, query_params, headers, path_params = field_integration.prepare_request_data(
                            case_data, field_value
                        )

                        # Execute the integration
                        if field_integration.is_async:
                            from dynamicflow.services.api_trigger_service import APITriggerService
                            APITriggerService._execute_integration_async.delay(
                                field_integration.id,
                                payload,
                                query_params,
                                headers,
                                path_params,  # Include path params
                                case.id,
                                case_data
                            )
                            executed.append({
                                "integration": field_integration.integration.name,
                                "status": "scheduled",
                                "async": True
                            })
                        else:
                            # Synchronous execution
                            response = field_integration.integration.make_api_request(
                                body=payload,
                                query_params=query_params,
                                headers=headers,
                                path_params=path_params  # Include path params
                            )

                            # Handle response updates if configured
                            response_data = {}
                            if field_integration.update_field_on_response:
                                # Extract value from response
                                if field_integration.response_field_path:
                                    from jsonpath_ng import parse
                                    jsonpath_expr = parse(field_integration.response_field_path)
                                    matches = jsonpath_expr.find(response)
                                    if matches:
                                        response_data['field_value'] = matches[0].value

                                # Extract additional mapped fields
                                response_data['mapped_fields'] = {}
                                for resp_path, case_field in field_integration.response_field_mapping.items():
                                    jsonpath_expr = parse(f"$.{resp_path}")
                                    matches = jsonpath_expr.find(response)
                                    if matches:
                                        response_data['mapped_fields'][case_field] = matches[0].value

                            executed.append({
                                "integration": field_integration.integration.name,
                                "status": "success",
                                "response_data": response_data,
                                "url_called": field_integration.integration.build_url(path_params) if path_params else field_integration.integration.endpoint
                            })

                    except Exception as e:
                        failed.append({
                            "integration": field_integration.integration.name,
                            "error": str(e)
                        })

            return Response({
                "status": "success",
                "integrations_executed": len(executed),
                "integrations_failed": len(failed),
                "executed": executed,
                "failed": failed
            })

        except Case.DoesNotExist:
            return Response(
                {"error": "Case not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Field.DoesNotExist:
            return Response(
                {"error": "Field not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class FieldIntegrationsListView(APIView):
    """
    Get all integrations configured for a specific field.
    Useful for frontend to know what integrations are available.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, field_id):
        try:
            field = Field.objects.get(id=field_id)
            integrations = field.field_integrations.filter(
                active=True
            ).select_related('integration')

            data = []
            for fi in integrations:
                data.append({
                    'id': fi.id,
                    'integration': {
                        'id': fi.integration.id,
                        'name': fi.integration.name,
                        'endpoint': fi.integration.endpoint,
                        'method': fi.integration.method
                    },
                    'trigger_event': fi.trigger_event,
                    'is_async': fi.is_async,
                    'condition_expression': fi.condition_expression,
                    'update_field_on_response': fi.update_field_on_response,
                    'response_field_path': fi.response_field_path
                })

            return Response({
                'field': {
                    'id': field.id,
                    'name': field._field_name,
                    'display_name': field._field_display_name
                },
                'integrations': data
            })

        except Field.DoesNotExist:
            return Response(
                {"error": "Field not found"},
                status=status.HTTP_404_NOT_FOUND
            )

class EmployeeCasesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_groups = user.groups.all()

        # -------- My Cases (assigned to me OR parallel approval cases I can act on) --------
        # Only include unassigned cases if they are parallel approval cases
        my_cases_query = Case.objects.filter(
            Q(assigned_emp=user) |  # Cases directly assigned to me
            (
                    Q(assigned_emp__isnull=True) & (  # Unassigned cases where...
                # I'm in a parallel approval group
                    Q(current_approval_step__parallel_approval_groups__group__in=user_groups) |
                    # OR I'm a priority approver
                    Q(current_approval_step__priority_approver_groups__in=user_groups)
            )
            )
        ).distinct()

        # Categorize them
        assigned_to_me = []
        pending_my_approval = []
        already_approved = []

        for case in my_cases_query:
            case_data = self._serialize_case_with_actions(case, user_groups, user)

            if case.assigned_emp == user:
                # Directly assigned to me
                assigned_to_me.append(case_data)
            else:
                # It's a parallel approval case
                approval_step = case.current_approval_step
                if approval_step and approval_step.parallel_approval_groups.exists():
                    # Check if I've already approved
                    user_approved = ApprovalRecord.objects.filter(
                        case=case,
                        approval_step=approval_step,
                        approved_by=user
                    ).exists()

                    if user_approved:
                        already_approved.append(case_data)
                    else:
                        pending_my_approval.append(case_data)

        # -------- Available Cases (unassigned non-parallel cases in my groups) --------
        # These are cases I can assign to myself
        available_cases = Case.objects.filter(
            Q(assigned_emp__isnull=True) &  # Not assigned to anyone
            Q(assigned_group__in=user_groups) &  # In my groups
            # Exclude parallel approval cases (they go in my_cases)
            ~Q(current_approval_step__parallel_approval_groups__isnull=False) &
            # Exclude priority approval cases
            ~Q(current_approval_step__priority_approver_groups__in=user_groups)
        ).distinct()

        available_cases_data = CaseSerializer(available_cases, many=True).data

        return Response({
            'my_cases': {
                'total_count': len(assigned_to_me) + len(pending_my_approval) + len(already_approved),
                'categories': {
                    'assigned_to_me': {
                        'count': len(assigned_to_me),
                        'results': assigned_to_me
                    },
                    'pending_my_approval': {
                        'count': len(pending_my_approval),
                        'results': pending_my_approval
                    },
                    'already_approved': {
                        'count': len(already_approved),
                        'results': already_approved
                    }
                }
            },
            'available_cases': {
                'count': available_cases.count(),
                'results': available_cases_data
            }
        })

    def _serialize_case_with_actions(self, case, user_groups, user):
        """
        Serialize a single case with its available actions and approval info.
        """
        case_data = CaseSerializer(case).data
        case_data["available_actions"] = []
        case_data["approval_info"] = None
        case_data["approval_history"] = []  # Add approval history

        # Get all historical approvals for this case
        historical_approvals = ApprovalRecord.objects.filter(
            case=case
        ).select_related('approved_by', 'approval_step', 'action_taken').order_by('-approved_at')

        # Group historical approvals by approval step
        approval_history_by_step = {}
        for record in historical_approvals:
            step_id = record.approval_step.id
            if step_id not in approval_history_by_step:
                approval_history_by_step[step_id] = {
                    'approval_step': {
                        'id': record.approval_step.id,
                        'status': record.approval_step.status.name if record.approval_step.status else None,
                        'group': record.approval_step.group.name if record.approval_step.group else None,
                        'step_type': record.approval_step.get_step_type_display() if record.approval_step.step_type else None,
                    },
                    'approvals': []
                }

            approval_history_by_step[step_id]['approvals'].append({
                'approved_by': record.approved_by.get_full_name() or record.approved_by.username,
                'approved_at': record.approved_at,
                'action_taken': record.action_taken.name if record.action_taken else 'Unknown',
                'department': None  # Will be filled below
            })

        # Convert to list and add department info
        for step_data in approval_history_by_step.values():
            # Determine if this was a parallel approval step
            step_id = step_data['approval_step']['id']
            try:
                step_obj = ApprovalStep.objects.get(id=step_id)
                parallel_groups = step_obj.parallel_approval_groups.all()

                if parallel_groups.exists():
                    step_data['approval_step']['type'] = 'parallel'
                    step_data['approval_step']['required_approvals'] = step_obj.required_approvals

                    # Add department info to each approval
                    for approval in step_data['approvals']:
                        user_obj = get_user_model().objects.filter(
                            username=approval['approved_by'].split(' ')[0]  # Rough match
                        ).first()

                        if user_obj:
                            user_groups_ids = user_obj.groups.values_list('id', flat=True)
                            for pg in parallel_groups:
                                if pg.group.id in user_groups_ids:
                                    approval['department'] = pg.group.name
                                    break
                else:
                    step_data['approval_step']['type'] = 'sequential'
            except ApprovalStep.DoesNotExist:
                step_data['approval_step']['type'] = 'unknown'

            case_data["approval_history"].append(step_data)

        approval_step = getattr(case, "current_approval_step", None)
        if not approval_step:
            return case_data

        # Check if this is a parallel approval step
        parallel_groups = approval_step.parallel_approval_groups.all()
        if parallel_groups.exists() and approval_step.required_approvals:
            # Get approval progress for current step
            approval_records = ApprovalRecord.objects.filter(
                case=case,
                approval_step=approval_step
            ).select_related('approved_by')

            # Check if current user already approved
            user_approved = approval_records.filter(approved_by=user).exists()

            # Get list of who has approved
            approvers = []
            approved_groups = set()

            for record in approval_records:
                approver_groups = record.approved_by.groups.all()
                approver_info = {
                    'user': record.approved_by.get_full_name() or record.approved_by.username,
                    'approved_at': record.approved_at,
                    'department': None
                }

                # Find which group this approver represents
                for pg in parallel_groups:
                    if pg.group in approver_groups:
                        approver_info['department'] = pg.group.name
                        approved_groups.add(pg.group.id)
                        break

                if not approver_info['department'] and case.assigned_group in approver_groups:
                    approver_info['department'] = case.assigned_group.name
                    approved_groups.add(case.assigned_group.id)

                approvers.append(approver_info)

            case_data["approval_info"] = {
                "type": "parallel",
                "required_approvals": approval_step.required_approvals,
                "current_approvals": len(approved_groups),
                "remaining_approvals": max(0, approval_step.required_approvals - len(approved_groups)),
                "user_has_approved": user_approved,
                "can_approve": not user_approved,
                "approvers": approvers,
                "pending_groups": [
                    {"id": pg.group.id, "name": pg.group.name}
                    for pg in parallel_groups
                    if pg.group.id not in approved_groups
                ]
            }
        else:
            # Regular sequential approval
            case_data["approval_info"] = {
                "type": "sequential",
                "can_approve": case.assigned_emp == user or
                               (case.assigned_emp is None and
                                case.assigned_group in user_groups)
            }

        # Get available actions based on approval type
        action_steps = approval_step.actions.filter(
            active_ind=True,
            action__active_ind=True,
        ).select_related('action')

        allowed_actions = []
        for step in action_steps:
            action = step.action
            if not action:
                continue

            action_groups = action.groups.all()
            if not action_groups.exists() or action_groups.intersection(user_groups).exists():
                # Check if user can perform this action
                if case_data["approval_info"]["type"] == "parallel":
                    if case_data["approval_info"]["can_approve"]:
                        allowed_actions.append(action)
                else:
                    if case_data["approval_info"]["can_approve"]:
                        allowed_actions.append(action)

        case_data["available_actions"] = ActionBasicSerializer(allowed_actions, many=True).data

        # Add UI hints for better UX
        if case_data["approval_info"]["type"] == "parallel":
            if case_data["approval_info"]["user_has_approved"]:
                case_data["ui_status"] = "You have approved this case"
                case_data["ui_status_color"] = "green"
            elif case_data["approval_info"]["remaining_approvals"] > 0:
                case_data["ui_status"] = f"Awaiting {case_data['approval_info']['remaining_approvals']} more approval(s)"
                case_data["ui_status_color"] = "orange"
            else:
                case_data["ui_status"] = "All approvals received"
                case_data["ui_status_color"] = "green"

        return case_data



class AssignCaseView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        case_id = request.query_params.get('case_id')  # Get ID > query parameters

        if not case_id:
            return Response(
                {"error": "Case ID is required."},
                status=status.HTTP_400_BAD_REQUEST)

        try:
            case = Case.objects.get(id=case_id)  # Retrieve the case
        except Case.DoesNotExist:
            return Response(
                {"error": "Case not found."},
                status=status.HTTP_404_NOT_FOUND)

        # Check if the user belongs to the same group as the case's assigned group
        if (case.assigned_group
                and request.user.groups.filter(id=case.assigned_group.id).exists()):

            case.assigned_emp = request.user
            case.save()

            return Response(
                {"message": "Case assigned successfully."},
                status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "You are not authorized to assign this case."},
                status=status.HTTP_403_FORBIDDEN)

class ApprovalFlowActionCaseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs): # Modified method signature
        case_obj = get_object_or_404(Case, id=pk)
        action_id = request.query_params.get('action_id') # Get action_id from request.data
        notes_content = request.data.get('notes_content', '').strip() # Get notes_content from request.data

        if not action_id:
            return Response(
                {"detail": "Action ID is required."}, # Changed 'error' to 'detail' for consistency
                status=status.HTTP_400_BAD_REQUEST
            )

        action_obj = get_object_or_404(Action, id=action_id)

        # --- Notes Mandatory Validation ---
        if action_obj.notes_mandatory and not notes_content:
            return Response(
                {"detail": f"Notes are mandatory for the '{action_obj.name}' action."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verify the user has access to this action
        if not action_obj.groups.filter(
                id__in=request.user.groups.values_list('id', flat=True)
        ).exists():
            return Response(
                {'error': 'User does not have access to this action.'},
                status=status.HTTP_403_FORBIDDEN
            )

        approval_step = case_obj.current_approval_step
        user_groups = request.user.groups.all()

        # Check if user can take action on this case
        can_take_action = False
        is_priority_approver = False

        # For assigned cases (non-parallel workflow)
        if case_obj.assigned_emp:
            if case_obj.assigned_emp == request.user:
                can_take_action = True
        else:
            # For unassigned cases (potentially parallel workflow)
            if case_obj.assigned_group and user_groups.filter(
                    id=case_obj.assigned_group.id).exists():
                can_take_action = True

            if approval_step and approval_step.parallel_approval_groups.filter(
                    group__in=user_groups).exists():
                can_take_action = True

            if approval_step and approval_step.priority_approver_groups.filter(
                    id__in=user_groups.values_list('id', flat=True)).exists():
                can_take_action = True
                is_priority_approver = True

        if not can_take_action:
            return Response(
                {'error': 'You do not have permission to take action on this case.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Check if user already took action (prevent double action)
        existing_record = ApprovalRecord.objects.filter(
            case=case_obj,
            approval_step=approval_step,
            approved_by=request.user
        ).first()

        if existing_record:
            return Response({
                "error": f"You have already performed '{existing_record.action_taken.name}' on this case.",
                "previous_action": existing_record.action_taken.name,
                "action_date": existing_record.approved_at
            }, status=status.HTTP_400_BAD_REQUEST)

        # Retrieve the action step
        action_step = ActionStep.objects.filter(
            approval_step=approval_step,
            action=action_obj
        ).first()

        if not action_step:
            return Response(
                {"error": "Action step not found for this approval step."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic(): # Ensure atomic operations for all scenarios
            note_created = False
            # SCENARIO 1: Priority Approver - Immediate action
            if is_priority_approver:
                # Record the action
                approval_record = ApprovalRecord.objects.create(
                    case=case_obj,
                    approval_step=approval_step,
                    approved_by=request.user,
                    action_taken=action_obj  # Track which action was taken
                )
                # Create Note if content is provided
                if notes_content:
                    Note.objects.create(
                        case=case_obj,
                        author=request.user,
                        content=notes_content,
                        related_approval_record=approval_record,
                        created_by=request.user,
                        updated_by=request.user
                    )
                    note_created = True

                # Update case immediately
                self.update_case(case_obj, action_step)

                # Handle auto-approval if next step is AUTO
                self.handle_auto_approval(case_obj)

                message = f"Case updated via priority approver with action: {action_obj.name}"
                if note_created:
                    message += " and note added"

                return Response({
                    "message": message,
                    "new_status": case_obj.status.name
                }, status=status.HTTP_200_OK)

            # SCENARIO 2 & 3: Parallel Approval
            parallel_groups = approval_step.parallel_approval_groups.all()
            if parallel_groups.exists() and approval_step.required_approvals:
                # Record the action
                approval_record = ApprovalRecord.objects.create(
                    case=case_obj,
                    approval_step=approval_step,
                    approved_by=request.user,
                    action_taken=action_obj
                )
                # Create Note if content is provided
                if notes_content:
                    Note.objects.create(
                        case=case_obj,
                        author=request.user,
                        content=notes_content,
                        related_approval_record=approval_record,
                        created_by=request.user,
                        updated_by=request.user
                    )
                    note_created = True

                # Analyze all actions taken
                approval_records = ApprovalRecord.objects.filter(
                    case=case_obj,
                    approval_step=approval_step
                ).select_related('approved_by', 'action_taken')

                # Group by action type
                action_counts = {}
                action_groups = {}  # Track which groups took which actions

                for record in approval_records:
                    action_name = record.action_taken.name
                    if action_name not in action_counts:
                        action_counts[action_name] = 0
                        action_groups[action_name] = set()

                    # Find which group this user represents
                    user_group_ids = record.approved_by.groups.values_list('id', flat=True)
                    for pg in parallel_groups:
                        if pg.group.id in user_group_ids:
                            action_groups[action_name].add(pg.group.id)
                            break
                    else:
                        # Check primary group
                        if case_obj.assigned_group and case_obj.assigned_group.id in user_group_ids:
                            action_groups[action_name].add(case_obj.assigned_group.id)

                # Count unique groups per action
                for action_name in action_groups:
                    action_counts[action_name] = len(action_groups[action_name])

                # Determine if we've reached a decision
                total_unique_groups = sum(len(groups) for groups in action_groups.values())

                # Check if any action has reached the required threshold
                decision_made = False
                winning_action = None

                for action_name, count in action_counts.items():
                    if count >= approval_step.required_approvals:
                        decision_made = True
                        winning_action = action_name
                        break

                # If no single action has enough approvals but all groups have acted
                if not decision_made and total_unique_groups >= approval_step.required_approvals:
                    # Find the action with most approvals (majority)
                    winning_action = max(action_counts.items(), key=lambda x: x[1])[0]
                    decision_made = True

                if decision_made:
                    # Find the ActionStep for the winning action
                    winning_action_obj = Action.objects.get(name=winning_action)
                    winning_action_step = ActionStep.objects.filter(
                        approval_step=approval_step,
                        action=winning_action_obj
                    ).first()

                    if winning_action_step:
                        # Update case with the winning action's routing
                        self.update_case(case_obj, winning_action_step)

                        # Handle auto-approval if next step is AUTO
                        self.handle_auto_approval(case_obj)

                        message = f"Parallel approval completed. Action '{winning_action}' prevailed."
                        if note_created:
                            message += " and note added"

                        return Response({
                            "message": message,
                            "action_summary": action_counts,
                            "new_status": case_obj.status.name,
                            "total_actions": total_unique_groups,
                            "required_actions": approval_step.required_approvals
                        }, status=status.HTTP_200_OK)
                else:
                    # Still waiting for more approvals
                    message = f"Action recorded. Waiting for {approval_step.required_approvals - total_unique_groups} more action(s)."
                    if note_created:
                        message += " and note added"
                    return Response({
                        "message": message,
                        "action_summary": action_counts,
                        "total_actions": total_unique_groups,
                        "required_actions": approval_step.required_approvals,
                        "your_action": action_obj.name
                    }, status=status.HTTP_202_ACCEPTED)

            # SCENARIO 4: Standard (non-parallel) approval
            else:
                # Record the action (even for non-parallel, for audit trail)
                approval_record = ApprovalRecord.objects.create(
                    case=case_obj,
                    approval_step=approval_step,
                    approved_by=request.user,
                    action_taken=action_obj
                )
                # Create Note if content is provided
                if notes_content:
                    Note.objects.create(
                        case=case_obj,
                        author=request.user,
                        content=notes_content,
                        related_approval_record=approval_record,
                        created_by=request.user,
                        updated_by=request.user
                    )
                    note_created = True

                # Update case immediately
                self.update_case(case_obj, action_step)

                # Handle auto-approval if next step is AUTO
                self.handle_auto_approval(case_obj)

                message = f"Case updated successfully with action: {action_obj.name}"
                if note_created:
                    message += " and note added"

                return Response({
                    "message": message,
                    "new_status": case_obj.status.name
                }, status=status.HTTP_200_OK)

    def update_case(self, case_obj, action_step):
        """Update the case status and assigned group based on the action step."""
        case_obj.status = action_step.to_status
        case_obj.sub_status = action_step.sub_status

        # Find next approval step
        next_approval_step = ApprovalStep.objects.filter(
            service_type=case_obj.case_type,
            status=action_step.to_status
        ).first()

        if next_approval_step:
            case_obj.assigned_group = next_approval_step.group
            case_obj.current_approval_step = next_approval_step

            # Clear assigned_emp for parallel approval steps
            if next_approval_step.parallel_approval_groups.exists():
                case_obj.assigned_emp = None
            else:
                case_obj.assigned_emp = None  # Clear for fresh assignment
        else:
            # No next step - might be final status
            case_obj.current_approval_step = None
            case_obj.assigned_emp = None
            case_obj.assigned_group = None

        case_obj.last_action = action_step.action
        case_obj.save()

    def handle_auto_approval(self, case_obj):
        """Handle automatic progression if the next approval step is of type AUTO."""
        new_current_approval_step = case_obj.current_approval_step

        if (new_current_approval_step and
                new_current_approval_step.step_type == ApprovalStep.STEP_TYPE.AUTO):

            result, condition_obj = evaluate_conditions(
                case_obj, new_current_approval_step
            )

            if result and condition_obj:
                new_next_approval_step = ApprovalStep.objects.filter(
                    service_type=case_obj.case_type,
                    status=condition_obj.to_status
                ).first()

                if new_next_approval_step:
                    case_obj.status = condition_obj.to_status
                    case_obj.sub_status = condition_obj.sub_status
                    case_obj.assigned_group = new_next_approval_step.group
                    case_obj.current_approval_step = new_next_approval_step
                    case_obj.assigned_emp = None
                    case_obj.save()

class NoteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Notes with full CRUD operations.

    Endpoints:
    - GET /notes/ - List all notes (with filtering)
    - POST /notes/ - Create a new note
    - GET /notes/{id}/ - Retrieve a specific note
    - PUT/PATCH /notes/{id}/ - Update a note
    - DELETE /notes/{id}/ - Delete a note
    - GET /notes/by_case/{case_id}/ - Get all notes for a specific case
    """
    serializer_class = NoteSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter queryset based on query parameters and user permissions.
        """
        queryset = Note.objects.select_related(
            'case', 'author', 'related_approval_record', 'created_by', 'updated_by'
        ).all()

        # Filter by case if specified
        case_id = self.request.query_params.get('case_id')
        if case_id:
            queryset = queryset.filter(case_id=case_id)

        # Filter by author if specified
        author_id = self.request.query_params.get('author_id')
        if author_id:
            queryset = queryset.filter(author_id=author_id)

        # Filter by approval record if specified
        approval_record_id = self.request.query_params.get('approval_record_id')
        if approval_record_id:
            queryset = queryset.filter(related_approval_record_id=approval_record_id)

        # Search in content
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(content__icontains=search)

        # Filter by date range
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        """
        Set audit fields when creating a note.
        Intelligently link to an approval record based on context.
        """
        case_id = self.request.data.get('case')
        related_approval_record_id = self.request.data.get('related_approval_record')

        # If an approval record is explicitly provided, use it
        if related_approval_record_id:
            try:
                related_approval_record = ApprovalRecord.objects.get(pk=related_approval_record_id)
            except ApprovalRecord.DoesNotExist:
                related_approval_record = None
        else:
            related_approval_record = None

            # If no approval record specified, try to find a relevant one
            if case_id:
                try:
                    case = Case.objects.get(pk=case_id)

                    # Priority 1: Most recent approval record by the current user for this case
                    user_approval = ApprovalRecord.objects.filter(
                        case=case,
                        approved_by=self.request.user
                    ).order_by('-approved_at').first()

                    if user_approval:
                        related_approval_record = user_approval
                    else:
                        # Priority 2: Most recent approval record for the current approval step
                        if case.current_approval_step:
                            step_approval = ApprovalRecord.objects.filter(
                                case=case,
                                approval_step=case.current_approval_step
                            ).order_by('-approved_at').first()

                            if step_approval:
                                related_approval_record = step_approval
                            else:
                                # Priority 3: Most recent approval record for this case
                                related_approval_record = ApprovalRecord.objects.filter(
                                    case=case
                                ).order_by('-approved_at').first()

                except Case.DoesNotExist:
                    pass

        serializer.save(
            author=self.request.user,
            created_by=self.request.user,
            updated_by=self.request.user,
            related_approval_record=related_approval_record
        )

        def perform_update(self, serializer):
            """
            Update the updated_by field when modifying a note.
            """
            serializer.save(updated_by=self.request.user)

    @action(detail=False, methods=['get'], url_path='by_case/(?P<case_id>\d+)')
    def by_case(self, request, case_id=None):
        """
        Get all notes for a specific case.
        URL: /notes/by_case/{case_id}/
        """
        try:
            case = get_object_or_404(Case, pk=case_id)
            notes = self.get_queryset().filter(case=case)

            # Apply pagination if configured
            page = self.paginate_queryset(notes)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)

            serializer = self.get_serializer(notes, many=True)
            return Response({
                'case_id': int(case_id),  # Ensure it's an integer
                'case_serial_number': case.serial_number,
                'total_notes': notes.count(),
                'notes': serializer.data
            })
        except Case.DoesNotExist:
            return Response(
                {'detail': f'Case with ID {case_id} not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'], url_path='by_approval_record/(?P<approval_record_id>[^/.]+)')
    def by_approval_record(self, request, approval_record_id=None):
        """
        Get all notes for a specific approval record.

        URL: /notes/by_approval_record/{approval_record_id}/
        """
        try:
            approval_record = get_object_or_404(ApprovalRecord, pk=approval_record_id)
            notes = self.get_queryset().filter(related_approval_record=approval_record)

            serializer = self.get_serializer(notes, many=True)
            return Response({
                'approval_record_id': approval_record_id,
                'case_id': approval_record.case.id,
                'case_serial_number': approval_record.case.serial_number,
                'action_name': approval_record.action_taken.name if approval_record.action_taken else None,
                'total_notes': notes.count(),
                'notes': serializer.data
            })
        except ApprovalRecord.DoesNotExist:
            return Response(
                {'detail': f'ApprovalRecord with ID {approval_record_id} not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

    @action(detail=False, methods=['get'])
    def my_notes(self, request):
        """
        Get all notes created by the current user.

        URL: /notes/my_notes/
        """
        notes = self.get_queryset().filter(author=request.user)

        # Apply pagination if configured
        page = self.paginate_queryset(notes)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(notes, many=True)
        return Response({
            'user_id': request.user.id,
            'username': request.user.username,
            'total_notes': notes.count(),
            'notes': serializer.data
        })

    @action(detail=True, methods=['post'])
    def add_reply(self, request, pk=None):
        """
        Add a reply note to an existing note (creates a new note referencing the case).

        URL: /notes/{id}/add_reply/
        Body: {"content": "Reply content"}
        """
        parent_note = self.get_object()
        content = request.data.get('content', '').strip()

        if not content:
            return Response(
                {'detail': 'Reply content is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create reply note with reference to original note in content
        reply_content = f"[Reply to note by {parent_note.author.username if parent_note.author else 'N/A'} on {parent_note.created_at.strftime('%Y-%m-%d %H:%M')}]\n\n{content}"

        reply_note = Note.objects.create(
            case=parent_note.case,
            author=request.user,
            content=reply_content,
            related_approval_record=parent_note.related_approval_record,
            created_by=request.user,
            updated_by=request.user
        )

        serializer = self.get_serializer(reply_note)
        return Response(
            {
                'detail': 'Reply note created successfully.',
                'parent_note_id': parent_note.id,
                'reply_note': serializer.data
            },
            status=status.HTTP_201_CREATED
        )


# class ApprovalFlowActionCaseView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request, pk):
#         action_id = request.query_params.get('action_id')
#
#         if not action_id:
#             return Response(
#                 {"error": "action_id is required."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         # Get action object
#         action_obj = get_object_or_404(Action, id=action_id)
#
#         # Verify the user has access to this action
#         if not action_obj.groups.filter(
#                 id__in=request.user.groups.values_list('id', flat=True)
#         ).exists():
#             return Response(
#                 {'error': 'User does not have access to this action.'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
#
#         # Retrieve the case instance
#         case_obj = get_object_or_404(Case, id=pk)
#         approval_step = case_obj.current_approval_step
#         user_groups = request.user.groups.all()
#
#         # Check if user can take action on this case
#         can_take_action = False
#         is_priority_approver = False
#
#         # For assigned cases (non-parallel workflow)
#         if case_obj.assigned_emp:
#             if case_obj.assigned_emp == request.user:
#                 can_take_action = True
#         else:
#             # For unassigned cases (potentially parallel workflow)
#             if case_obj.assigned_group and user_groups.filter(
#                     id=case_obj.assigned_group.id).exists():
#                 can_take_action = True
#
#             if approval_step and approval_step.parallel_approval_groups.filter(
#                     group__in=user_groups).exists():
#                 can_take_action = True
#
#             if approval_step and approval_step.priority_approver_groups.filter(
#                     id__in=user_groups.values_list('id', flat=True)).exists():
#                 can_take_action = True
#                 is_priority_approver = True
#
#         if not can_take_action:
#             return Response(
#                 {'error': 'You do not have permission to take action on this case.'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
#
#         # Check if user already took action (prevent double action)
#         existing_record = ApprovalRecord.objects.filter(
#             case=case_obj,
#             approval_step=approval_step,
#             approved_by=request.user
#         ).first()
#
#         if existing_record:
#             return Response({
#                 "error": f"You have already performed '{existing_record.action_taken.name}' on this case.",
#                 "previous_action": existing_record.action_taken.name,
#                 "action_date": existing_record.approved_at
#             }, status=status.HTTP_400_BAD_REQUEST)
#
#         # Retrieve the action step
#         action_step = ActionStep.objects.filter(
#             approval_step=approval_step,
#             action=action_obj
#         ).first()
#
#         if not action_step:
#             return Response(
#                 {"error": "Action step not found for this approval step."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         # SCENARIO 1: Priority Approver - Immediate action
#         if is_priority_approver:
#             # Record the action
#             ApprovalRecord.objects.create(
#                 case=case_obj,
#                 approval_step=approval_step,
#                 approved_by=request.user,
#                 action_taken=action_obj  # Track which action was taken
#             )
#
#             # Update case immediately
#             self.update_case(case_obj, action_step)
#
#             # Handle auto-approval if next step is AUTO
#             self.handle_auto_approval(case_obj)
#
#             return Response({
#                 "message": f"Case updated via priority approver with action: {action_obj.name}",
#                 "new_status": case_obj.status.name
#             }, status=status.HTTP_200_OK)
#
#         # SCENARIO 2 & 3: Parallel Approval
#         parallel_groups = approval_step.parallel_approval_groups.all()
#         if parallel_groups.exists() and approval_step.required_approvals:
#             # Record the action
#             ApprovalRecord.objects.create(
#                 case=case_obj,
#                 approval_step=approval_step,
#                 approved_by=request.user,
#                 action_taken=action_obj
#             )
#
#             # Analyze all actions taken
#             approval_records = ApprovalRecord.objects.filter(
#                 case=case_obj,
#                 approval_step=approval_step
#             ).select_related('approved_by', 'action_taken')
#
#             # Group by action type
#             action_counts = {}
#             action_groups = {}  # Track which groups took which actions
#
#             for record in approval_records:
#                 action_name = record.action_taken.name
#                 if action_name not in action_counts:
#                     action_counts[action_name] = 0
#                     action_groups[action_name] = set()
#
#                 # Find which group this user represents
#                 user_group_ids = record.approved_by.groups.values_list('id', flat=True)
#                 for pg in parallel_groups:
#                     if pg.group.id in user_group_ids:
#                         action_groups[action_name].add(pg.group.id)
#                         break
#                 else:
#                     # Check primary group
#                     if case_obj.assigned_group and case_obj.assigned_group.id in user_group_ids:
#                         action_groups[action_name].add(case_obj.assigned_group.id)
#
#             # Count unique groups per action
#             for action_name in action_groups:
#                 action_counts[action_name] = len(action_groups[action_name])
#
#             # Determine if we've reached a decision
#             total_unique_groups = sum(len(groups) for groups in action_groups.values())
#
#             # Check if any action has reached the required threshold
#             decision_made = False
#             winning_action = None
#
#             for action_name, count in action_counts.items():
#                 if count >= approval_step.required_approvals:
#                     decision_made = True
#                     winning_action = action_name
#                     break
#
#             # If no single action has enough approvals but all groups have acted
#             if not decision_made and total_unique_groups >= approval_step.required_approvals:
#                 # Find the action with most approvals (majority)
#                 winning_action = max(action_counts.items(), key=lambda x: x[1])[0]
#                 decision_made = True
#
#             if decision_made:
#                 # Find the ActionStep for the winning action
#                 winning_action_obj = Action.objects.get(name=winning_action)
#                 winning_action_step = ActionStep.objects.filter(
#                     approval_step=approval_step,
#                     action=winning_action_obj
#                 ).first()
#
#                 if winning_action_step:
#                     # Update case with the winning action's routing
#                     self.update_case(case_obj, winning_action_step)
#
#                     # Handle auto-approval if next step is AUTO
#                     self.handle_auto_approval(case_obj)
#
#                     return Response({
#                         "message": f"Parallel approval completed. Action '{winning_action}' prevailed.",
#                         "action_summary": action_counts,
#                         "new_status": case_obj.status.name,
#                         "total_actions": total_unique_groups,
#                         "required_actions": approval_step.required_approvals
#                     }, status=status.HTTP_200_OK)
#             else:
#                 # Still waiting for more approvals
#                 remaining = approval_step.required_approvals - total_unique_groups
#                 return Response({
#                     "message": f"Action recorded. Waiting for {remaining} more action(s).",
#                     "action_summary": action_counts,
#                     "total_actions": total_unique_groups,
#                     "required_actions": approval_step.required_approvals,
#                     "your_action": action_obj.name
#                 }, status=status.HTTP_202_ACCEPTED)
#
#         # SCENARIO 4: Standard (non-parallel) approval
#         else:
#             # Record the action (even for non-parallel, for audit trail)
#             ApprovalRecord.objects.create(
#                 case=case_obj,
#                 approval_step=approval_step,
#                 approved_by=request.user,
#                 action_taken=action_obj
#             )
#
#             # Update case immediately
#             self.update_case(case_obj, action_step)
#
#             # Handle auto-approval if next step is AUTO
#             self.handle_auto_approval(case_obj)
#
#             return Response({
#                 "message": f"Case updated successfully with action: {action_obj.name}",
#                 "new_status": case_obj.status.name
#             }, status=status.HTTP_200_OK)
#
#     def update_case(self, case_obj, action_step):
#         """Update the case status and assigned group based on the action step."""
#         case_obj.status = action_step.to_status
#         case_obj.sub_status = action_step.sub_status
#
#         # Find next approval step
#         next_approval_step = ApprovalStep.objects.filter(
#             service_type=case_obj.case_type,
#             status=action_step.to_status
#         ).first()
#
#         if next_approval_step:
#             case_obj.assigned_group = next_approval_step.group
#             case_obj.current_approval_step = next_approval_step
#
#             # Clear assigned_emp for parallel approval steps
#             if next_approval_step.parallel_approval_groups.exists():
#                 case_obj.assigned_emp = None
#             else:
#                 case_obj.assigned_emp = None  # Clear for fresh assignment
#         else:
#             # No next step - might be final status
#             case_obj.current_approval_step = None
#             case_obj.assigned_emp = None
#             case_obj.assigned_group = None
#
#         case_obj.last_action = action_step.action
#         case_obj.save()
#
#     def handle_auto_approval(self, case_obj):
#         """Handle automatic progression if the next approval step is of type AUTO."""
#         new_current_approval_step = case_obj.current_approval_step
#
#         if (new_current_approval_step and
#                 new_current_approval_step.step_type == ApprovalStep.STEP_TYPE.AUTO):
#
#             result, condition_obj = evaluate_conditions(
#                 case_obj, new_current_approval_step
#             )
#
#             if result and condition_obj:
#                 new_next_approval_step = ApprovalStep.objects.filter(
#                     service_type=case_obj.case_type,
#                     status=condition_obj.to_status
#                 ).first()
#
#                 if new_next_approval_step:
#                     case_obj.status = condition_obj.to_status
#                     case_obj.sub_status = condition_obj.sub_status
#                     case_obj.assigned_group = new_next_approval_step.group
#                     case_obj.current_approval_step = new_next_approval_step
#                     case_obj.assigned_emp = None
#                     case_obj.save()


class UserCaseActionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # user = self.request.user
        try:
            user = self.request.user

        except AttributeError:
            user = None

        response_data = {}

        if user:
            user_groups = user.groups.all()
            # 1. All cases related to the same beneficiary
            user_cases = Case.objects.filter(applicant=user).all()
            user_cases_serialized = CaseSerializer(user_cases, many=True).data

            # 2. Extract current approval steps from user cases
            current_steps = ApprovalStep.objects.filter(
                id__in=user_cases.values_list('current_approval_step_id', flat=True),
                group__in=user_groups,
                active_ind=True
            ).distinct()

            # 3. Get related actions from ActionStep model
            action_ids = ActionStep.objects.filter(
                approval_step__in=current_steps,
                active_ind=True
            ).values_list('action_id', flat=True)

            actions = Action.objects.filter(
                id__in=action_ids,
                groups__in=user_groups,
                active_ind=True
            ).distinct()

            actions_serialized = ActionBasicSerializer(actions, many=True).data

            response_data = {
                'my_cases': {
                    'all': user_cases_serialized,
                    # //TODO: make sure status is
                    # //TODO: configured exactly as it in the lookups
                    'draft': CaseSerializer(user_cases.filter(
                        status__name='Draft'), many=True).data,
                    'approved': CaseSerializer(user_cases.filter(
                        status__name='Approved'), many=True).data,
                    'rejected': CaseSerializer(user_cases.filter(
                        status__name='Rejected'), many=True).data,
                    'returned': CaseSerializer(user_cases.filter(
                        status__name='Return To Applicant'), many=True).data,
                },
                'available_actions': actions_serialized
            }

        elif not user:


            # Handle if user is not authenticated properly (assigned_emp case)
            assigned_emp_cases = Case.objects.filter(assigned_emp=user).all()
            assigned_emp_cases_serialized = CaseSerializer(assigned_emp_cases, many=True).data

            user_groups = user.groups.all()
            # Same logic if needed here too
            current_steps = ApprovalStep.objects.filter(
                id__in=assigned_emp_cases.values_list('current_approval_step_id', flat=True),
                group__in=user_groups,
                active_ind=True
            ).distinct()

            action_ids = ActionStep.objects.filter(
                approval_step__in=current_steps,
                active_ind=True
            ).values_list('action_id', flat=True)

            actions = Action.objects.filter(
                id__in=action_ids,
                groups__in=user_groups,
                active_ind=True
            ).distinct()

            actions_serialized = ActionBasicSerializer(actions, many=True).data

            response_data = {
                'assigned_cases': assigned_emp_cases_serialized,
                'available_actions': actions_serialized
            }

            response_data = response_data
        else:
            response_data = {}
        return Response(response_data)


class RunMapperAPIView(views.APIView):
    def post(self, request):
        serializer = RunMapperInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        case = Case.objects.get(id=serializer.validated_data['case_id'])
        target = MapperTarget.objects.get(id=serializer.validated_data['mapper_target_id'])

        try:
            result = process_records(case, target, found_object=None)
            return Response({
                "message": "✅ Mapping executed successfully.",
                "result_count": len(result) if isinstance(result, list) else 1
            })
        except Exception as e:
            return Response({"error": str(e)}, status=400)

class DryRunMapperAPIView(views.APIView):
    def post(self, request):
        # from .plugins.default_plugin import dry_run
        serializer = DryRunMapperInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        case = Case.objects.get(id=serializer.validated_data['case_id'])
        target = MapperTarget.objects.get(id=serializer.validated_data['mapper_target_id'])

        try:
            preview = dry_run(case, target, found_object=None)
            return Response(preview)
        except Exception as e:
            return Response({"error": str(e)}, status=400)

class MapperExecutionLogListAPIView(generics.ListAPIView):
    queryset = MapperExecutionLog.objects.all().order_by('-executed_at')
    serializer_class = MapperExecutionLogSerializer

class MapperExecutionLogDetailAPIView(generics.RetrieveAPIView):
    queryset = MapperExecutionLog.objects.all()
    serializer_class = MapperExecutionLogSerializer



class CaseMapperViewSet(viewsets.ModelViewSet):
    queryset = CaseMapper.objects.all()
    serializer_class = CaseMapperSerializer

class MapperTargetViewSet(viewsets.ModelViewSet):
    queryset = MapperTarget.objects.all()
    serializer_class = MapperTargetSerializer

class MapperFieldRuleViewSet(viewsets.ModelViewSet):
    queryset = MapperFieldRule.objects.all()
    serializer_class = MapperFieldRuleSerializer

