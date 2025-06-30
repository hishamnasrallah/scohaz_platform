import json
from datetime import datetime
import pytz
from coreapi.compat import force_text
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework.generics import GenericAPIView, RetrieveUpdateAPIView

from ab_app.crud.managers import user_can
from authentication.models import CustomUser, UserPreference, PhoneNumber, CRUDPermission, UserType
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
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
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
                                             UserPhoneNumberSerializer, GroupSerializer, CRUDPermissionSerializer,
                                             CustomUserDetailSerializer, CustomUserManagementSerializer)

from authentication.tokens import (ScohazToken,
                                   ScohazRefreshToken)


class ScohazTokenObtainPairView(TokenObtainPairView):
    serializer_class = ScohazObtainPairSerializer


class ScohazTokenRefreshView(TokenRefreshView):
    serializer_class = ScohazTokenRefreshSerializer


class GroupViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint to list and retrieve Django groups.
    """
    queryset = Group.objects.all()
    serializer_class = GroupSerializer
    permission_classes = [IsAuthenticated]

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


class CRUDPermissionViewSet(viewsets.ModelViewSet):
    """
    CRUD API for managing group-model-context level permissions.
    """
    queryset = CRUDPermission.objects.all()
    serializer_class = CRUDPermissionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optional filtering by group_id, content_type_id, or context.
        """
        queryset = super().get_queryset()
        group_id = self.request.query_params.get("group")
        content_type_id = self.request.query_params.get("content_type")
        context = self.request.query_params.get("context")

        if group_id:
            queryset = queryset.filter(group_id=group_id)
        if content_type_id:
            queryset = queryset.filter(content_type_id=content_type_id)
        if context:
            queryset = queryset.filter(context=context)

        return queryset

    @action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """
        Create multiple permissions at once.
        Expects: {
            "group": 1,
            "content_types": [1, 2, 3],
            "contexts": ["api", "admin"],
            "can_create": true,
            "can_read": true,
            "can_update": true,
            "can_delete": false
        }
        """
        data = request.data
        group_id = data.get('group')
        content_types = data.get('content_types', [])
        contexts = data.get('contexts', [])

        if not group_id or not content_types or not contexts:
            return Response(
                {"error": "group, content_types, and contexts are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        created_permissions = []
        errors = []

        for content_type_id in content_types:
            for context in contexts:
                permission_data = {
                    'group': group_id,
                    'content_type': content_type_id,
                    'context': context,
                    'can_create': data.get('can_create', False),
                    'can_read': data.get('can_read', False),
                    'can_update': data.get('can_update', False),
                    'can_delete': data.get('can_delete', False)
                }

                # Check if permission already exists
                existing = CRUDPermission.objects.filter(
                    group_id=group_id,
                    content_type_id=content_type_id,
                    context=context
                ).first()

                if existing:
                    errors.append(f"Permission already exists for group {group_id}, content_type {content_type_id}, context {context}")
                    continue

                serializer = self.get_serializer(data=permission_data)
                if serializer.is_valid():
                    permission = serializer.save()
                    created_permissions.append(serializer.data)
                else:
                    errors.append(f"Error creating permission: {serializer.errors}")

        return Response({
            'created': created_permissions,
            'errors': errors,
            'created_count': len(created_permissions)
        }, status=status.HTTP_201_CREATED if created_permissions else status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['put'], url_path='bulk-update')
    def bulk_update(self, request):
        """
        Update multiple permissions at once.
        Expects: {
            "permission_ids": [1, 2, 3],
            "can_create": true,
            "can_read": true,
            "can_update": true,
            "can_delete": false
        }
        """
        data = request.data
        permission_ids = data.get('permission_ids', [])

        if not permission_ids:
            return Response(
                {"error": "permission_ids are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        update_fields = {}
        for field in ['can_create', 'can_read', 'can_update', 'can_delete']:
            if field in data:
                update_fields[field] = data[field]

        if not update_fields:
            return Response(
                {"error": "No fields to update"},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated = CRUDPermission.objects.filter(id__in=permission_ids).update(**update_fields)

        # Get updated permissions
        updated_permissions = CRUDPermission.objects.filter(id__in=permission_ids)
        serializer = self.get_serializer(updated_permissions, many=True)

        return Response({
            'updated': serializer.data,
            'updated_count': updated
        })

    @action(detail=False, methods=['delete'], url_path='bulk-delete')
    def bulk_delete(self, request):
        """
        Delete multiple permissions at once.
        Expects: {"permission_ids": [1, 2, 3]}
        """
        permission_ids = request.data.get('permission_ids', [])

        if not permission_ids:
            return Response(
                {"error": "permission_ids are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        deleted_count = CRUDPermission.objects.filter(id__in=permission_ids).delete()[0]

        return Response({
            'deleted_count': deleted_count
        })


class ContentTypeAppListView(APIView):
    """
    GET /content-types/apps/
    Returns only custom (user-created) app labels — excludes Django/system/third-party apps.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get all app labels from ContentType table
        all_content_app_labels = set(ContentType.objects.values_list("app_label", flat=True))

        # Derive your project root (e.g., where manage.py is)
        project_root = settings.BASE_DIR

        # List of your own apps (assumes they have __init__.py and models.py)
        custom_apps = []
        for app in all_content_app_labels:
            app_path = os.path.join(project_root, app)
            if os.path.isdir(app_path) and os.path.isfile(os.path.join(app_path, "models.py")):
                custom_apps.append(app)

        return Response(sorted(custom_apps))


class ContentTypeModelListView(APIView):
    """
    GET /content-types/models/?app=app_label
    Returns list of models for a given app label.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        app_label = request.query_params.get("app")
        # if not app_label:
        #
        #     return Response(
        #         {"detail": "Missing 'app' query parameter."},
        #         status=status.HTTP_400_BAD_REQUEST
        #     )
        if not app_label:
            models = ContentType.objects.all().values("id", "model", "app_label")
            return Response(models)

        models = ContentType.objects.filter(app_label=app_label).values("id", "model", "app_label")
        return Response(models)


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



class UserDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = CustomUserDetailSerializer(request.user)
        return Response(serializer.data)

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

class CustomUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users (CRUD operations).
    Follows the same pattern as generated ViewSets.
    """
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserManagementSerializer
    permission_classes = (IsAuthenticated,)  # You can change to CRUDPermissionDRF if you have it

    def get_queryset(self):
        """Add filtering capabilities"""
        queryset = super().get_queryset()

        # Filter by user_type
        user_type = self.request.query_params.get('user_type')
        if user_type:
            queryset = queryset.filter(user_type__code=user_type)

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Filter by group
        group_id = self.request.query_params.get('group')
        if group_id:
            queryset = queryset.filter(groups__id=group_id)

        # Search functionality
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                models.Q(username__icontains=search) |
                models.Q(email__icontains=search) |
                models.Q(first_name__icontains=search) |
                models.Q(last_name__icontains=search)
            )

        return queryset.distinct()

    def list(self, request, *args, **kwargs):
        """Custom list with filtering"""
        queryset = self.get_queryset()

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], url_path='activate')
    def activate_user(self, request, pk=None):
        """Activate a user account"""
        user = self.get_object()
        user.is_active = True
        user.activated_account = True
        user.save()
        return Response({'message': f'User {user.username} activated successfully'})

    @action(detail=True, methods=['post'], url_path='deactivate')
    def deactivate_user(self, request, pk=None):
        """Deactivate a user account"""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({'message': f'User {user.username} deactivated successfully'})

    @action(detail=True, methods=['post'], url_path='reset-password')
    def reset_password(self, request, pk=None):
        """Reset user password"""
        user = self.get_object()
        new_password = request.data.get('password')

        if not new_password:
            return Response(
                {'error': 'Password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user.set_password(new_password)
        user.save()

        # Optionally send SMS/email notification
        try:
            user.reset_sms_code()
            user.sms()
        except:
            pass

        return Response({'message': 'Password reset successfully'})

    @action(detail=True, methods=['post'], url_path='assign-groups')
    def assign_groups(self, request, pk=None):
        """Assign groups to user"""
        user = self.get_object()
        group_ids = request.data.get('group_ids', [])

        if not isinstance(group_ids, list):
            return Response(
                {'error': 'group_ids must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )

        groups = Group.objects.filter(id__in=group_ids)
        user.groups.set(groups)

        return Response({
            'message': f'Groups assigned successfully',
            'groups': GroupSerializer(groups, many=True).data
        })

    @action(detail=False, methods=['get'], url_path='user-types')
    def get_user_types(self, request):
        """Get all available user types"""
        user_types = UserType.objects.filter(active_ind=True)
        data = [
            {
                'id': ut.id,
                'name': ut.name,
                'name_ara': ut.name_ara,
                'code': ut.code,
                'group': ut.group.name if ut.group else None
            }
            for ut in user_types
        ]
        return Response(data)

    @action(detail=False, methods=['post'], url_path='bulk-activate')
    def bulk_activate(self, request):
        """Bulk activate users"""
        user_ids = request.data.get('user_ids', [])

        if not isinstance(user_ids, list):
            return Response(
                {'error': 'user_ids must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated = CustomUser.objects.filter(id__in=user_ids).update(
            is_active=True,
            activated_account=True
        )

        return Response({
            'message': f'{updated} users activated successfully'
        })

    @action(detail=False, methods=['post'], url_path='bulk-deactivate')
    def bulk_deactivate(self, request):
        """Bulk deactivate users"""
        user_ids = request.data.get('user_ids', [])

        if not isinstance(user_ids, list):
            return Response(
                {'error': 'user_ids must be a list'},
                status=status.HTTP_400_BAD_REQUEST
            )

        updated = CustomUser.objects.filter(id__in=user_ids).update(is_active=False)

        return Response({
            'message': f'{updated} users deactivated successfully'
        })

    def destroy(self, request, *args, **kwargs):
        """Override destroy to prevent actual deletion - just deactivate"""
        instance = self.get_object()
        instance.is_active = False
        instance.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


# If you want to use CRUDPermissionDRF, create this permission class
class CRUDPermissionDRF(BasePermission):
    """
    Custom permission class for user management
    """
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        model = CustomUser

        if view.action == 'create':
            return user_can(request.user, 'create', model, context='api')
        elif view.action in ['list', 'retrieve']:
            return user_can(request.user, 'read', model, context='api')
        elif view.action in ['update', 'partial_update']:
            return user_can(request.user, 'update', model, context='api')
        elif view.action == 'destroy':
            return user_can(request.user, 'delete', model, context='api')

        # For custom actions, default to requiring read permission
        return user_can(request.user, 'read', model, context='api')

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        model = type(obj)
        action_map = {
            'retrieve': 'read',
            'update': 'update',
            'partial_update': 'update',
            'destroy': 'delete',
        }
        crud_action = action_map.get(view.action, 'read')

        return user_can(request.user, crud_action, model, context='api', object_id=obj.pk)