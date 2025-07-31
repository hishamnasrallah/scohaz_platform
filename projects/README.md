# Projects App - Flutter Visual Builder

This Django app manages Flutter projects, screens, and integrates with the existing version control system.

## Installation

1. Copy the `projects` directory to your Django project's apps directory
2. Add to `INSTALLED_APPS` in settings.py:
```python
INSTALLED_APPS = [
    # ... other apps
    'version',  # Your existing version app (must come first)
    'projects',
    'rest_framework',
    'corsheaders',
]
```

3. Add to `MIDDLEWARE` in settings.py:
```python
MIDDLEWARE = [
    # ... other middleware
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
]
```

4. Configure CORS for Angular frontend:
```python
CORS_ALLOWED_ORIGINS = [
    "http://localhost:4200",  # Angular dev server
]
```

5. Include URLs in your main urls.py:
```python
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('projects.urls')),
    # ... other patterns
]
```

6. Run migrations:
```bash
python manage.py makemigrations projects
python manage.py migrate
```

## Models

### FlutterProject
- Represents a Flutter application project
- Links to Version model for app versioning
- Supports multiple languages via LocalVersion
- Stores UI structure as JSON

### Screen
- Represents individual screens within a project
- Contains the component tree structure
- Supports navigation routing
- Designates home screen

## Admin Interface

The admin interface provides:
- Project management with version control
- Language configuration
- Screen management
- Quick actions for common tasks
- JSON preview of UI structures

### Admin Actions
- **Create version 1.0.0**: Initialize version for projects
- **Add English & Arabic**: Add default language support
- **Create default home screen**: Generate starter screen

## API Endpoints

### Projects
- `GET/POST /api/projects/` - List/Create projects
- `GET/PUT/DELETE /api/projects/{id}/` - Project details
- `POST /api/projects/{id}/set_version/` - Create initial version
- `POST /api/projects/{id}/add_language/` - Add language support
- `GET /api/projects/{id}/screens/` - List project screens

### Screens
- `GET/POST /api/screens/` - List/Create screens
- `GET/PUT/DELETE /api/screens/{id}/` - Screen details
- `POST /api/screens/{id}/set_as_home/` - Set as home screen
- `POST /api/screens/{id}/duplicate/` - Duplicate screen

## Management Commands

Create sample data for testing:
```bash
python manage.py create_sample_project --username=testuser
```

## Integration with Version App

This app integrates seamlessly with your existing version control system:

1. **Version Management**: Each Flutter project can be linked to a Version entry
2. **Multi-language Support**: Uses LocalVersion for translations
3. **Translation Keys**: UI components can reference translation keys from your system

### Example: Using Translations in UI

```json
{
  "type": "text",
  "properties": {
    "useTranslation": true,
    "translationKey": "welcome_message",
    "style": {
      "fontSize": 24
    }
  }
}
```

This will generate Flutter code that uses your translation system:
```dart
Text(AppLocalizations.of(context)!.welcome_message)
```

## Required Dependencies

Add to requirements.txt:
```
djangorestframework>=3.14.0
django-cors-headers>=4.0.0
```

## Development Workflow

1. Create a project via API or admin
2. Add supported languages from your LocalVersion entries
3. Design screens with component trees
4. Link to a Version when ready for deployment
5. Generate Flutter code using the builder app (separate)

## Testing

Run tests:
```bash
python manage.py test projects
```

## Notes

- Projects are user-specific (filtered by authenticated user)
- Package names must be unique and follow Android conventions
- Only one home screen allowed per project
- UI structures are validated as valid JSON