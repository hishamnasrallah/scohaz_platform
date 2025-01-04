from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers, exceptions
# from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueValidator
from rest_framework_simplejwt.serializers import (PasswordField,
                                                  TokenRefreshSerializer,
                                                  TokenObtainSerializer)
from authentication.models import CustomUser, UserPreference, PhoneNumber
from django.utils.translation import gettext_lazy as _
from authentication.tokens import ScohazRefreshToken
from lookup.apis.serializers import LookupCategoryMixin


class RegistrationSerializer(serializers.ModelSerializer):
    """Serializers registration requests and creates a new user."""
    password = PasswordField(
        max_length=128,
        min_length=8,
        write_only=True
    )
    first_name = serializers.CharField(
        max_length=128,
        min_length=2
    )
    last_name = serializers.CharField(
        max_length=128,
        min_length=2
    )
    username = serializers.CharField(
        validators=[
            UniqueValidator(queryset=CustomUser.objects.all(),
                            message=_("username is used by another user."))
        ]
    )

    email = serializers.EmailField()

    def create(self, validated_data):
        validated_data['is_active'] = True
        created_user = CustomUser.objects.create_user(**validated_data)
        return created_user

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name',
                  'last_name', 'email', 'password']


class ChangePasswordSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True,
                                     required=True,
                                     validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    old_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = CustomUser
        fields = ('old_password', 'password', 'password2')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."})

        return attrs

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                {"old_password": "Old password is not correct"})
        return value

    # def post(self, instance, validated_data):
    #
    #     instance.set_password(validated_data['password'])
    #     instance.save()
    #
    #     return instance


class CustomTokenObtainPairSerializer(TokenObtainSerializer):

    def validate(self, attrs):
        authenticate_kwargs = {
            self.username_field: attrs[self.username_field],
            'password': attrs['password'],
        }
        try:
            authenticate_kwargs['request'] = self.context['request']
        except KeyError:
            pass

        self.user = authenticate(**authenticate_kwargs)
        try:
            is_deleted = self.user.is_deleted
        except AttributeError:
            is_deleted = False
        if self.user is None or not self.user.is_active or is_deleted:
            raise exceptions.AuthenticationFailed(
                {"detail": "No active account found "
                           "with the given credentials",
                 "detail_ara": "اسم المستخدم او كلمة المرور غير"
                               " صحيحة اوهذا المستخدم غير موجود"}
            )

        return {}


class ScohazObtainPairSerializer(CustomTokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        print(data)
        refresh = self.get_token(self.user)

        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)

        return data

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass

    @classmethod
    def get_token(cls, user):
        return ScohazRefreshToken.for_user(user)


class ScohazTokenRefreshSerializer(TokenRefreshSerializer):

    def validate(self, attrs):
        refresh = ScohazRefreshToken(attrs['refresh'])
        data = {'access': str(refresh.access_token)}
        return data

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        pass


class ThumbnailMinimalInfoUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'first_name', 'last_name',)


class ActivateEmailSerializer(serializers.Serializer):
    class Meta:
        fields = ('status', 'status_code')


class ActivateSMSSerializer(serializers.Serializer):
    class Meta:
        fields = ('status', 'status_code')


class ResendActivationEmailSerializer(serializers.Serializer):
    class Meta:
        fields = ('email',)


class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ['id', 'lang']  # Include the fields you want to expose in the API
        read_only_fields = ['user']


class NewPasswordSerializer(serializers.Serializer):
    class Meta:
        fields = ('sms_code', 'username', 'password')


class UserPhoneNumberSerializer(LookupCategoryMixin, serializers.ModelSerializer):
    class Meta:
        model = PhoneNumber
        fields = ['id', 'phone_number', 'number_type', 'is_default', 'main']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Dynamically add lookup fields based on configuration
        dynamic_fields = self.get_dynamic_lookup_fields(self.Meta.model)
        for field_name, field in dynamic_fields.items():
            self.fields[field_name] = field
