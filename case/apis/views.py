import json

from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status, views, generics
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from case.models import Case, ApprovalRecord, MapperTarget, MapperExecutionLog, CaseMapper, MapperFieldRule
from conditional_approval.apis.serializers import ActionBasicSerializer
from conditional_approval.models import Action, ApprovalStep, ActionStep, ParallelApprovalGroup
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

# last working submit api view before detailed validation
# class SubmitApplication(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def put(self, request, *args, **kwargs):
#         # Fetch case object and verify user ownership
#         case_obj = get_object_or_404(Case, pk=kwargs["pk"])
#
#         # Ensure the user belongs to the beneficiary of the case
#         if self.request.user == case_obj.applicant:
#
#             # Fetch the Submit action and corresponding approval step
#             submit_action = Action.objects.filter(name="Submit").first()
#             if not submit_action:
#                 return Response(
#                     {"detail": "Submit action not found."},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#             approval_step = ApprovalStep.objects.filter(
#                 service_type=case_obj.case_type,
#                 group=case_obj.assigned_group
#             ).first()
#
#             if not approval_step:
#                 return Response(
#                     {"detail": "No valid approval step found"},
#                     status=status.HTTP_400_BAD_REQUEST)
#
#             # Get the next action step based on the submit action
#             next_step = ActionStep.objects.filter(
#                 approval_step=approval_step,
#                 action=submit_action
#             ).first()
#             if not next_step:
#                 return Response(
#                     {"detail": "No action step found for the submit action."},
#                     status=status.HTTP_400_BAD_REQUEST
#                 )
#             # Dynamically fetch the "Submitted" case status from the Lookup model
#             case_status = Lookup.objects.filter(
#                 parent_lookup__name='Case Status',
#                 name='Submitted').first()
#             if not case_status:
#                 return Response(
#                     {"detail": "Submitted status not found in Lookup model"},
#                     status=status.HTTP_400_BAD_REQUEST)
#
#             # Update the case status and assigned group
#             case_obj.status = case_status  # Update status dynamically
#             next_approval_step = ApprovalStep.objects.filter(
#                 service_type=case_obj.case_type,
#                 status=next_step.to_status
#             ).first()
#
#             if not next_approval_step:
#                 return Response(
#                     {"detail": "Next approval step not found for the given status."},
#                     status=status.HTTP_400_BAD_REQUEST)
#
#             case_obj.assigned_group = next_approval_step.group
#             case_obj.last_action = submit_action
#             case_obj.current_approval_step = next_approval_step
#
#             # Save case object with updated details
#             case_obj.save()
#
#             # Handle automatic progression based on the current approval step type
#             new_current_approval_step = ApprovalStep.objects.filter(
#                 service_type=case_obj.case_type,
#                 status=case_obj.status
#             ).first()
#
#             if (new_current_approval_step
#                     and new_current_approval_step.step_type
#                     == ApprovalStep.STEP_TYPE.AUTO):
#                 result, condition_obj = evaluate_conditions(
#                     case_obj, new_current_approval_step)
#
#                 if result and condition_obj:
#                     # Auto-progress case to next status based on condition evaluation
#                     new_next_approval_step = ApprovalStep.objects.filter(
#                         service_type=case_obj.case_type,
#                         status=condition_obj.to_status
#                     ).first()
#                     if not next_approval_step:
#                         return Response(
#                             {"detail": "Next approval step not found for the given status."},
#                             status=status.HTTP_400_BAD_REQUEST
#                         )
#                     if new_next_approval_step:
#                         new_case_values = {
#                             "status": condition_obj.to_status,
#                             "sub_status": condition_obj.sub_status,
#                             "assigned_group": new_next_approval_step.group,
#                             "current_approval_step": new_next_approval_step,
#                             "assigned_emp": None
#                         }
#                         for key, value in new_case_values.items():
#                             setattr(case_obj, key, value)
#
#                         case_obj.save()
#
#             return Response({"detail": "success"}, status=status.HTTP_200_OK)
#
#         else:
#             return Response(
#                 {
#                     "detail": "you don't have permission to perform this action",
#                     "detail_ara": "ليس لديك الصلاحية لتنفيذ هذا الامر"
#                 },
#                 status=status.HTTP_403_FORBIDDEN
#             )


class EmployeeCasesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        user_groups = user.groups.all()

        # -------- My Cases --------
        my_cases = Case.objects.filter(assigned_emp=user)
        my_cases_data = self._serialize_cases_with_actions(my_cases, user_groups)
        my_cases_count = my_cases.count()

        # -------- Available Cases --------
        available_cases = Case.objects.filter(
            Q(assigned_emp__isnull=True) & (
                    Q(assigned_group__in=user_groups) |
                    Q(current_approval_step__parallel_approval_groups__group__in=user_groups) |
                    Q(current_approval_step__priority_approver_groups__in=user_groups)
            )
        ).distinct()
        available_cases_data = CaseSerializer(available_cases, many=True).data
        available_cases_count = available_cases.count()

        # -------- Response --------
        return Response({
            'my_cases': {
                'count': my_cases_count,
                'next': None,
                'previous': None,
                'results': my_cases_data
            },
            'available_cases': {
                'count': available_cases_count,
                'next': None,
                'previous': None,
                'results': available_cases_data
            }
        })

    def _serialize_cases_with_actions(self, cases, user_groups):
        """
        For each case, attach valid actions based on the current approval step and user group.
        """
        enriched_cases = []

        for case in cases:
            case_data = CaseSerializer(case).data

            # Initialize available actions list
            case_data["available_actions"] = []

            # Get the current approval step
            approval_step = getattr(case, "current_approval_step", None)
            if not approval_step:
                enriched_cases.append(case_data)
                continue

            # Get active ActionSteps for this approval step
            action_steps = approval_step.actions.filter(
                active_ind=True,
                action__active_ind=True,
            ).select_related('action')

            # Filter actions by group access
            allowed_actions = []
            for step in action_steps:
                action = step.action
                if not action:
                    continue

                action_groups = action.groups.all()
                if not action_groups.exists() or action_groups.intersection(user_groups).exists():
                    allowed_actions.append(action)

            # Serialize allowed actions
            case_data["available_actions"] = ActionBasicSerializer(allowed_actions, many=True).data
            enriched_cases.append(case_data)

        return enriched_cases

# last view was working fine without pararrel approvals
# class EmployeeCasesView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def get(self, request):
#         user = request.user
#
#         # Get cases assigned to the user
#         my_cases = Case.objects.filter(assigned_emp=user)
#         case_serializer = CaseSerializer(my_cases, many=True)
#
#         # Get the count of 'my_cases'
#         my_cases_count = my_cases.count()
#
#         # Get user's groups
#         user_groups = user.groups.all()
#
#         # Get available cases related to the user's groups (not assigned to anyone)
#         available_cases = Case.objects.filter(
#             assigned_emp__isnull=True,
#             assigned_group__in=user_groups
#         ).distinct()
#         available_case_serializer = CaseSerializer(available_cases, many=True)
#
#         # Get the count of 'available_cases'
#         available_cases_count = available_cases.count()
#
#         # Return the response with the correct counts and results
#         return Response({
#             'my_cases': {
#                 'count': my_cases_count,
#                 'next': None,
#                 'previous': None,
#                 'results': case_serializer.data
#             },
#             'available_cases': {
#                 'count': available_cases_count,
#                 'next': None,
#                 'previous': None,
#                 'results': available_case_serializer.data
#             }
#         })


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

    def post(self, request, pk):
        action_id = request.query_params.get('action_id')

        if not action_id:
            return Response(
                {"error": "action_id is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get action object
        action_obj = get_object_or_404(Action, id=action_id)

        # Verify the user has access to this action
        if not action_obj.groups.filter(
                id__in=request.user.groups.values_list('id', flat=True)
        ).exists():
            return Response(
                {'error': 'User does not have access to this action.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Retrieve the case instance
        case_obj = get_object_or_404(Case, id=pk)
        if case_obj.assigned_emp and case_obj.assigned_emp != request.user:
            return Response(
                {'error': 'User does not have permission to this action.'},
                status=status.HTTP_403_FORBIDDEN
            )

        # Retrieve the current approval step
        approval_step = ApprovalStep.objects.filter(
            service_type=case_obj.case_type,
            group=case_obj.assigned_group
        ).first()

        if not approval_step:
            return Response(
                {"error": "Approval step not found or misconfigured."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Retrieve the action step for the current approval step
        action_step = ActionStep.objects.filter(
            approval_step=approval_step,
            action=action_obj
        ).first()

        if not action_step:
            return Response(
                {"error": "Action step not found for this approval step."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Handle Priority Approvals
        if approval_step.priority_approver_groups.exists():
            if approval_step.priority_approver_groups.filter(
                    id__in=request.user.groups.values_list('id', flat=True)
            ).exists():
                # Immediate approval for priority approvers
                self.update_case(case_obj, action_step)
                return Response(
                    {"message": "Case approved via priority approver."},
                    status=status.HTTP_200_OK
                )

        # Handle Parallel Approvals
        parallel_groups = approval_step.parallel_approval_groups.all()
        if parallel_groups.exists():
            # Record the approval
            ApprovalRecord.objects.get_or_create(
                case=case_obj,
                approval_step=approval_step,
                approved_by=request.user
            )

            # Count distinct group approvals
            approved_groups = ApprovalRecord.objects.filter(
                case=case_obj,
                approval_step=approval_step
            ).values('approved_by__groups').distinct().count()

            # Check if the required number of approvals is met
            if approved_groups < approval_step.required_approvals:
                return Response(
                    {"message": "Approval recorded. Waiting for more approvals."},
                    status=status.HTTP_202_ACCEPTED
                )

        # Proceed to update the case if no parallel or priority conditions prevent it
        self.update_case(case_obj, action_step)

        # Handle Automatic Approval Steps
        self.handle_auto_approval(case_obj)

        return Response({"message": "Case updated successfully."},
                        status=status.HTTP_200_OK)

    def update_case(self, case_obj, action_step):
        """
        Update the case status and assigned group based on the action step.
        """
        case_obj.status = action_step.to_status
        next_approval_step = ApprovalStep.objects.filter(
            service_type=case_obj.case_type,
            status=action_step.to_status
        ).first()

        if not next_approval_step:
            raise ValidationError(
                {"error": "Next approval step not found for the given status."}
            )

        case_obj.assigned_group = next_approval_step.group
        case_obj.last_action = action_step.action
        case_obj.current_approval_step = next_approval_step
        case_obj.sub_status = action_step.sub_status
        case_obj.assigned_emp = None
        case_obj.save()

    def handle_auto_approval(self, case_obj):
        """
        Handle automatic progression if the next approval step is of type AUTO.
        """
        new_current_approval_step = ApprovalStep.objects.filter(
            service_type=case_obj.case_type,
            status=case_obj.status
        ).first()

        if new_current_approval_step and new_current_approval_step.step_type == ApprovalStep.STEP_TYPE.AUTO:
            result, condition_obj = evaluate_conditions(
                case_obj, new_current_approval_step
            )

            if result and condition_obj:
                new_next_approval_step = ApprovalStep.objects.filter(
                    service_type=case_obj.case_type,
                    status=condition_obj.to_status
                ).first()

                if new_next_approval_step:
                    new_case_values = {
                        "status": condition_obj.to_status,
                        "sub_status": condition_obj.sub_status,
                        "assigned_group": new_next_approval_step.group,
                        "current_approval_step": new_next_approval_step,
                        "assigned_emp": None
                    }
                    for key, value in new_case_values.items():
                        setattr(case_obj, key, value)

                    case_obj.save()


# latest view employe actions working without pararrel approvals
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
#         if case_obj.assigned_emp != request.user:
#             return Response(
#                 {'error': 'User does not have permission to this action.'},
#                 status=status.HTTP_403_FORBIDDEN
#             )
#
#         # Retrieve the current approval step
#         approval_step = ApprovalStep.objects.filter(
#             service_type=case_obj.case_type,
#             group=case_obj.assigned_group
#         ).first()
#
#         if not approval_step:
#             return Response(
#                 {"error": "Approval step not found or misconfigured."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#
#         # Retrieve the action step for the current approval step
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
#         # Handle Priority Approvals
#         if approval_step.priority_approver_groups.exists():
#             if approval_step.priority_approver_groups.filter(
#                     id__in=request.user.groups.values_list('id', flat=True)
#             ).exists():
#                 # Immediate approval for priority approvers
#                 self.update_case(case_obj, action_step)
#                 return Response({"message": "Case approved via priority approver."},
#                                 status=status.HTTP_200_OK)
#
#         # Handle Parallel Approvals
#         parallel_config = ParallelApprovalGroup.objects.filter(
#             approval_step=approval_step
#         ).first()
#
#         if parallel_config:
#             # Record the approval
#             ApprovalRecord.objects.get_or_create(
#                 case=case_obj,
#                 approval_step=approval_step,
#                 approved_by=request.user
#             )
#
#             # Count distinct group approvals
#             approved_groups = ApprovalRecord.objects.filter(
#                 case=case_obj,
#                 approval_step=approval_step
#             ).values_list('approved_by__groups', flat=True).distinct()
#
#             # Check if the required number of approvals is met
#             if len(approved_groups) < parallel_config.required_approvals:
#                 return Response(
#                     {"message": "Approval recorded. Waiting for more approvals."},
#                     status=status.HTTP_202_ACCEPTED
#                 )
#
#         # Proceed to update the case
#         self.update_case(case_obj, action_step)
#
#         # Handle Automatic Approval Steps
#         self.handle_auto_approval(case_obj)
#
#         return Response({"message": "Case updated successfully."},
#                         status=status.HTTP_200_OK)
#
#     def update_case(self, case_obj, action_step):
#         """
#         Update the case status and assigned group based on the action step.
#         """
#         case_obj.status = action_step.to_status
#         next_approval_step = ApprovalStep.objects.filter(
#             service_type=case_obj.case_type,
#             status=action_step.to_status
#         ).first()
#
#         if not next_approval_step:
#             raise ValidationError(
#                 {"error": "Next approval step not found for the given status."}
#             )
#
#         case_obj.assigned_group = next_approval_step.group
#         case_obj.last_action = action_step.action
#         case_obj.current_approval_step = next_approval_step
#         case_obj.sub_status = action_step.sub_status
#         case_obj.assigned_emp = None
#         case_obj.save()
#
#     def handle_auto_approval(self, case_obj):
#         """
#         Handle automatic progression if the next approval step is of type AUTO.
#         """
#         new_current_approval_step = ApprovalStep.objects.filter(
#             service_type=case_obj.case_type,
#             status=case_obj.status
#         ).first()
#
#         if new_current_approval_step and new_current_approval_step.step_type == ApprovalStep.STEP_TYPE.AUTO:
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
#                     new_case_values = {
#                         "status": condition_obj.to_status,
#                         "sub_status": condition_obj.sub_status,
#                         "assigned_group": new_next_approval_step.group,
#                         "current_approval_step": new_next_approval_step,
#                         "assigned_emp": None
#                     }
#                     for key, value in new_case_values.items():
#                         setattr(case_obj, key, value)
#
#                     case_obj.save()


# latest working view
# class ApprovalFlowActionCaseView(APIView):
#     permission_classes = [IsAuthenticated]
#
#     def post(self, request, pk):
#         action_id = request.query_params.get('action_id')
#
#         if not action_id:
#             return Response(
#                 {"error": "action_id is required."},
#                 status=status.HTTP_400_BAD_REQUEST)
#
#         # Get action_id from query parameters
#         action_obj = get_object_or_404(Action, id=action_id)
#         if not action_obj.groups.filter(
#                 id__in=request.user.groups.values_list('id', flat=True)
#         ).exists():
#             return Response(
#                 {'error': 'User does not have access to this action.'},
#                 status=status.HTTP_403_FORBIDDEN)
#         #
#         # try:
#         #     # Retrieve the action based on the action_id
#         #     action = Action.objects.get(id=action_id)
#         # except Action.DoesNotExist:
#         #     return Response(
#         #         {"error": "Action not found."},
#         #         status=status.HTTP_404_NOT_FOUND)
#
#         try:
#             # Retrieve the case instance using the pk from the URL
#             case_obj = Case.objects.get(id=pk)
#             if case_obj.assigned_emp != request.user:
#                 return Response(
#                     {'error': 'User does not have permission to this action.'},
#                     status=status.HTTP_403_FORBIDDEN)
#
#         except Case.DoesNotExist:
#             return Response(
#                 {"error": "Case not found."},
#                 status=status.HTTP_404_NOT_FOUND)
#
#         # Filter ApprovalStep based on last_action, group, and service_type
#         approval_step = ApprovalStep.objects.filter(
#             service_type=case_obj.case_type,
#             group=case_obj.assigned_group).first()
#
#         # Check if exactly one approval step is found
#         if not approval_step:
#             return Response(
#                 {
#                     "error": (
#                         "Approval step not found or misconfigured."
#                     )
#                 },
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#         action_step = ActionStep.objects.filter(
#             approval_step=approval_step,
#             action=action_obj).first()  # approval_step.to_group
#
#         if not action_step:
#             return Response(
#                 {"error": "Action step not found for this approval step."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#         # Update the case instance
#         case_obj.status = action_step.to_status
#         next_approval_step = ApprovalStep.objects.filter(
#             service_type=case_obj.case_type,
#             status=action_step.to_status).first()
#         if not next_approval_step:
#             return Response(
#                 {"error": "Next approval step not found for the given status."},
#                 status=status.HTTP_400_BAD_REQUEST
#             )
#         case_obj.assigned_group = next_approval_step.group  # next_step
#         case_obj.last_action = action
#         case_obj.current_approval_step = next_approval_step
#         case_obj.sub_status = action_step.sub_status
#         case_obj.assigned_emp = None
#         case_obj.save()
#
#         new_current_approval_step = ApprovalStep.objects.filter(
#             service_type=case_obj.case_type,
#             status=case_obj.status).first()
#         if new_current_approval_step.step_type == ApprovalStep.STEP_TYPE.AUTO:
#             result, condition_obj = evaluate_conditions(
#                 case_obj, new_current_approval_step)
#             if result:
#                 new_next_approval_step = ApprovalStep.objects.filter(
#                     service_type=case_obj.case_type,
#                     status=condition_obj.to_status).first()
#                 if not next_approval_step:
#                     return Response(
#                         {"error": "Next approval step not found for the given status."},
#                         status=status.HTTP_400_BAD_REQUEST
#                     )
#                 new_case_values = {"status": condition_obj.to_status,
#                                    "sub_status": condition_obj.sub_status,
#                                    "assigned_group": new_next_approval_step.group,
#                                    "current_approval_step": new_next_approval_step,
#                                    "assigned_emp": None
#                                    }
#                 for key, value in new_case_values.items():
#                     setattr(case_obj, key, value)
#                 case_obj.save()
#
#         return Response({"message": "Case updated successfully."},
#                         status=status.HTTP_200_OK)


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

