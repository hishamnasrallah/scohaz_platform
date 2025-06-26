from collections import defaultdict
from django.db.models import Prefetch
from dynamicflow.models import Page, Category, Field, Condition


class WorkflowServiceFlowHelper:
    """
    Dedicated helper for workflow builder service flow API
    Provides consistent data structure with explicit foreign key fields
    """

    def __init__(self, query=None):
        self.query = {
            "service__in": [],
            "user": None,
        }

        if query is None:
            self.query["service__in"] = self._get_all_service_codes()
        elif isinstance(query, dict):
            service_ids = query.get("service__in")
            if service_ids is None:
                self.query["service__in"] = self._get_all_service_codes()
            elif isinstance(service_ids, list):
                self.query["service__in"] = service_ids
            else:
                self.query["service__in"] = [service_ids]
            self.query["user"] = query.get("user")
        elif isinstance(query, (int, str)):
            self.query["service__in"] = [query]
        elif isinstance(query, list):
            self.query["service__in"] = query

    def _get_all_service_codes(self):
        from lookup.models import Lookup
        return list(Lookup.objects.filter(
            parent_lookup__name="Service"
        ).values_list('code', flat=True))

    def get_flow(self):
        if not self.query["service__in"]:
            return {"error": "Select at least one service before continuing."}

        pages = self._get_pages()
        categories = self._get_categories(pages)
        fields = self._get_fields(categories)

        service_count = len(self.query["service__in"])

        if service_count == 1:
            return {
                "service_flow": [self._format_page(page, fields) for page in pages]
            }

        # Grouped format for multiple services
        service_flows = defaultdict(list)
        for page in pages:
            if hasattr(page, 'service') and hasattr(page.service, 'code'):
                service_code = page.service.code
                service_flows[service_code].append(page)

        response = []
        for service_code, service_pages in service_flows.items():
            formatted_pages = [self._format_page(p, fields) for p in service_pages]
            response.append({
                "service_code": service_code,
                "pages": formatted_pages
            })

        return {"service_flow": response}

    def _get_pages(self):
        return Page.objects.filter(
            service__code__in=self.query["service__in"],
            active_ind=True
        ).select_related(
            "service",
            "sequence_number",
            "applicant_type"
        ).prefetch_related(
            Prefetch('category_set', queryset=Category.objects.filter(active_ind=True))
        )

    def _get_categories(self, pages):
        return Category.objects.filter(
            page__in=pages,
            active_ind=True
        ).prefetch_related('field_set')

    def _get_fields(self, categories):
        return Field.objects.filter(
            _category__in=categories,
            active_ind=True
        ).select_related(
            '_field_type', '_lookup', '_parent_field'
        ).prefetch_related('allowed_lookups')

    def _format_page(self, page, fields):
        """Format page with consistent foreign key structure"""
        return {
            # Keep original fields for backward compatibility
            "sequence_number": page.sequence_number.code if page.sequence_number else None,
            "name": page.name,
            "name_ara": page.name_ara,
            "description": page.description,
            "description_ara": page.description_ara,
            "is_hidden_page": not page.active_ind,
            "page_id": page.id,

            # Add explicit foreign key fields for workflow builder
            "sequence_number_id": page.sequence_number.id if page.sequence_number else None,
            "sequence_number_code": page.sequence_number.code if page.sequence_number else None,
            "sequence_number_name": page.sequence_number.name if page.sequence_number else None,

            "service_id": page.service.id if page.service else None,
            "service_code": page.service.code if page.service else None,
            "service_name": page.service.name if page.service else None,

            "applicant_type_id": page.applicant_type.id if page.applicant_type else None,
            "applicant_type_code": page.applicant_type.code if page.applicant_type else None,
            "applicant_type_name": page.applicant_type.name if page.applicant_type else None,

            "categories": [self._format_category(c, fields) for c in page.category_set.all()],
        }

    def _format_category(self, category, fields):
        category_fields = [
            self._format_field(f)
            for f in fields if category in f._category.all()
        ]
        return {
            "id": category.id,
            "name": category.name,
            "name_ara": category.name_ara,
            "repeatable": category.is_repeatable,
            "fields": category_fields,
        }

    def _format_field(self, field):
        """Format field with consistent foreign key structure"""
        field_type = field._field_type.name.lower() if field._field_type else None

        field_data = {
            # Keep original fields for backward compatibility
            "name": field._field_name,
            "field_id": field.id,
            "display_name": field._field_display_name,
            "display_name_ara": field._field_display_name_ara,
            "field_type": field_type,
            "mandatory": field._mandatory,
            "lookup": field._lookup.id if field._lookup else None,
            "is_hidden": field._is_hidden,
            "is_disabled": field._is_disabled,
            "sequence": field._sequence,

            # Add explicit foreign key fields for workflow builder
            "field_type_id": field._field_type.id if field._field_type else None,
            "field_type_name": field._field_type.name if field._field_type else None,
            "field_type_code": field._field_type.code if field._field_type else None,

            "lookup_id": field._lookup.id if field._lookup else None,
            "lookup_name": field._lookup.name if field._lookup else None,
            "lookup_code": field._lookup.code if field._lookup else None,

            "allowed_lookups": [
                {"name": l.name, "id": l.id, "code": l.code, "icon": l.icon}
                for l in field.allowed_lookups.all()
            ],
            "sub_fields": self._format_sub_fields(field),
            "visibility_conditions": self._get_visibility_conditions(field),
        }

        # Add field-type specific validations
        self._add_field_validations(field_data, field, field_type)

        return field_data

    def _format_sub_fields(self, parent_field):
        sub_fields_data = []
        sub_fields = Field.objects.filter(
            _parent_field=parent_field,
            active_ind=True
        ).select_related('_field_type', '_lookup')

        for sub_field in sub_fields:
            sub_fields_data.append(self._format_field(sub_field))
        return sub_fields_data

    def _get_visibility_conditions(self, field):
        conditions = Condition.objects.filter(target_field=field, active_ind=True)
        return [{
            "id": c.id,
            "condition_logic": c.condition_logic,
            "target_field_id": c.target_field.id,
            "target_field_name": c.target_field._field_name
        } for c in conditions]

    def _add_field_validations(self, field_data, field, field_type):
        """Add field type specific validation properties"""
        if field_type in {"text", "textarea", "rich_text", "password", "slug", "email", "url", "phone_number"}:
            field_data.update({
                "max_length": field._max_length,
                "min_length": field._min_length,
                "regex_pattern": field._regex_pattern,
                "allowed_characters": field._allowed_characters,
                "forbidden_words": field._forbidden_words,
            })

        if field_type in {"number", "decimal", "currency", "percentage", "rating"}:
            field_data.update({
                "value_greater_than": field._value_greater_than,
                "value_less_than": field._value_less_than,
                "integer_only": field._integer_only,
                "positive_only": field._positive_only,
                "precision": field._precision,
            })

        if field_type in {"date", "datetime"}:
            field_data.update({
                "date_greater_than": str(field._date_greater_than) if field._date_greater_than else None,
                "date_less_than": str(field._date_less_than) if field._date_less_than else None,
                "future_only": field._future_only,
                "past_only": field._past_only,
            })

        if field_type == "boolean":
            field_data["default_boolean"] = field._default_boolean

        if field_type in {"file", "image"}:
            field_data.update({
                "file_types": field._file_types,
                "max_file_size": field._max_file_size,
                "image_max_width": field._image_max_width,
                "image_max_height": field._image_max_height,
            })

        if field_type in {"choice", "multi_choice"}:
            field_data.update({
                "max_selections": field._max_selections,
                "min_selections": field._min_selections,
            })

        if field_type == "coordinates":
            field_data["coordinates_format"] = field._coordinates_format

        if field_type == "uuid":
            field_data["uuid_format"] = field._uuid_format