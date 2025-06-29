# app_builder/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.db import transaction
from django.contrib import messages
from django.http import HttpResponseRedirect
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import (
    ApplicationDefinitionForm,
    ModelDefinitionFormSet,
    FieldDefinitionFormSet,
    RelationshipDefinitionFormSet
)
from rest_framework import viewsets, status
from .models import ApplicationDefinition, ModelDefinition, FieldDefinition, RelationshipDefinition
from app_builder.serializers.application_serializer import (
    ApplicationSerializer,
    ModelDefinitionSerializer,
    FieldDefinitionSerializer,
    RelationshipDefinitionSerializer, ApplicationERDSerializer,
)
# Enhanced version of DiagramImportView in app_builder/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db import transaction
from django.core.exceptions import ValidationError

from app_builder.services import create_application_from_diagram
from app_builder.utils.erd_converter import convert_erd_to_django


class DiagramImportView(APIView):
    """
    Enhanced API endpoint that imports ERD JSON and creates Django application structure.
    Includes validation, error handling, and detailed feedback.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        diagram_data = request.data

        # Validate input
        if not diagram_data:
            return Response(
                {"error": "No data provided"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not isinstance(diagram_data, dict):
            return Response(
                {"error": "Invalid data format. Expected JSON object."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # First, validate the conversion without saving
        try:
            app_name = diagram_data.get("name", "untitled_app")

            # Test conversion
            conversion_result = convert_erd_to_django(diagram_data, app_name=app_name)

            # If validation failed, return detailed errors
            if not conversion_result["is_valid"]:
                return Response({
                    "error": "ERD validation failed",
                    "validation_errors": conversion_result["errors"],
                    "warnings": conversion_result["warnings"],
                    "statistics": {
                        "models_found": conversion_result["model_count"],
                        "fields_found": conversion_result["field_count"],
                        "relationships_found": conversion_result["relationship_count"]
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            return Response({
                "error": "Failed to validate ERD structure",
                "detail": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

        # If validation passed, create the application
        try:
            with transaction.atomic():
                application = create_application_from_diagram(diagram_data)

                # Prepare detailed response
                response_data = {
                    "success": True,
                    "message": "Diagram imported successfully!",
                    "application": {
                        "id": application.id,
                        "app_name": application.app_name,
                        "created_at": application.created_at.isoformat()
                    },
                    "statistics": {
                        "models": conversion_result["model_count"],
                        "fields": conversion_result["field_count"],
                        "relationships": conversion_result["relationship_count"]
                    }
                }

                # Include warnings if any
                if conversion_result["warnings"]:
                    response_data["warnings"] = conversion_result["warnings"]

                # Include next steps
                response_data["next_steps"] = [
                    f"Generate Django app: python manage.py create_app {application.app_name} --models-file generated_application_source/{application.app_name}.json",
                    f"Make migrations: python manage.py makemigrations {application.app_name}",
                    f"Apply migrations: python manage.py migrate {application.app_name}"
                ]

                return Response(response_data, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            return Response({
                "error": "Validation error during import",
                "detail": str(e),
                "warnings": conversion_result.get("warnings", [])
            }, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            # Log the full exception for debugging
            import traceback
            traceback.print_exc()

            return Response({
                "error": "Failed to import diagram",
                "detail": str(e),
                "type": type(e).__name__
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def get(self, request, *args, **kwargs):
        """
        Provide API documentation when accessed via GET.
        """
        return Response({
            "endpoint": "ERD Diagram Import",
            "method": "POST",
            "description": "Import an ERD JSON export and create Django application structure",
            "request_format": {
                "id": "string (optional)",
                "name": "string - will be used as app name",
                "tables": [
                    {
                        "id": "string",
                        "name": "string",
                        "fields": [
                            {
                                "id": "string",
                                "name": "string",
                                "type": {"id": "string", "name": "string"},
                                "nullable": "boolean",
                                "unique": "boolean",
                                "primaryKey": "boolean"
                            }
                        ],
                        "indexes": "array (optional)"
                    }
                ],
                "relationships": [
                    {
                        "id": "string",
                        "name": "string",
                        "sourceTableId": "string",
                        "targetTableId": "string",
                        "sourceFieldId": "string",
                        "targetFieldId": "string",
                        "sourceCardinality": "one|many",
                        "targetCardinality": "one|many"
                    }
                ]
            },
            "response_format": {
                "success": {
                    "success": "boolean",
                    "message": "string",
                    "application": {
                        "id": "number",
                        "app_name": "string",
                        "created_at": "ISO 8601 datetime"
                    },
                    "statistics": {
                        "models": "number",
                        "fields": "number",
                        "relationships": "number"
                    },
                    "warnings": "array of strings (optional)",
                    "next_steps": "array of strings"
                },
                "error": {
                    "error": "string",
                    "detail": "string",
                    "validation_errors": "array (optional)",
                    "warnings": "array (optional)"
                }
            },
            "example_curl": 'curl -X POST -H "Content-Type: application/json" -d @erd_export.json http://localhost:8000/app_builder/api/diagram/import/'
        })

# class DiagramImportView(APIView):
#     """
#     Handles a POST request with the diagram JSON and maps it
#     into the ApplicationDefinition/ModelDefinition/etc. schema.
#     """
#
#     @transaction.atomic  # ensures atomic DB transactions
#     def post(self, request, *args, **kwargs):
#         data = request.data  # This is the diagram JSON
#
#         # 1) Validate the incoming JSON if needed
#         #    (You can write a custom serializer or do manual validation)
#
#         # 2) Map the JSON to your existing models
#         try:
#             application = create_application_from_diagram(data)
#         except Exception as e:
#             return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
#
#         # 3) Return success response
#         return Response(
#             {"detail": "Diagram imported successfully!", "application_id": application.id},
#             status=status.HTTP_201_CREATED
#         )

class ApplicationDefinitionViewSet(viewsets.ModelViewSet):
    queryset = ApplicationDefinition.objects.all()
    serializer_class = ApplicationSerializer


class ApplicationDefinitionERDView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        queryset = ApplicationDefinition.objects.all()
        serializer = ApplicationERDSerializer(queryset, many=True)
        return Response(serializer.data)


class ModelDefinitionViewSet(viewsets.ModelViewSet):
    queryset = ModelDefinition.objects.all()
    serializer_class = ModelDefinitionSerializer

class FieldDefinitionViewSet(viewsets.ModelViewSet):
    queryset = FieldDefinition.objects.all()
    serializer_class = FieldDefinitionSerializer

class RelationshipDefinitionViewSet(viewsets.ModelViewSet):
    queryset = RelationshipDefinition.objects.all()
    serializer_class = RelationshipDefinitionSerializer


###############################################################



def list_applications(request):
    apps = ApplicationDefinition.objects.all().order_by('-created_at')
    return render(request, 'app_builder/list_applications.html', {
        'apps': apps
    })


@transaction.atomic
def application_definition_crud(request, pk=None):
    """
    Create or edit a single ApplicationDefinition with all nested models in one page.
    - If pk is None => create new. If pk is set => edit existing.
    """
    if pk:
        app_def = get_object_or_404(ApplicationDefinition, pk=pk)
        creating = False
    else:
        app_def = ApplicationDefinition()
        creating = True

    if request.method == 'POST':
        form = ApplicationDefinitionForm(request.POST, instance=app_def, prefix='appdef')
        formset = ModelDefinitionFormSet(request.POST, instance=app_def, prefix='models')

        if form.is_valid() and formset.is_valid():
            # We must do a partial save of the top-level objects first
            app_saved = form.save()

            # Now handle model definitions
            modeldefs = formset.save(commit=False)
            # Delete forms
            for obj in formset.deleted_objects:
                obj.delete()

            modeldef_ids = []
            for modeldef in modeldefs:
                modeldef.application = app_saved
                modeldef.save()
                modeldef_ids.append(modeldef.pk)

            formset.save_m2m()  # if needed

            # Now handle sub-formsets for fields/relationships for each modeldef
            all_subformsets_valid = True
            for mdef_id in modeldef_ids:
                mdef = ModelDefinition.objects.get(pk=mdef_id)
                field_formset = FieldDefinitionFormSet(
                    request.POST,
                    instance=mdef,
                    prefix=f'fields_{mdef_id}'
                )
                rel_formset = RelationshipDefinitionFormSet(
                    request.POST,
                    instance=mdef,
                    prefix=f'rels_{mdef_id}'
                )

                if field_formset.is_valid() and rel_formset.is_valid():
                    field_objs = field_formset.save(commit=False)
                    for fobj in field_formset.deleted_objects:
                        fobj.delete()
                    for fobj in field_objs:
                        fobj.model_definition = mdef
                        fobj.save()
                    field_formset.save_m2m()

                    rel_objs = rel_formset.save(commit=False)
                    for robj in rel_formset.deleted_objects:
                        robj.delete()
                    for robj in rel_objs:
                        robj.model_definition = mdef
                        robj.save()
                    rel_formset.save_m2m()

                else:
                    all_subformsets_valid = False

            if not all_subformsets_valid:
                messages.error(request, "Error in fields or relationships sub-formsets.")
            else:
                messages.success(request, "Application saved successfully.")
                return redirect('app_builder:list_applications')
        else:
            messages.error(request, "Error in top-level form or model definitions.")

    else:
        form = ApplicationDefinitionForm(instance=app_def, prefix='appdef')
        formset = ModelDefinitionFormSet(instance=app_def, prefix='models')

    # We also must build empty sub-formsets for display (for each ModelDefinition).
    sub_formsets = []
    if app_def.pk:  # if the object is saved
        # Load existing model definitions
        existing_models = app_def.modeldefinition_set.all()
    else:
        existing_models = []

    for mdef in existing_models:
        field_formset = FieldDefinitionFormSet(
            instance=mdef,
            prefix=f'fields_{mdef.pk}'
        )
        rel_formset = RelationshipDefinitionFormSet(
            instance=mdef,
            prefix=f'rels_{mdef.pk}'
        )
        sub_formsets.append((mdef, field_formset, rel_formset))

    return render(request, 'app_builder/application_crud.html', {
        'form': form,
        'formset': formset,
        'sub_formsets': sub_formsets,
        'creating': creating
    })


def delete_application(request, pk):
    app_def = get_object_or_404(ApplicationDefinition, pk=pk)
    if request.method == 'POST':
        app_def.delete()
        messages.success(request, "Application deleted.")
        return redirect('app_builder:list_applications')
    return render(request, 'app_builder/confirm_delete.html', {
        'app_def': app_def
    })
