from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.views import APIView
from case.models import Case, ApprovalRecord
from conditional_approval.apis.serializers import ActionSerializer
from conditional_approval.models import Action, ApprovalStep, ActionStep, ParallelApprovalGroup
from dynamicflow.utils.dynamicflow_validator_helper import DynamicFlowValidator
from lookup.models import Lookup
from utils.conditional_approval import evaluate_conditions
from dynamicflow.utils.dynamicflow_helper import DynamicFlowHelper
from .serializers import CaseSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action


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

        # Merge stored case data with request body (override stored values with request body values)
        merged_data = stored_case_data.copy()
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

        # Get cases assigned to the user
        my_cases = Case.objects.filter(assigned_emp=user)
        case_serializer = CaseSerializer(my_cases, many=True)

        # Get the count of 'my_cases'
        my_cases_count = my_cases.count()

        # Get user's groups
        user_groups = user.groups.all()

        # Fetch cases eligible for the user's groups in parallel and priority approvals
        available_cases = Case.objects.filter(
            Q(assigned_emp__isnull=True) & (
                # Cases where the assigned group matches the user's groups
                    Q(assigned_group__in=user_groups) |
                    # Cases where the current approval step has parallel approval groups matching user's groups
                    Q(current_approval_step__parallel_approval_groups__group__in=user_groups) |
                    # Cases where the current approval step has priority approver groups matching user's groups
                    Q(current_approval_step__priority_approver_groups__in=user_groups)
            )
        ).distinct()

        available_case_serializer = CaseSerializer(available_cases, many=True)

        # Get the count of 'available_cases'
        available_cases_count = available_cases.count()

        # Return the response with the correct counts and results
        return Response({
            'my_cases': {
                'count': my_cases_count,
                'next': None,
                'previous': None,
                'results': case_serializer.data
            },
            'available_cases': {
                'count': available_cases_count,
                'next': None,
                'previous': None,
                'results': available_case_serializer.data
            }
        })

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

        if user:
            # 1. All cases related to the same beneficiary
            user_cases = Case.objects.filter(applicant=user).all()
            user_cases_serialized = CaseSerializer(user_cases, many=True).data
            # 3. All actions related to the requested user group
            user_groups = user.groups.all()
            actions = Action.objects.filter(groups__in=user_groups).distinct()
            actions_serialized = ActionSerializer(actions, many=True).data

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

            # 2. All cases related to assigned employee user
            assigned_emp_cases = Case.objects.filter(
                assigned_emp=user).all()
            assigned_emp_cases_serialized = CaseSerializer(
                assigned_emp_cases, many=True).data

            # 3. All actions related to the requested user group
            user_groups = user.groups.all()
            actions = Action.objects.filter(groups__in=user_groups).distinct()
            actions_serialized = ActionSerializer(actions, many=True).data

            # 4. Create separate keys for the response
            response_data = {
                'assigned_cases': assigned_emp_cases_serialized,
                'available_actions': actions_serialized
            }
        else:
            response_data = {}
        return Response(response_data)
