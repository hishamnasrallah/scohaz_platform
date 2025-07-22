import six
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from authentication.models import CustomUser
from license_subscription_manager.models import License


# from beneficiary.models import Case, PhoneNumber, BeneficiaryAddress


class ScohazToken(AccessToken):
    token_type = 'scohaz'
    lifetime = api_settings.ACCESS_TOKEN_LIFETIME

    def set_jti(self):
        pass

    def verify(self):
        # Verify Token's Expiration
        self.check_exp()
        # Verify Token's Type
        self.verify_token_type()


class ScohazRefreshToken(RefreshToken):
    token_type = 'scohaz_refresh'
    lifetime = api_settings.REFRESH_TOKEN_LIFETIME

    def set_jti(self):
        pass

    @property
    def access_token(self):
        access = ScohazToken()
        access.set_exp(from_time=self.current_time)
        no_copy = self.no_copy_claims
        for claim, value in self.payload.items():
            if claim in no_copy:
                continue
            access[claim] = value
        try:
            user = CustomUser.objects.get(id=access.payload["uid"])
        except AttributeError:
            user = None
        try:
            access.payload["user_type"] = user.user_type.code
        except AttributeError:
            access.payload["user_type"] = None

        try:
            access.payload["national_number"] = user.national_number
        except AttributeError:
            access.payload["national_number"] = None

        try:
            access.payload["avatar"] = user.avatar.url
        except AttributeError:
            access.payload["avatar"] = None

        try:
            # Get user groups as a list of group names
            access.payload["groups"] = list(user.groups.values_list('id', flat=True))
        except AttributeError:
            access.payload["groups"] = []

        try:
            license = License.objects.filter(developers__in=[user], client__project_id__isnull=False).first()
            access.payload["project_id"] = license.client.project_id
        except:
            access.payload["project_id"] = None

        return access


    def verify(self):
        self.check_exp()
        self.verify_token_type()


class TokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (six.text_type(user.pk) + six.text_type(timestamp)
                + six.text_type(user.is_active))


account_activation_token = TokenGenerator()
