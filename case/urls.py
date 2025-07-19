from django.urls import path, include
from rest_framework.routers import DefaultRouter
from case.apis.views import (CaseViewSet, SubmitApplication,
                             EmployeeCasesView, AssignCaseView,
                             ApprovalFlowActionCaseView, UserCaseActionsView, RunMapperAPIView, DryRunMapperAPIView,
                             MapperExecutionLogListAPIView, MapperExecutionLogDetailAPIView, CaseMapperViewSet,
                             MapperTargetViewSet, MapperFieldRuleViewSet, NoteViewSet)
from case.apps import CaseConfig

app_name = CaseConfig.name
router = DefaultRouter()
router.register('case-mappers', CaseMapperViewSet, basename='case-mapper')
router.register('case-targets', MapperTargetViewSet, basename='case-target')
router.register('case-rules', MapperFieldRuleViewSet, basename='case-rule')
router.register('cases', CaseViewSet, basename='applicant_cases')
router.register(r'notes', NoteViewSet, basename='notes')


urlpatterns = [
    # path('cases/',
    #      CaseViewSet.as_view(), name='applicant_cases'),
    path('cases/submit/<int:pk>/',
         SubmitApplication.as_view(), name='submit_beneficiary_application'),
    path('cases/employee/',
         EmployeeCasesView.as_view(), name='employee_cases'),
    path('cases/assign_case/',
         AssignCaseView.as_view(), name='assign_case'),
    path('cases/<int:pk>/action/',
         ApprovalFlowActionCaseView.as_view(), name='approval_case_flow'),
    path('cases_actions/',
         UserCaseActionsView.as_view(), name='user-cases-actions'),
    # path('cases/<int:case>/documents/',
    #      CaseDocumentsAPIView.as_view(), name='case_documents'),
    path('', include(router.urls)),
]
urlpatterns += router.urls
# mapping log urls
urlpatterns += [
    path('api/mapper/run/', RunMapperAPIView.as_view(), name='run-mapper'),
    path('api/mapper/dry-run/', DryRunMapperAPIView.as_view(), name='dry-run-mapper'),
    path('api/mapper/logs/', MapperExecutionLogListAPIView.as_view(), name='mapper-log-list'),
    path('api/mapper/logs/<int:pk>/', MapperExecutionLogDetailAPIView.as_view(), name='mapper-log-detail'),
]




#
# urlpatterns = [

# #     # re_path('status/', BeneficiaryRequiredFieldsBasedOnInterestedServices.as_view(), name='beneficiary_status'),
# #     # path('upload_profile_pic/', BeneficiaryProfileImageView.as_view(),name='beneficiary_profile_pic_upload'),
# #     # path('update_profile_pic/<int:beneficiary>/', BeneficiaryProfileImageUpdateAPIView.as_view(),name='beneficiary_profile_pic_update'),
# #     # # path('beneficiary_checker/<int:pk>/', BeneficiaryCheckerAPIView.as_view(),name='beneficiary_checker'),
# #     # re_path('data/<int:national_number>/', BeneficiaryDataAPIView.as_view(), name='beneficiary_data'),
# #     #
# #     # path('gen-id-input/', GenID.as_view()),
# #     #
# #     # # BLOCK CHAIN URLS
# #     # re_path('request-data/', EntityAllBeneficiaryData.as_view(), name='entity_beneficiary_data'),
# #     # path('bc_data/', BeneficiaryDataFromBlockChainAPIView.as_view(), name='bc_beneficiary_data'),
# #     #
# #     # # path('verify-beneficiary/', VerifyBeneficiary.as_view()),
# #     # path('reject-beneficiary-maker-checker/', MakerCheckerRejectAPIView.as_view()),
# #     #
# #     # # start of not used #
# #     # path('verify-beneficiary/', VerifyBeneficiary.as_view()),
# #     # # end of not used #
# #     # path('entities_list/', BeneficiaryEntities.as_view()),
# #     #
# #     # path('deny-entity/', DenyEntity.as_view()),
# #     # path('approve-entity/', ApproveEntity.as_view()),
# #     #
# #     #
# #     # path('approve-entity-by_notification/', ApproveEntityByNotificationApiView.as_view()),
# #
# #
# #     # path('retrieve-request-history/', RetrieveRequestHistory.as_view()),
# # #     path('retrieve-pending-requests/', RetrievePendingRequests.as_view()),
# #
# #     # path('bd_create_profile/', VerifyBeneficiaryData, name='bc_beneficiary_data'),
# #
# ]
