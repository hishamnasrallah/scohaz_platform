from celery import shared_task
from django.utils.timezone import now
from icecream import ic

from .models import Subscription, License
from django.core.mail import send_mail


@shared_task
def test_task():
    return "Celery is working!"

result = test_task.delay()
ic(result)  # Should print 'Celery is working!'

#
# @shared_task
# def renew_subscriptions():
#     """
#     Task to renew subscriptions that have auto-renew enabled.
#     """
#     subscriptions = Subscription.objects.filter(auto_renew=True, end_date__lte=now(), status='active')
#     for subscription in subscriptions:
#         subscription.renew()
#
# @shared_task
# def renew_licenses():
#     """
#     Task to renew licenses that have auto-renew enabled.
#     """
#     licenses = License.objects.filter(auto_renew=True, valid_until__lte=now(), status='active')
#     for license in licenses:
#         license.renew()
#
#
# @shared_task
# def notify_about_renewal():
#     """
#     Notify clients about upcoming subscription/license expirations.
#     """
#     subscriptions = Subscription.objects.filter(end_date__lte=now() + timedelta(days=7), status='active')
#     for subscription in subscriptions:
#         send_mail(
#             'Subscription Renewal Reminder',
#             f'Your subscription for {subscription.plan.name} will expire on {subscription.end_date}.',
#             settings.DEFAULT_FROM_EMAIL,
#             [subscription.client.contact_email],
#         )
#
#     licenses = License.objects.filter(valid_until__lte=now() + timedelta(days=7), status='active')
#     for license in licenses:
#         send_mail(
#             'License Renewal Reminder',
#             f'Your license for project {license.project_id} will expire on {license.valid_until}.',
#             settings.DEFAULT_FROM_EMAIL,
#             [license.client.contact_email],
#         )