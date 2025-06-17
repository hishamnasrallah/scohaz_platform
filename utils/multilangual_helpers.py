# utils.py
import os
import json
from django.conf import settings
from django.utils.timezone import now

from version.models import LocalVersion


def get_translation_file_path(lang_code):
    return os.path.join(settings.TRANSLATION_DIR, f"{lang_code}.json")

def get_backup_file_path(lang_code, version_number):
    return os.path.join(settings.TRANSLATION_DIR, f"{lang_code}_{version_number}.json")

def list_languages():
    files = os.listdir(settings.TRANSLATION_DIR)
    return [f.split(".")[0] for f in files if f.endswith(".json") and "_" not in f]

def read_translation(lang_code):
    path = get_translation_file_path(lang_code)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def write_translation_with_versioning(lang_code, updated_data):
    current_file_path = get_translation_file_path(lang_code)

    try:
        current_version = LocalVersion.objects.get(lang=lang_code, active_ind=True)
        version_number = current_version.version_number or now().strftime('%Y%m%d%H%M%S')
        current_version.active_ind = False
        current_version.save()
    except LocalVersion.DoesNotExist:
        version_number = now().strftime('%Y%m%d%H%M%S')

    if os.path.exists(current_file_path):
        backup_path = get_backup_file_path(lang_code, version_number)
        os.rename(current_file_path, backup_path)

    with open(current_file_path, 'w', encoding='utf-8') as f:
        json.dump(updated_data, f, ensure_ascii=False, indent=4)

    new_version = now().strftime('%Y%m%d%H%M%S')
    LocalVersion.objects.create(
        lang=lang_code,
        version_number=new_version,
        active_ind=True
    )
    return new_version
