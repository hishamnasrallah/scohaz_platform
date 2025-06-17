import json
from django.core.serializers.json import DjangoJSONEncoder
import uuid
from case.models import CaseMapper, MapperTarget, MapperFieldRule

def export_mapper(case_type):
    try:
        mapper = CaseMapper.objects.get(case_type=case_type)
    except CaseMapper.DoesNotExist:
        return {"error": "Mapper not found."}

    data = {
        "case_mapper": {
            "name": mapper.name,
            "case_type": mapper.case_type,
            "active_ind": mapper.active_ind,
        },
        "targets": []
    }

    for target in mapper.targets.all():
        t = {
            "content_type_id": target.content_type_id,
            "finder_function_path": target.finder_function_path,
            "processor_function_path": target.processor_function_path,
            "post_processor_path": target.post_processor_path,
            "active_ind": target.active_ind,
            "field_rules": []
        }

        for rule in target.field_rules.all():
            t["field_rules"].append({
                "target_field": rule.target_field,
                "json_path": rule.json_path,
                "transform_function_path": rule.transform_function_path,
                "condition_path": rule.condition_path,
                "condition_operator": rule.condition_operator,
                "condition_value": rule.condition_value,
                "default_value": rule.default_value,
            })

        data["targets"].append(t)

    return json.dumps(data, indent=2, cls=DjangoJSONEncoder)


def import_mapper(data_json):
    data = json.loads(data_json)
    from django.contrib.contenttypes.models import ContentType

    # Create CaseMapper
    mapper = CaseMapper.objects.create(
        name=data["case_mapper"]["name"],
        case_type=data["case_mapper"]["case_type"],
        active_ind=data["case_mapper"].get("active_ind", True)
    )

    for target_data in data["targets"]:
        target = MapperTarget.objects.create(
            id=uuid.uuid4(),
            case_mapper=mapper,
            content_type_id=target_data["content_type_id"],
            finder_function_path=target_data.get("finder_function_path"),
            processor_function_path=target_data.get("processor_function_path"),
            post_processor_path=target_data.get("post_processor_path"),
            active_ind=target_data.get("active_ind", True),
        )

        for rule_data in target_data.get("field_rules", []):
            MapperFieldRule.objects.create(
                mapper_target=target,
                target_field=rule_data["target_field"],
                json_path=rule_data["json_path"],
                transform_function_path=rule_data.get("transform_function_path"),
                condition_path=rule_data.get("condition_path"),
                condition_operator=rule_data.get("condition_operator"),
                condition_value=rule_data.get("condition_value"),
                default_value=rule_data.get("default_value"),
            )

    return {"success": True, "mapper_id": mapper.id}
