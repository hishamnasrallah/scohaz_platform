import json
from django.core.management.base import BaseCommand
from case.models import CaseMapper


class Command(BaseCommand):
    help = 'Export a CaseMapper and its targets + rules to a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('mapper_id', type=int, help='CaseMapper ID to export')
        parser.add_argument('--output', type=str, default='mapper_export.json', help='Output JSON file path')

    def handle(self, *args, **options):
        mapper_id = options['mapper_id']
        output_path = options['output']

        try:
            mapper = CaseMapper.objects.get(id=mapper_id)
        except CaseMapper.DoesNotExist:
            self.stderr.write(f"[ERROR] No CaseMapper found with ID={mapper_id}")
            return

        # Serialize mapper
        data = {
            "name": mapper.name,
            "case_type": mapper.case_type,
            "active_ind": mapper.active_ind,
            "targets": []
        }

        for target in mapper.targets.all():
            target_data = {
                "content_type": target.content_type.natural_key(),  # ('app_label', 'model')
                "finder_function_path": target.finder_function_path,
                "processor_function_path": target.processor_function_path,
                "post_processor_path": target.post_processor_path,
                "root_path": target.root_path,
                "filter_function_path": target.filter_function_path,
                "active_ind": target.active_ind,
                "field_rules": []
            }

            for rule in target.field_rules.all():
                rule_data = {
                    "target_field": rule.target_field,
                    "json_path": rule.json_path,
                    "default_value": rule.default_value,
                    "transform_function_path": rule.transform_function_path,
                    "condition_path": rule.condition_path,
                    "condition_operator": rule.condition_operator,
                    "condition_value": rule.condition_value
                }
                target_data["field_rules"].append(rule_data)

            data["targets"].append(target_data)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        self.stdout.write(f"✅ CaseMapper exported to: {output_path}")
