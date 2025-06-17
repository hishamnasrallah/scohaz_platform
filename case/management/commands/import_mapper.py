import json
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from case.models import CaseMapper, MapperTarget, MapperFieldRule


class Command(BaseCommand):
    help = 'Import a CaseMapper from JSON file'

    def add_arguments(self, parser):
        parser.add_argument('--input', type=str, required=True, help='Path to JSON file')

    def handle(self, *args, **options):
        input_path = options['input']

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.stderr.write(f"[ERROR] Failed to load file: {e}")
            return

        mapper = CaseMapper.objects.create(
            name=data["name"] + " (imported)",
            case_type=data["case_type"],
            active_ind=data.get("active_ind", True)
        )

        for target_data in data.get("targets", []):
            app_label, model = target_data["content_type"]
            content_type = ContentType.objects.get(app_label=app_label, model=model)

            target = MapperTarget.objects.create(
                case_mapper=mapper,
                content_type=content_type,
                finder_function_path=target_data.get("finder_function_path"),
                processor_function_path=target_data.get("processor_function_path"),
                post_processor_path=target_data.get("post_processor_path"),
                root_path=target_data.get("root_path"),
                filter_function_path=target_data.get("filter_function_path"),
                active_ind=target_data.get("active_ind", True)
            )

            for rule_data in target_data.get("field_rules", []):
                MapperFieldRule.objects.create(
                    mapper_target=target,
                    target_field=rule_data["target_field"],
                    json_path=rule_data["json_path"],
                    default_value=rule_data.get("default_value"),
                    transform_function_path=rule_data.get("transform_function_path"),
                    condition_path=rule_data.get("condition_path"),
                    condition_operator=rule_data.get("condition_operator"),
                    condition_value=rule_data.get("condition_value"),
                )

        self.stdout.write(f"✅ CaseMapper imported: {mapper.name} (ID={mapper.id})")
