import ast
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from authentication.models import CustomUser
from case.models import Case
from dynamicflow.models import Page
from utils.constant_lists_variables import UserTypes
from dynamicflow.utils.dynamicflow_helper import DynamicFlowHelper


class FlowAPIView(GenericAPIView):
    permission_classes = [AllowAny]

    queryset = Page.objects.all()
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):

        _query = {}
        if "service" in self.request.GET:
            _query["service__in"] = ast.literal_eval(
                self.request.GET.get("service"))

        if "beneficiary_type" in self.request.GET:
            _query["beneficiary_type"] = self.request.GET.get("beneficiary_type")
        request_by_user = CustomUser.objects.filter(id=self.request.user.id).first()

        _query["user"] = request_by_user
        # is_public_user = False
        # try:
        #     if _query['user'].user_type.code == UserTypes.PUBLIC_USER_CODE:
        #         is_public_user = True
        #         print(is_public_user)
        #     else:
        #         _query["user"] = Case.objects.filter(
        #             national_number=_query["national_number"]).first()
        # except AttributeError:
        #     _query["user"] = Case.objects.filter(applicant=request_by_user).first()
        result = DynamicFlowHelper(_query)
        flow = result.get_flow()
        # if is_public_user:
        #     result.save_services()
        return Response(flow, status=status.HTTP_200_OK)
