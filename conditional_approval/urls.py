from rest_framework.routers import DefaultRouter
from django.urls import path, include
from conditional_approval.apis import views

router = DefaultRouter()
router.register(r'actions', views.ActionViewSet)
router.register(r'approval-steps', views.ApprovalStepViewSet)
router.register(r'action-steps', views.ActionStepViewSet)
router.register(r'parallel-approval-groups', views.ParallelApprovalGroupViewSet)
router.register(r'step-conditions', views.ApprovalStepConditionViewSet)
router.register(r'api-call-conditions', views.APICallConditionViewSet)
router.register(r'master-steps', views.FullApprovalStepViewSet, basename='master-steps')

urlpatterns = [
    path('', include(router.urls)),
]
