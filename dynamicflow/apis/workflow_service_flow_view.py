from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import ast

from authentication.models import CustomUser
from dynamicflow.models import Page
from dynamicflow.utils.workflow_helper import WorkflowServiceFlowHelper


class WorkflowServiceFlowAPIView(GenericAPIView):
    """
    Dedicated service flow API for workflow builder
    Provides consistent data structure with explicit foreign key fields
    """
    permission_classes = [AllowAny]
    queryset = Page.objects.all()
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        _query = {}

        if "service" in self.request.GET:
            _query["service__in"] = ast.literal_eval(
                self.request.GET.get("service")
            )

        if "beneficiary_type" in self.request.GET:
            _query["beneficiary_type"] = self.request.GET.get("beneficiary_type")

        request_by_user = CustomUser.objects.filter(id=self.request.user.id).first()
        _query["user"] = request_by_user

        # Use the workflow-specific helper
        result = WorkflowServiceFlowHelper(_query)
        flow = result.get_flow()

        return Response(flow, status=status.HTTP_200_OK)