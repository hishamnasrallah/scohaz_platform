import json
from datetime import datetime
import pytz
from coreapi.compat import force_text
from django.shortcuts import get_object_or_404
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView
from authentication.models import CustomUser, UserPreference, PhoneNumber
from django.utils.http import (urlsafe_base64_encode,
                               urlsafe_base64_decode)
from django.utils.encoding import force_bytes
from scohaz_platform.settings import (DOMAIN,
                                      EMAIL_VERIFICATION_TEMPLATE_ID,
                                      FE_DOMAIN, settings)
import os
# from utils.constant_lists_variables import ApplicationStatus
# from utils.constant_lists_variables import ErrorCodes
from utils.send_email import ScohazEmailHelper
from authentication.tokens import account_activation_token
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import (TokenObtainPairView,
                                            TokenRefreshView)
from authentication.apis.serializers import (RegistrationSerializer,
                                             ChangePasswordSerializer,
                                             ScohazObtainPairSerializer,
                                             ScohazTokenRefreshSerializer,
                                             ActivateEmailSerializer,
                                             ResendActivationEmailSerializer,
                                             ActivateSMSSerializer,
                                             UserPreferenceSerializer,
                                             NewPasswordSerializer,
                                             UserPhoneNumberSerializer)

from authentication.tokens import (ScohazToken,
                                   ScohazRefreshToken)


class ScohazTokenObtainPairView(TokenObtainPairView):
    serializer_class = ScohazObtainPairSerializer


class ScohazTokenRefreshView(TokenRefreshView):
    serializer_class = ScohazTokenRefreshSerializer


class ActivateEmail(APIView):
    permission_classes = (AllowAny,)
    serializer_class = ActivateEmailSerializer

    def get(self, request, *args, **kwargs):

        uidb64 = kwargs['uidb64']
        token = kwargs['token']
        try:
            uid = force_text(urlsafe_base64_decode(uidb64))
            user = CustomUser.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError,
                CustomUser.DoesNotExist):
            user = None

        if user is not None and account_activation_token.check_token(user, token):
            user.is_active = True
            user.save()
            return Response({"status": "activated", "status_code": 200})
        else:
            return Response({"status": "Invalid Url", "status_code": 403})


class ActivateSMSAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ActivateSMSSerializer

    def post(self, request):

        code = request.data['code']
        user = self.request.user
        original_code = self.request.user.sms_code
        original_sms_time = self.request.user.sms_time
        utc = pytz.UTC
        now = datetime.now().replace(tzinfo=utc)
        time_diff = now - original_sms_time
        if original_code == code:
            if time_diff.seconds / 60 < 3:
                user.activated_account = True
                user.save()
                return Response({"status": "Activated", "status_code": 200})

            else:
                return Response({"status": "Expired code", "status_code": 504})

        else:
            return Response({"status": "Invalid code", "status_code": 403})


class ResendActivateSMSAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = ActivateSMSSerializer

    def post(self, request):
        user = self.request.user
        user.reset_sms_code()
        user.sms()
        return Response({"status": "code sent by sms", "status_code": 200})


class ResendActivationEmail(APIView):
    permission_classes = (AllowAny,)
    serializer_class = ResendActivationEmailSerializer

    def post(self, request):
        user_email = request.data['email']
        user_obj = get_object_or_404(CustomUser, email=user_email)

        if user_obj.is_active:
            return Response({"status": "email already verified", "status_code": 200})
        else:
            current_site = DOMAIN

            oturl = {

                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user_obj.pk)),
                'token': account_activation_token.make_token(user_obj),
            }

            context = {
                "substitutions": {
                    "-username-": user_obj.first_name,
                    "-confirm_url_be-":
                        f'{oturl["domain"]}/auth/activate/'
                        f'{oturl["uid"]}/{oturl["token"]}/',
                    "-domain-": str(oturl["domain"]),
                    "-prefix_url-": "auth/activate/",
                    "-uid-": str(oturl["uid"]),
                    "-token-": str(oturl["token"]),
                    "-confirm_url-": f'{FE_DOMAIN}'
                },
                "to": user_email,
                "template_id": EMAIL_VERIFICATION_TEMPLATE_ID,
                "subject": "Ekyc Email Verification",
            }
            email_message = ScohazEmailHelper.create_mail(context=context)
            # //TODO:  Send email
            _send_message = ScohazEmailHelper.send_email(email_message)
            print(_send_message)
            return Response({"status": "email sent successfully"},
                            status=status.HTTP_201_CREATED)


class RegistrationAPIView(APIView):
    permission_classes = (AllowAny,)
    serializer_class = RegistrationSerializer

    def post(self, request):
        user_details = request.data
        serializer = self.serializer_class(data=user_details)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user.is_active = True
        user.save()
        UserPreference.objects.create(user=user)
        tokens = self._generate_tokens(user)
        data = serializer.data
        data['tokens'] = tokens

        to_email = data['email']
        current_site = DOMAIN
        oturl = {

            'domain': current_site,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': account_activation_token.make_token(user),
        }

        context = {
            "substitutions": {
                "-username-": user.first_name,
                "-confirm_url_be-": (
                    f'{oturl["domain"]}/auth/'
                    f'activate/{oturl["uid"]}/{oturl["token"]}/'
                ),
                "-domain-": str(oturl["domain"]),
                "-prefix_url-": "auth/activate/",
                "-uid-": str(oturl["uid"]),
                "-token-": str(oturl["token"]),
                "-confirm_url-": f'{FE_DOMAIN}'
            },
            "to": to_email,
            "template_id": EMAIL_VERIFICATION_TEMPLATE_ID,
            "subject": "Ekyc Email Verification",
        }
        email_message = ScohazEmailHelper.create_mail(context=context)
        ScohazEmailHelper.send_email(email_message)
        # # Additional logic
        try:
            user.reset_sms_code()
            user.sms()
            # user.status = Status.objects.get(code=ApplicationStatus.OTP)
        except AttributeError:
            pass
        return Response(data, status=status.HTTP_201_CREATED)

    def _generate_tokens(self, user):
        if user.is_active:
            tokens = {
                'access': str(ScohazToken.for_user(user)),
                'refresh': str(ScohazRefreshToken.for_user(user))
            }
            return tokens
        else:
            return {"user_status": "Inactive account, please confirm your email"}


class UserPreferenceAPIView(RetrieveUpdateAPIView):
    """
    API to retrieve and update user preferences.
    """
    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # Return the current user's preference
        return UserPreference.objects.get_or_create(user=self.request.user)[0]


class TranslationAPIView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request, language, *args, **kwargs):
        # Path to the translations folder
        translations_dir = os.path.join(settings.BASE_DIR, 'local')
        file_path = os.path.join(translations_dir, f'{language}.json')

        # Check if the translation file exists
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
            return Response(data)
        else:
            return Response({"error": "Language file not found"},
                            status=status.HTTP_404_NOT_FOUND)


class UserPhoneNumberAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserPhoneNumberSerializer

    def get_queryset(self):
        # Get all phone numbers for the authenticated user
        return PhoneNumber.objects.filter(user=self.request.user)

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get(self, request, pk=None):
        if pk:
            phone_number = self.get_object(pk)
            if phone_number is None:
                return Response({"error": "Phone number not found."},
                                status=status.HTTP_404_NOT_FOUND)
            serializer = self.serializer_class(phone_number)
            return Response({"result": serializer.data}, status=status.HTTP_200_OK)

        phone_numbers = self.get_queryset()
        serializer = self.serializer_class(phone_numbers, many=True)
        return Response({"result": serializer.data}, status=status.HTTP_200_OK)

    def get_object(self, pk):
        try:
            return PhoneNumber.objects.get(pk=pk, user=self.request.user)
        except PhoneNumber.DoesNotExist:
            return None

    def put(self, request, pk):
        phone_number = self.get_object(pk)
        if phone_number is None:
            return Response({"error": "Phone number not found."},
                            status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(phone_number, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        phone_number = self.get_object(pk)
        if phone_number is None:
            return Response({"error": "Phone number not found."},
                            status=status.HTTP_404_NOT_FOUND)

        phone_number.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# class RequestForgetUsername(GenericAPIView):
#     permission_classes = [
#         AllowAny  # Or anon users can't register
#     ]
#     http_method_names = ['get']
#
#     def get(self, request, *args, **kwargs):
#         nationalNum = request.GET.get('national_number')
#         try:
#             pass
#
#         except:
#             pass
#
#         beneficiary_user = get_object_or_404(Beneficiary, national_number=nationalNum)
#
#         print(type(beneficiary_user))
#         beneficiary_user.reset_sms_code()
#         beneficiary_user.sms()
#         return Response('Success', status=status.HTTP_200_OK)


# class ForgetUsername(GenericAPIView):
#     permission_classes = [
#         AllowAny  # Or anon users can't register
#     ]
#     http_method_names = ['get']
#
#     def get(self, request, *args, **kwargs):
#         sms_code = request.GET.get('sms_code')
#         nationalNum = request.GET.get('national_number')
#         if not sms_code or not nationalNum:
#             return Response('Missing Params',
#             status=status.HTTP_400_BAD_REQUEST)
#         if Beneficiary.objects.filter(
#         national_number=nationalNum, sms_code=sms_code):
#             beneficiary_user = get_object_or_404(
#             Beneficiary, national_number=nationalNum)
#             username = beneficiary_user.username
#             beneficiary_user.reset_sms_code()
#             beneficiary_user.sms_username()
#             return Response('Success', status=status.HTTP_200_OK)
#         return Response('Incorrect',
#         status=status.HTTP_401_UNAUTHORIZED)


class RequestResetPasswordSMS(GenericAPIView):
    permission_classes = [
        AllowAny  # Or anon users can't register
    ]
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        username = request.GET.get('username')

        user = CustomUser.objects.filter(username=username).first()
        if not user:
            return Response({'detail': 'username not exists',
                             "detail_ara": "اسم المستخدم غير موجود"},
                            status=status.HTTP_404_NOT_FOUND)

        user.reset_sms_code()
        user.sms()
        return Response('Success', status=status.HTTP_200_OK)


class NewPassword(GenericAPIView):
    permission_classes = [
        AllowAny  # Or anon users can't register
    ]
    http_method_names = ['post']
    serializer_class = NewPasswordSerializer

    def post(self, request, *args, **kwargs):
        sms_code = request.data.get('sms_code')
        username = request.data.get('username')
        password = request.data.get('password')
        if not sms_code or not username or not password:
            return Response('Missing Params', status=status.HTTP_400_BAD_REQUEST)
        if CustomUser.objects.filter(username=username, sms_code=sms_code):
            user = get_object_or_404(CustomUser, username=username)
            utc = pytz.UTC
            now = datetime.now().replace(tzinfo=utc)
            original_sms_time = user.sms_time
            time_diff = now - original_sms_time
            if user.sms_code == sms_code:
                if time_diff.seconds / 60 < 3:
                    user.set_password(password)
                    user.save()
                    return Response('Success', status=status.HTTP_200_OK)

                else:
                    return Response({"status": "Expired code", "status_code": 504})

            else:
                return Response({"status": "Invalid code", "status_code": 403})

        return Response('Incorrect', status=status.HTTP_401_UNAUTHORIZED)


class ChangePasswordView(GenericAPIView):

    queryset = CustomUser.objects.all()
    permission_classes = (IsAuthenticated,)
    serializer_class = ChangePasswordSerializer

    def post(self, request):
        # user = self.request.user
        _data = self.request.data
        serializer = self.get_serializer(data=request.data)
        serializer.context["user"] = request.user.id
        # serializer.context["query_params"] = request.query_params
        serializer.is_valid(raise_exception=True)
        request.user.set_password(_data['password'])
        request.user.save()
        # serializer.save()
        return Response({"status": "success"}, status=status.HTTP_200_OK)
