from django.conf import settings
from django.db import models

# Create your models here.
from authentication.models import CustomUser
from django.utils.translation import gettext_lazy as _


def get_language_choices():
    return settings.LANGUAGES


class Version(models.Model):
    INACTIVE = "IOS"
    CREATED = "Android"

    OPERATING_SYSTEM = (
        (INACTIVE, 'IOS'),
        (CREATED, 'Android'),
    )

    STAGING = "0"
    PROD = "1"
    DEV = "2"
    LOCAL = "3"
    ENVIRONMENT = (
        (STAGING, 'Staging'),
        (PROD, 'Production'),
        (DEV, 'Development'),
        (LOCAL, 'Local'),
    )

    version_number = models.CharField(max_length=15, null=True, blank=True)
    operating_system = models.CharField(max_length=10,
                                        choices=OPERATING_SYSTEM, null=True, blank=True)
    _environment = models.CharField(max_length=1,
                                    choices=ENVIRONMENT, null=True, blank=True)
    backend_endpoint = models.CharField(max_length=200, null=True, blank=True)
    active_ind = models.BooleanField(default=True)
    expiration_date = models.DateField(blank=True, null=True)


class ListOfActiveOldApp(models.Model):
    user = models.ForeignKey(CustomUser, null=True,
                             blank=True, on_delete=models.CASCADE)


class LocalVersion(models.Model):
    lang = models.CharField(
        max_length=10,
        choices=get_language_choices(),
        default='en',
        verbose_name=_("language")
    )
    version_number = models.CharField(max_length=15, null=True, blank=True)
    active_ind = models.BooleanField(default=True)
