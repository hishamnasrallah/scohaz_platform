from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from license_subscription_manager.models import (License,
                                                 Client,
                                                 SubscriptionPlan,
                                                 Subscription)
from rest_framework import status
from django.core.mail import send_mail
from django.conf import settings


class ValidateLicenseView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        license_key = request.data.get('license_key')
        project_id = request.data.get('project_id')
        license = License.objects.filter(
            license_key=license_key, project_id=project_id, status='active'
        ).first()
        if license and license.valid_until > timezone.now():
            return Response({'status': 'valid'})
        return Response({'status': 'invalid'}, status=status.HTTP_400_BAD_REQUEST)


class SubscriptionManagementView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        client = Client.objects.get(user=request.user)
        plan_id = request.data.get('plan_id')
        plan = SubscriptionPlan.objects.get(id=plan_id)

        subscription = Subscription.objects.create(
            client=client, plan=plan, status='active'
        )

        send_mail(
            'Subscription Activated',
            f'Your subscription for {plan.name} has been activated.',
            settings.DEFAULT_FROM_EMAIL,
            [client.contact_email],
        )

        return Response({'subscription_id': subscription.id, 'status': 'activated'})
