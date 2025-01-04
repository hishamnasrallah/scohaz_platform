from django.db import connection
from django.core.management.color import no_style

from authentication.models import CustomUser


from dynamicflow.models import Field, Category, Page
from lookup.models import Lookup
# from notifications.models import NotificationType,
# EntityNotification, UserNotification, NotificationAction
from version.models import Version, ListOfActiveOldApp

sequence_sql = connection.ops.sequence_reset_sql(
    no_style(),
    [CustomUser, Lookup, Field, Category, Page,
     Version, ListOfActiveOldApp])
with connection.cursor() as cursor:
    for sql in sequence_sql:
        cursor.execute(sql)
