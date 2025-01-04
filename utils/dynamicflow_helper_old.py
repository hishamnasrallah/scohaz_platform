from django.db.models import Prefetch
from dynamicflow.models import Page, Category, Field
# from lookup.models import Lookup


class DynamicFlowHelper:
    def __init__(self, query):
        try:
            self.query = {
                "service__in": query.get("service__in"),
                "user": query.get("user"),
            }

        except:
            self.query = {
                "service__in": query
            }

    def get_flow(self):
        """
        Entry point to retrieve the full service flow structure.
        """
        if not self.query["service__in"]:
            return self.error_handling()

        pages = self.get_pages()
        categories = self.get_categories(pages)
        fields = self.get_fields(categories)

        return self.format_response(pages, categories, fields)

    def get_pages(self):
        """
        Retrieve all pages for the provided services.
        """
        return Page.objects.filter(
            service__code__in=self.query["service__in"],
            active_ind=True
        ).prefetch_related(
            Prefetch('category_set', queryset=Category.objects.filter(active_ind=True))
        )

    def get_categories(self, pages):
        """
        Retrieve categories linked to the provided pages.
        """
        return Category.objects.filter(
            page__in=pages,
            active_ind=True
        ).prefetch_related(
            Prefetch('field_set', queryset=Field.objects.filter(active_ind=True))
        )

    def get_fields(self, categories):
        """
        Retrieve fields linked to the provided categories.
        """
        return Field.objects.filter(
            _category__in=categories,
            active_ind=True
        ).select_related('_field_type')

    def format_response(self, pages, categories, fields):
        """
        Format the response as a JSON-compatible structure.
        """
        flow_details_list = []

        for page in pages:
            page_categories = page.category_set.all()
            flow_details_list.append({
                "sequence_number": page.sequence_number.code if page.sequence_number else None,
                "name": page.name,
                "name_ara": page.name_ara,
                "description": page.description,
                "description_ara": page.description_ara,
                "is_hidden_page": not page.active_ind,
                "page_id": page.id,
                "categories": [
                    {
                        "id": category.id,
                        "name": category.name,
                        "name_ara": category.name_ara,
                        "repeatable": category.is_repeatable,
                        "fields": [
                            {
                                "name": field._field_name,
                                "field_id": field.id,
                                "display_name": field._field_display_name,
                                "display_name_ara": field._field_display_name_ara,
                                "field_type": field._field_type.name if field._field_type else None,
                                "mandatory": field._mandatory,
                                "max_length": field._max_length,
                                "min_length": field._min_length,
                                "regex_pattern": field._regex_pattern,
                                "allowed_characters": field._allowed_characters,
                                "forbidden_words": field._forbidden_words,
                                "value_greater_than": field._value_greater_than,
                                "value_less_than": field._value_less_than,
                                "integer_only": field._integer_only,
                                "positive_only": field._positive_only,
                                "date_greater_than": field._date_greater_than,
                                "date_less_than": field._date_less_than,
                                "future_only": field._future_only,
                                "past_only": field._past_only,
                                "default_boolean": field._default_boolean,
                                "file_types": field._file_types,
                                "max_file_size": field._max_file_size,
                                "image_max_width": field._image_max_width,
                                "image_max_height": field._image_max_height,
                                "allowed_lookups": [
                                    lookup.name for lookup in field.allowed_lookups.all()
                                ],
                                "max_selections": field._max_selections,
                                "min_selections": field._min_selections,
                                "precision": field._precision,
                                "unique": field._unique,
                                "default_value": field._default_value,
                                "coordinates_format": field._coordinates_format,
                                "uuid_format": field._uuid_format,
                                "is_hidden": field._is_hidden,
                                "is_disabled": field._is_disabled,
                                "active": field.active_ind
                            }
                            for field in fields if category in field._category.all()
                        ]
                    }
                    for category in page_categories
                ]
            })

        return {"service_flow": flow_details_list}


    def error_handling(self):
        """
        Return an error response if no service is provided.
        """
        return {"error": "Select at least one service before continuing."}
