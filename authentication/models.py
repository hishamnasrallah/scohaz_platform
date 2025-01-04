import random
from datetime import datetime

import pytz
import requests
from django.contrib.auth.models import AbstractUser, Permission, Group
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings

from lookup.models import Lookup


def get_language_choices():
    return settings.LANGUAGES


# Create your models here.
class UserPreference(models.Model):
    """
    Stores user-specific preferences such as language.
    """
    user = models.OneToOneField(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="preference",
        verbose_name=_("user")
    )
    lang = models.CharField(
        max_length=10,
        choices=get_language_choices(),
        default='en',
        verbose_name=_("language")
    )

    def __str__(self):
        return f"Preferences for {self.user.username}"


class CustomUser(AbstractUser):
    second_name = models.CharField(_('second name'), max_length=150, blank=True)
    third_name = models.CharField(_('third name'), max_length=150, blank=True)
    user_type = models.ForeignKey(
        "authentication.UserType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
        verbose_name=_('user type')
    )
    sms_code = models.CharField(max_length=4, null=True, blank=True)
    sms_time = models.DateTimeField(auto_now_add=True, null=True)
    activated_account = models.BooleanField(default=False, null=True, blank=True)
    is_developer = models.BooleanField(
        _("developer status"),
        default=False,
        help_text=_("Designates whether the user can log into this admin site."),
    )
    def __str__(self):
        return self.username

    def random_number(self):
        return str(random.randint(1000, 9999))

    def reset_sms_code(self):
        self.sms_code = self.random_number()
        utc = pytz.UTC
        now = datetime.now().replace(tzinfo=utc)
        self.sms_time = now
        self.save()

    # def get_child(self):
    def sms(self):
        # print(Case.objects.get(pk=self.id).phone_number)
        try:
            phone_number = PhoneNumber.objects.filter(user=self.id,
                                                      main=True).first()
            if phone_number:
                return self.send_sms(
                    phone_number.phone_number,
                    f'SCOHAZ APP: Your verification code is {self.sms_code}')
        except PhoneNumber.DoesNotExist:
            print("Phone number not found")

    @staticmethod
    def send_sms(mobile, message_body):
        url = settings.SMS_OTP
        data = {
            "body": message_body,
            "password": settings.SMS_PASSWORD,
            "mobile": mobile
        }

        headers = {
            'Content-Type': 'application/json'
        }
        r = requests.post(url=url, headers=headers, json=data)
        # logger.info(r.content)
        print(r.content)
        print(r.status_code)
        return r.content


class UserType(models.Model):
    """
    Represents different types of users (e.g., Admin, Customer, Vendor, etc.).
    """
    name = models.CharField(_('user type name'), max_length=100, unique=True)
    name_ara = models.CharField(_('user type name ara'), max_length=100, unique=True)
    description = models.TextField(_('description'), blank=True, null=True)
    code = models.CharField(_('user type code'), max_length=2, unique=True)
    permissions = models.ManyToManyField(Permission,
                                         blank=True, related_name='user_types')
    group = models.OneToOneField(Group,
                                 on_delete=models.SET_NULL, null=True, blank=True)

    active_ind = models.BooleanField(_('active indicator'), default=True)

    def __str__(self):
        return self.name

    def assign_permissions_to_user(self, user):
        """
        Assign the user type's permissions to the user dynamically.
        """
        # Avoid adding duplicate permissions
        for permission in self.permissions.all():
            if not user.user_permissions.filter(id=permission.id).exists():
                user.user_permissions.add(permission)
        user.save()

    def assign_group_permissions(self):
        """
        Assigns a group to the user type.
        The group will have permissions associated with it.
        """
        if not self.group:
            group, created = Group.objects.get_or_create(name=self.name)
            self.group = group
            self.save()

        # Assign permissions of the group to all users with this UserType
        for user in self.group.user_set.all():
            self.assign_permissions_to_user(user)

    def deactivate(self):
        """
        Deactivates a user type,
        useful for preventing users from being assigned this type.
        """
        self.active_ind = False
        self.save()

    def activate(self):
        """
        Activates a user type.
        """
        self.active_ind = True
        self.save()


phone_regex_validator = RegexValidator(regex=r'^\+?1?\d{9,15}$',
                                       message="Phone number must "
                                               "be entered in the format: "
                                               "'+999999999'. Up to 15 digits allowed.")


class PhoneNumber(models.Model):

    is_default = models.BooleanField(default=False)
    number_type = models.ForeignKey(
        Lookup,
        on_delete=models.CASCADE,
        limit_choices_to={'parent_lookup__name': 'Phone Types',
                          'type': Lookup.LookupTypeChoices.LOOKUP_VALUE},
        # Limit to child lookup under 'Phone Types'
        verbose_name='Number Type'
    )
    phone_number = models.CharField(
        validators=[phone_regex_validator],
        max_length=17,
        blank=True
    )
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    main = models.BooleanField(default=False)
