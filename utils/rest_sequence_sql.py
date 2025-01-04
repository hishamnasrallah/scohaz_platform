from django.core.management.color import no_style
from django.db import connection

from authentication.models import CustomUser
from case.models import Case

from dynamicflow.models import Field, Category, Page

from version.models import Version, ListOfActiveOldApp


def reset_sequence():
    sequence_sql = connection.ops.sequence_reset_sql(no_style(),
                                                     [CustomUser, Case,
                                                      Page, Category, Field,
                                                      Version, ListOfActiveOldApp])
    print('helloo')
    with connection.cursor() as cursor:
        for sql in sequence_sql:
            cursor.execute(sql)
