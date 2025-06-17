import json
from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from case.models import CaseMapper, MapperTarget, MapperFieldRule


class Command(BaseCommand):
    help = 'Create a new version of a CaseMapper with all nested targets and rules'

    def add_arguments(self, parser):
        parser.add_argument('mapper_id', type=int, help='CaseMapper ID to clone')

    def handle(self, *args, **options):
        original_id = options['mapper_id']
        try:
            original = CaseMapper.objects.get(id=original_id)
        except CaseMapper.DoesNotExist:
            self.stderr.write(f"[ERROR] Mapper {original_id} not found.")
            return

        new_version = (original.versions.aggregate(models.Max('version'))['version__max'] or original.version) + 1

        # ✅ Clone mapper
        cloned_mapper = CaseMapper.objects.create(
            name=f"{original.name} v{new_version}",
            case_type=original.case_type,
            version=new_version,
            parent=original,
            active_ind=False,  # New versions start inactive
        )

        # ✅ Clone targets and rules
        for target in original.targets.all():
            new_target = MapperTarget.objects.create(
                case_mapper=cloned_mapper,
                content_type=target.content_type,
                finder_function_path=target.finder_function_path,
                processor_function_path=target.processor_function_path,
                post_processor_path=target.post_processor_path,
                root_path=target.root_path,
                filter_function_path=target.filter_function_path,
                active_ind=target.active_ind,
            )

            for rule in target.field_rules.all():
                MapperFieldRule.objects.create(
                    mapper_target=new_target,
                    target_field=rule.target_field,
                    json_path=rule.json_path,
                    default_value=rule.default_value,
                    transform_function_path=rule.transform_function_path,
                    condition_path=rule.condition_path,
                    condition_operator=rule.condition_operator,
                    condition_value=rule.condition_value,
                )

        self.stdout.write(f"✅ New version created: {cloned_mapper.name} (ID={cloned_mapper.id})")
