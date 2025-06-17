from datetime import datetime
from django.db.models import Q
from django.utils.timezone import now
from rest_framework import status, viewsets
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.response import Response
import json
from utils.multilangual_helpers import write_translation_with_versioning, read_translation, \
    list_languages, get_translation_file_path
from version.apis.serializers import VersionSerializer
from version.models import Version, ListOfActiveOldApp, LocalVersion
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound

from django.conf import settings


class AvailableLanguagesView(APIView):
    """
    GET /languages/available/
    Returns all available languages defined in settings.LANGUAGES
    """
    permission_classes = [AllowAny]  # Make public, or use authentication as needed

    def get(self, request):
        languages = [
            {"code": code, "name": name}
            for code, name in settings.LANGUAGES
        ]
        return Response(languages)


class LanguageListView(APIView):
    """
    GET /languages/ → list languages
    POST /languages/ → create a new empty language file
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        return Response(list_languages())

    def post(self, request):
        lang = request.data.get("code")
        if not lang:
            return Response({"detail": "Missing 'code'"}, status=400)

        if lang in list_languages():
            return Response({"detail": f"Language '{lang}' already exists."}, status=400)

        with open(get_translation_file_path(lang), 'w', encoding='utf-8') as f:
            json.dump({}, f, ensure_ascii=False, indent=4)

        LocalVersion.objects.create(
            lang=lang,
            version_number=now().strftime('%Y%m%d%H%M%S'),
            active_ind=True
        )
        return Response({"detail": f"Language '{lang}' created successfully."}, status=201)


class TranslationFileView(APIView):
    """
    GET /auth/translation/<lang_code>/ → full translation file
    PUT /translations/<lang_code>/ → full file replace
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, lang_code):
        data = read_translation(lang_code)
        if not data:
            return Response({"detail": "Language not found or empty"}, status=404)
        return Response(data)

    def put(self, request, lang_code):
        data = request.data
        if not isinstance(data, dict):
            return Response({"detail": "Request body must be a JSON object"}, status=400)

        version = write_translation_with_versioning(lang_code, data)
        return Response({
            "detail": "Translation replaced.",
            "version": version,
            "lang": lang_code
        })


class TranslationPartialUpdateView(APIView):
    """
    PATCH /translations/<lang_code>/
    Partial update: add, update, or delete specific keys.
    {
        "add_or_update": {
            "new_key": "value",
            "login_failed": "Updated message"
        },
        "delete": ["old_key"]
    }
    """
    permission_classes = [IsAuthenticatedOrReadOnly]

    def patch(self, request, lang_code):
        add_or_update = request.data.get("add_or_update", {})
        delete_keys = request.data.get("delete", [])

        if not isinstance(add_or_update, dict) or not isinstance(delete_keys, list):
            return Response({
                "detail": "'add_or_update' must be a dict and 'delete' must be a list."
            }, status=400)

        current_data = read_translation(lang_code)

        current_data.update(add_or_update)
        for key in delete_keys:
            current_data.pop(key, None)

        version = write_translation_with_versioning(lang_code, current_data)

        return Response({
            "detail": "Translation updated.",
            "version": version,
            "lang": lang_code,
            "updated_keys": list(add_or_update.keys()),
            "deleted_keys": delete_keys
        })


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


class VersionViewSet(viewsets.ModelViewSet):
    """
    CRUD API ViewSet for Version model.
    """
    queryset = Version.objects.all()
    serializer_class = VersionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optional filtering by environment or operating system.
        """
        queryset = super().get_queryset()
        os = self.request.query_params.get("os")
        env = self.request.query_params.get("env")
        active = self.request.query_params.get("active")

        if os:
            queryset = queryset.filter(operating_system=os)
        if env:
            queryset = queryset.filter(_environment=env)
        if active is not None:
            queryset = queryset.filter(active_ind=(active.lower() == "true"))

        return queryset

