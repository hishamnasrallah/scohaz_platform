from collections import defaultdict

from django.db.models import Prefetch

from dynamicflow.apis.serializers import FieldWithIntegrationsSerializer
from dynamicflow.models import Page, Category, Field, Condition


class DynamicFlowHelper:
    def __init__(self, query=None):
        """
        Accepts:
        - None → means get all services
        - a single service code (int/str)
        - a list of service codes
        - a dict: {"service__in": [...], "user": ...}
        """
        self.query = {
            "service__in": [],
            "user": None,
        }

        if query is None:
            # If nothing is passed, fetch all services
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
        """
        Helper to return all service codes.
        Assumes Service model uses 'code' as the unique identifier.
        """
        from lookup.models import Lookup  # or from your actual service model
        return list(Lookup.objects.filter(parent_lookup__name="Service").values_list('code', flat=True))

    def get_flow(self):
        """
        Returns flow structure:
        - Original flat format if one service is passed
        - Grouped per service if many or all services are passed
        """
        if not self.query["service__in"]:
            return self.error_handling()
    
        pages = self.get_pages()
        categories = self.get_categories(pages)
        fields = self.get_fields(categories)

        service_count = len(self.query["service__in"])

        if service_count == 1:
            # Original flat format
            return {
                "service_flow": [self.format_page(page, fields) for page in pages]
            }

        # Grouped format
        service_flows = defaultdict(list)
        for page in pages:
            if hasattr(page, 'service') and hasattr(page.service, 'code'):
                service_code = page.service.code
                service_flows[service_code].append(page)

        response = []
        for service_code, service_pages in service_flows.items():
            formatted_pages = [self.format_page(p, fields) for p in service_pages]
            response.append({
                "service_code": service_code,
                "pages": formatted_pages
            })

        return {"service_flow": response}

    def get_pages(self):
        return Page.objects.filter(
            service__code__in=self.query["service__in"],
            active_ind=True
        ).select_related("service").only(
            "id", "name", "sequence_number", 'is_review_page', "applicant_type", "description", "service__code"
        ).prefetch_related(
            Prefetch('category_set', queryset=Category.objects.filter(active_ind=True))
        )


    def get_categories(self, pages):
        return Category.objects.filter(
            page__in=pages,
            active_ind=True
        ).prefetch_related('field_set')

    def get_fields(self, categories):
        return Field.objects.filter(
            _category__in=categories,
            active_ind=True
        ).select_related('_field_type')

    def format_response(self, pages, categories, fields):
        return {"service_flow": [self.format_page(page, fields) for page in pages]}

    def format_field_data(self, field, format_sub_fields=None, get_visibility_conditions=None):
        if not format_sub_fields:
            format_sub_fields = lambda x: []
        if not get_visibility_conditions:
            get_visibility_conditions = lambda x: []

        field_type = field._field_type.name.lower() if field._field_type else None
        field_data = {
            "name": field._field_name,
            "field_id": field.id,
            "display_name": field._field_display_name,
            "display_name_ara": field._field_display_name_ara,
            "field_type": field_type,
            "mandatory": field._mandatory,
            "sequence": field._sequence,
            "lookup": field._lookup.id if field._lookup else None,
            "allowed_lookups": [
                {"name": l.name, "id": l.id, "code": l.code, "icon": l.icon}
                for l in field.allowed_lookups.all()
            ],
            "sub_fields": format_sub_fields(field),
            "is_hidden": field._is_hidden,
            "is_disabled": field._is_disabled,
            "visibility_conditions": get_visibility_conditions(field),

            "integrations": self.get_field_integrations(field)
        }

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

        if field_type == "json":
            field_data.update({
                "max_length": field._max_length,
                "min_length": field._min_length,
            })

        if field_type in {"date", "datetime"}:
            field_data.update({
                "date_greater_than": field._date_greater_than,
                "date_less_than": field._date_less_than,
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

        return field_data

    def format_category(self, category, fields):
        category_fields = [
            self.format_field_data(f, self.format_sub_fields, self.get_visibility_conditions)
            for f in fields if category in f._category.all()
        ]
        return {
            "id": category.id,
            "name": category.name,
            "name_ara": category.name_ara,
            "repeatable": category.is_repeatable,
            "fields": category_fields,
        }

    def format_page(self, page, fields):
        return {
            "sequence_number": page.sequence_number.code if page.sequence_number else None,
            "name": page.name,
            "name_ara": page.name_ara,
            "applicant_type": page.applicant_type.id,
            # "service": page.service.id,
            "description": page.description,
            "description_ara": page.description_ara,
            "is_review_page": page.is_review_page,
            "is_hidden_page": not page.active_ind,
            "page_id": page.id,
            "categories": [self.format_category(c, fields) for c in page.category_set.all()],
        }

    def format_sub_fields(self, parent_field):
        sub_fields_data = []
        sub_fields = Field.objects.filter(_parent_field=parent_field)
        for sub_field in sub_fields:
            sub_fields_data.append(self.format_field_data(sub_field, self.format_sub_fields, self.get_visibility_conditions))
        return sub_fields_data

    def get_visibility_conditions(self, field):
        conditions = Condition.objects.filter(target_field=field, active_ind=True)
        return [{"condition_logic": c.condition_logic} for c in conditions]

    def error_handling(self):
        return {"error": "Select at least one service before continuing."}


    # def serialize_fields(self, fields):
    #     """Serialize fields with integration information"""
    #     serialized_fields = []
    #
    #     for field in fields:
    #         # Use the new serializer that includes integrations
    #         field_data = FieldWithIntegrationsSerializer(field).data
    #
    #         # Add any additional field processing here
    #         serialized_fields.append(field_data)
    #
    #     return serialized_fields

    def get_field_integrations(self, field):
        """
        Get all active integrations for a field
        """
        integrations = []

        # Get all active field integrations
        field_integrations = field.field_integrations.filter(
            active=True,
            integration__active_ind=True
        ).select_related('integration').order_by('order')

        for fi in field_integrations:
            integration_data = {
                "id": fi.id,
                "integration_id": fi.integration.id,
                "integration_name": fi.integration.name,
                "trigger_event": fi.trigger_event,
                "is_async": fi.is_async,

                # Include condition so frontend knows when to trigger
                "has_condition": bool(fi.condition_expression),

                # Tell frontend if this integration updates fields
                "updates_fields": fi.update_field_on_response,

                # Include which fields will be updated (for UI hints)
                "target_fields": list(fi.response_field_mapping.keys()) if fi.response_field_mapping else [],

                # For frontend to show loading states
                "order": fi.order
            }

            # For on_change integrations, include more details
            if fi.trigger_event == 'on_change':
                integration_data.update({
                    # Frontend needs to know if it should wait for response
                    "wait_for_response": not fi.is_async and fi.update_field_on_response,

                    # If there's a simple length condition, frontend can pre-validate
                    "min_length_trigger": self.extract_min_length_from_condition(fi.condition_expression)
                })

            integrations.append(integration_data)

        return integrations

    def extract_min_length_from_condition(self, condition):
        """
        Extract minimum length from condition for frontend optimization
        """
        if not condition:
            return None

        # Simple pattern matching for common length conditions
        import re

        # Match patterns like "len(field_value) >= 3" or "len(str(field_value)) == 10"
        patterns = [
            r'len\s*\(\s*(?:str\s*\(\s*)?field_value\s*(?:\)\s*)?\)\s*>=\s*(\d+)',
            r'len\s*\(\s*(?:str\s*\(\s*)?field_value\s*(?:\)\s*)?\)\s*==\s*(\d+)',
            r'len\s*\(\s*(?:str\s*\(\s*)?field_value\s*(?:\)\s*)?\)\s*>\s*(\d+)'
        ]

        for pattern in patterns:
            match = re.search(pattern, condition)
            if match:
                length = int(match.group(1))
                # For > operator, add 1
                if '>' in pattern and '>=' not in pattern:
                    length += 1
                return length

        return None


# Example of what the service flow API should return:

"""
{
  "pages": [
    {
      "sequence_number": "1",
      "name": "Personal Information",
      "categories": [
        {
          "name": "Basic Info",
          "fields": [
            {
              "_field_name": "national_id",
              "_field_display_name": "National ID",
              "_field_type": "text",
              "_mandatory": true,
              "_max_length": 10,
              "_min_length": 10,
              "integrations": [
                {
                  "id": 1,
                  "integration_id": 5,
                  "integration_name": "National ID Lookup",
                  "trigger_event": "on_change",
                  "is_async": false,
                  "has_condition": true,
                  "updates_fields": true,
                  "target_fields": ["first_name", "last_name", "date_of_birth"],
                  "wait_for_response": true,
                  "min_length_trigger": 10,
                  "order": 0
                }
              ]
            },
            {
              "_field_name": "first_name",
              "_field_display_name": "First Name",
              "_field_type": "text",
              "_mandatory": true,
              "integrations": []  // No integrations for this field
            }
          ]
        }
      ]
    }
  ]
}
"""
