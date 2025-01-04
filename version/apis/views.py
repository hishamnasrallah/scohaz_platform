from datetime import datetime
from django.db.models import Q
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from version.models import Version, ListOfActiveOldApp, LocalVersion
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound


class CheckVersion(GenericAPIView):
    permission_classes = [
        AllowAny  # Or anon users can't register
    ]
    http_method_names = ['get']

    def get(self, request, *args, **kwargs):
        version = request.GET.get('version', None)
        app_type = request.GET.get('app-type', None)

        try:
            user_id = self.request.user.id
        except AttributeError:
            user_id = None

        if not app_type or not version:
            return Response('Missing Params',
                            status=status.HTTP_400_BAD_REQUEST)

        if app_type.strip().lower() == 'ios':
            available_versions = Version.objects.filter(
                Q(expiration_date__gte=datetime.now()
                  ) | Q(expiration_date__isnull=True),
                active_ind=True,
                operating_system='IOS'
            ).values_list('version_number', flat=True)
        elif app_type.strip().lower() == 'android':
            available_versions = Version.objects.filter(
                Q(expiration_date__gte=datetime.now()
                  ) | Q(expiration_date__isnull=True),
                active_ind=True,
                operating_system='Android'
            ).values_list('version_number', flat=True)

        if version.strip() in available_versions:
            is_exist = ListOfActiveOldApp.objects.filter(user_id=user_id)
            if is_exist:
                is_exist.delete()

            version_obj = Version.objects.filter(version_number=version,
                                                 active_ind=True).first()
            x = {"endpoint": version_obj.backend_endpoint,
                 "env": version_obj._environment}
            return Response(x, status=status.HTTP_200_OK)

        if user_id:
            is_exist = ListOfActiveOldApp.objects.filter(user_id=user_id)
            if not is_exist:
                ListOfActiveOldApp.objects.create(user_id=user_id)

        version_obj = Version.objects.filter(
            version_number=version,
            active_ind=True).first()

        if version_obj:
            x = {"endpoint": version_obj.backend_endpoint,
                 "env": version_obj._environment}
            return Response(x, status=status.HTTP_200_OK)
        else:
            return Response(
                {
                    "detail": (
                        "this version not configured yet,"
                        " please contact system administration"
                    )
                },
                status=status.HTTP_404_NOT_FOUND
            )


class LatestVersionAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, lang):
        # Fetch the latest active version for the given language
        version = LocalVersion.objects.filter(
            lang=lang, active_ind=True).order_by('-version_number').first()
        if not version:
            raise NotFound(detail="No version found for the specified language.")

        return Response({
            'lang': version.lang,
            'version_number': version.version_number,
            'active_ind': version.active_ind
        })
