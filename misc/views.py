# translations/views.py
import json
import os
from django.shortcuts import render
from django.http import (HttpResponseForbidden,
                         HttpResponse, JsonResponse)
from django.conf import settings

TRANSLATIONS_DIR = os.path.join(settings.BASE_DIR, 'local')


def list_files(request):
    """View to list all translation files."""
    # Check if the user is a superuser (highest admin privilege)
    if not request.user.is_superuser:
        return HttpResponseForbidden(
            "You are not authorized to view this page.")

    # Get the list of all JSON files in the translations folder
    json_files = [
        f for f in os.listdir(TRANSLATIONS_DIR)
        if f.endswith('.json')]

    return render(
        request,
        'translations/list_files.html',
        {'json_files': json_files})


def edit_translation(request, filename):
    file_path = os.path.join(TRANSLATIONS_DIR,
                             filename)
    # user_preference = UserPreference.objects.get(user=request.user)
    # lang = user_preference.lang
    # activate(lang)

    # Load translations from the file
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            translations = json.load(file)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

    # Apply search filter if there's a search query
    search_query = request.GET.get('search', '')
    if search_query:
        filtered_translations = {key: value for key, value
                                 in translations.items()
                                 if search_query.lower()
                                 in key.lower()
                                 or search_query.lower()
                                 in value.lower()}
    else:
        filtered_translations = translations

    # Handle the POST request from AJAX form submission
    if request.method == "POST":
        key = request.POST.get('key')
        value = request.POST.get('value')
        key = key.replace(" ", "_")
        if key and value:
            translations[key] = value  # Update translation dictionary

            try:
                # Save updated translations back to the file
                with open(file_path, 'w', encoding='utf-8') as file:
                    json.dump(translations, file, ensure_ascii=False, indent=4)
                return JsonResponse({
                    'success': True,
                    'translations': [{'key': k,
                                      'value': v}
                                     for k, v in translations.items()]
                })
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)})

        return JsonResponse({'success': False, 'error': 'Key or value is missing.'})

    # If form submission is a GET request, just show the initial form with translations
    context = {
        'filename': filename,
        'translations': translations,
        'filtered_translations': filtered_translations
    }

    return render(request, 'translations/edit_file.html', context)


def delete_translation(request, filename, key):
    file_path = os.path.join(TRANSLATIONS_DIR, filename)

    try:
        # Open the translation file and load the JSON data
        with open(file_path, 'r', encoding='utf-8') as file:
            translations = json.load(file)

        # Remove the key-value pair
        if key in translations:
            del translations[key]

            # Save the updated data back to the file
            with open(file_path, 'w', encoding='utf-8') as file:
                json.dump(translations, file, ensure_ascii=False, indent=4)

            # Provide a success message
            return HttpResponse("Translation deleted successfully")

        else:
            # Handle case where key does not exist
            return HttpResponse("Translation key not found.", status=404)

    except FileNotFoundError:
        # Handle case where the file does not exist
        return HttpResponse(f"File '{filename}' not found.", status=404)
