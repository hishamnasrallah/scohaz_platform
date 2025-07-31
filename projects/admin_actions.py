from django.contrib import messages
from django.shortcuts import redirect
from django.http import HttpResponse, JsonResponse
from django.core import serializers
from django.utils import timezone
import json
import zipfile
import io

from .models import FlutterProject, Screen, ComponentTemplate


def duplicate_project(modeladmin, request, queryset):
    """Duplicate selected projects with all screens"""
    duplicated_count = 0

    for project in queryset:
        # Store original data
        original_id = project.pk
        original_screens = list(project.screen_set.all())
        original_languages = list(project.supported_languages.all())

        # Duplicate project
        project.pk = None
        project.name = f"{project.name} (Copy)"
        project.created_at = timezone.now()
        project.updated_at = timezone.now()
        project.save()

        # Add languages
        project.supported_languages.set(original_languages)

        # Duplicate screens
        for screen in original_screens:
            screen.pk = None
            screen.project = project
            screen.created_at = timezone.now()
            screen.updated_at = timezone.now()
            screen.save()

        duplicated_count += 1

    messages.success(
        request,
        f'Successfully duplicated {duplicated_count} project(s) with all screens.'
    )

duplicate_project.short_description = 'Duplicate selected projects'


def generate_preview(modeladmin, request, queryset):
    """Generate preview for selected projects"""
    if queryset.count() > 1:
        messages.warning(request, 'Please select only one project to preview.')
        return

    project = queryset.first()

    # Redirect to preview URL
    preview_url = f'/admin/preview/project/{project.pk}/'
    return redirect(preview_url)

generate_preview.short_description = 'Generate preview'


def export_project_json(modeladmin, request, queryset):
    """Export project configuration as JSON"""
    if queryset.count() > 1:
        # Export multiple projects as ZIP
        zip_buffer = io.BytesIO()

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for project in queryset:
                project_data = _serialize_project(project)
                filename = f"{project.package_name.replace('.', '_')}.json"
                zip_file.writestr(filename, json.dumps(project_data, indent=2))

        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer.read(), content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename="flutter_projects.zip"'

    else:
        # Export single project as JSON
        project = queryset.first()
        project_data = _serialize_project(project)

        response = HttpResponse(
            json.dumps(project_data, indent=2),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{project.package_name}.json"'

    return response

export_project_json.short_description = 'Export as JSON'


def _serialize_project(project):
    """Serialize project with all related data"""
    # Get screens
    screens = []
    for screen in project.screen_set.all():
        screens.append({
            'name': screen.name,
            'route': screen.route,
            'is_home': screen.is_home,
            'ui_structure': screen.ui_structure,
            'created_at': screen.created_at.isoformat(),
            'updated_at': screen.updated_at.isoformat()
        })

    # Get languages
    languages = list(project.supported_languages.values_list('lang', flat=True))

    # Build complete project data
    return {
        'version': '1.0',
        'export_date': timezone.now().isoformat(),
        'project': {
            'name': project.name,
            'package_name': project.package_name,
            'description': project.description,
            'default_language': project.default_language,
            'supported_languages': languages,
            'ui_structure': project.ui_structure,
            'created_at': project.created_at.isoformat(),
            'updated_at': project.updated_at.isoformat()
        },
        'screens': screens,
        'app_version': {
            'version_number': project.app_version.version_number if project.app_version else None,
            'operating_system': project.app_version.operating_system if project.app_version else None
        }
    }


def bulk_update_version(modeladmin, request, queryset):
    """Bulk update version for selected projects"""
    if 'apply' in request.POST:
        version_number = request.POST.get('version_number')

        if not version_number:
            messages.error(request, 'Version number is required.')
            return

        # Update versions
        from version.models import Version
        updated_count = 0

        for project in queryset:
            if project.app_version:
                project.app_version.version_number = version_number
                project.app_version.save()
            else:
                # Create new version
                version = Version.objects.create(
                    version_number=version_number,
                    operating_system='Android',
                    _environment='1',
                    active_ind=True
                )
                project.app_version = version
                project.save()

            updated_count += 1

        messages.success(
            request,
            f'Successfully updated version to {version_number} for {updated_count} project(s).'
        )
        return

    # Show form
    return modeladmin.bulk_update_version_form(request, queryset)

bulk_update_version.short_description = 'Bulk update version'


def validate_projects(modeladmin, request, queryset):
    """Validate project configurations"""
    validation_results = []

    for project in queryset:
        errors = []
        warnings = []

        # Check basic configuration
        if not project.package_name:
            errors.append('Missing package name')

        if not project.supported_languages.exists():
            errors.append('No languages configured')

        # Check screens
        screen_count = project.screen_set.count()
        if screen_count == 0:
            errors.append('No screens defined')
        else:
            # Check for home screen
            home_screens = project.screen_set.filter(is_home=True).count()
            if home_screens == 0:
                errors.append('No home screen defined')
            elif home_screens > 1:
                errors.append(f'Multiple home screens defined ({home_screens})')

            # Validate each screen
            for screen in project.screen_set.all():
                if not screen.ui_structure:
                    warnings.append(f'Screen "{screen.name}" has empty UI structure')

        # Check version
        if not project.app_version:
            warnings.append('No version assigned')

        validation_results.append({
            'project': project.name,
            'errors': errors,
            'warnings': warnings,
            'valid': len(errors) == 0
        })

    # Show results
    if request.META.get('HTTP_ACCEPT') == 'application/json':
        return JsonResponse({'results': validation_results})

    # Display in messages
    for result in validation_results:
        if result['errors']:
            messages.error(
                request,
                f"{result['project']}: {', '.join(result['errors'])}"
            )
        if result['warnings']:
            messages.warning(
                request,
                f"{result['project']}: {', '.join(result['warnings'])}"
            )
        if result['valid'] and not result['warnings']:
            messages.success(request, f"{result['project']}: Valid configuration")

    return

validate_projects.short_description = 'Validate configuration'


def generate_component_documentation(modeladmin, request, queryset):
    """Generate documentation for selected component templates"""
    doc_parts = []

    # Header
    doc_parts.append("# Flutter Visual Builder - Component Documentation\n")
    doc_parts.append(f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    doc_parts.append(f"Total Components: {queryset.count()}\n\n")

    # Group by category
    categories = {}
    for component in queryset.order_by('category', 'name'):
        if component.category not in categories:
            categories[component.category] = []
        categories[component.category].append(component)

    # Generate documentation for each category
    for category, components in categories.items():
        doc_parts.append(f"## {category.title()} Components\n\n")

        for comp in components:
            doc_parts.append(f"### {comp.icon or '🔧'} {comp.name}\n")
            doc_parts.append(f"**Flutter Widget:** `{comp.flutter_widget}`\n")

            if comp.description:
                doc_parts.append(f"\n{comp.description}\n")

            # Properties
            if comp.default_properties:
                doc_parts.append("\n**Default Properties:**\n```json\n")
                doc_parts.append(json.dumps(comp.default_properties, indent=2))
                doc_parts.append("\n```\n")

            # Container info
            if comp.is_container:
                doc_parts.append(f"\n**Container:** Yes\n")
                if comp.allowed_children:
                    doc_parts.append(f"**Allowed Children:** {', '.join(comp.allowed_children)}\n")

            doc_parts.append("\n---\n\n")

    # Return as markdown file
    response = HttpResponse(
        ''.join(doc_parts),
        content_type='text/markdown'
    )
    response['Content-Disposition'] = 'attachment; filename="component_documentation.md"'

    return response

generate_component_documentation.short_description = 'Generate documentation'


def batch_activate_components(modeladmin, request, queryset):
    """Activate multiple components at once"""
    updated = queryset.update(is_active=True)
    messages.success(request, f'{updated} components activated.')

batch_activate_components.short_description = 'Activate selected'


def batch_deactivate_components(modeladmin, request, queryset):
    """Deactivate multiple components at once"""
    updated = queryset.update(is_active=False)
    messages.warning(request, f'{updated} components deactivated.')

batch_deactivate_components.short_description = 'Deactivate selected'