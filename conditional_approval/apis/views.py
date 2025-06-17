from rest_framework import viewsets
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from conditional_approval.models import (
    Action, ApprovalStep, ActionStep, ParallelApprovalGroup,
    ApprovalStepCondition, APICallCondition
)
from lookup.models import Lookup

from .serializers import (
    ActionSerializer, ApprovalStepSerializer, ActionStepSerializer,
    ParallelApprovalGroupSerializer, ApprovalStepConditionSerializer,
    APICallConditionSerializer, FullApprovalStepSerializer, LookupSerializer
)


class ActionViewSet(viewsets.ModelViewSet):
    queryset = Action.objects.all()
    serializer_class = ActionSerializer
    permission_classes = [IsAuthenticated]


class ApprovalStepViewSet(viewsets.ModelViewSet):
    queryset = ApprovalStep.objects.all()
    serializer_class = ApprovalStepSerializer
    permission_classes = [IsAuthenticated]


class ActionStepViewSet(viewsets.ModelViewSet):
    queryset = ActionStep.objects.all()
    serializer_class = ActionStepSerializer
    permission_classes = [IsAuthenticated]


class ParallelApprovalGroupViewSet(viewsets.ModelViewSet):
    queryset = ParallelApprovalGroup.objects.all()
    serializer_class = ParallelApprovalGroupSerializer
    permission_classes = [IsAuthenticated]


class ApprovalStepConditionViewSet(viewsets.ModelViewSet):
    queryset = ApprovalStepCondition.objects.all()
    serializer_class = ApprovalStepConditionSerializer
    permission_classes = [IsAuthenticated]


class APICallConditionViewSet(viewsets.ModelViewSet):
    queryset = APICallCondition.objects.all()
    serializer_class = APICallConditionSerializer
    permission_classes = [IsAuthenticated]


# Master API for Full Nested Step Handling

class FullApprovalStepViewSet(viewsets.ModelViewSet):
    queryset = ApprovalStep.objects.prefetch_related(
        'actions', 'parallel_approval_groups',
        'approvalstepcondition_set', 'apicallcondition_set'
    ).select_related('service_type')
    serializer_class = FullApprovalStepSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        service_type = request.query_params.get("service_type")

        qs = self.queryset
        if service_type:
            qs = qs.filter(service_type_id=service_type)

        # Group by service_type
        service_to_steps = {}
        for step in qs:
            service_id = step.service_type_id
            if service_id not in service_to_steps:
                service_to_steps[service_id] = {
                    "service": LookupSerializer(step.service_type).data,
                    "steps": []
                }
            service_to_steps[service_id]["steps"].append(
                self.get_serializer(step).data
            )

        grouped_data = list(service_to_steps.values())
        return Response({
            "count": len(grouped_data),
            "results": grouped_data
        })

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve steps for a specific service by ID.
        This will work with `/master-steps/{service_type}/`
        """
        service_type = kwargs.get("pk")
        service = get_object_or_404(Lookup, pk=service_type)

        steps = self.queryset.filter(service_type=service)
        data = [
            self.get_serializer(step).data for step in steps
        ]
        return Response({
            "service": LookupSerializer(service).data,
            "steps": data
        })
