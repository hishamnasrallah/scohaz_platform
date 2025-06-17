from collections import defaultdict

from django.db.models import Prefetch
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
            "id", "name", "sequence_number", "description", "service__code"
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
            "lookup": field._lookup.id if field._lookup else None,
            "allowed_lookups": [
                {"name": l.name, "id": l.id, "code": l.code, "icon": l.icon}
                for l in field.allowed_lookups.all()
            ],
            "sub_fields": format_sub_fields(field),
            "is_hidden": field._is_hidden,
            "is_disabled": field._is_disabled,
            "visibility_conditions": get_visibility_conditions(field),
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
            "description": page.description,
            "description_ara": page.description_ara,
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



# from django.db.models import Prefetch
# from dynamicflow.models import Page, Category, Field, Condition
#
#
# class DynamicFlowHelper:
#     def __init__(self, query):
#         try:
#             self.query = {
#                 "service__in": query.get("service__in", []),
#                 "user": query.get("user"),
#             }
#         except AttributeError:
#             self.query = {
#                 "service__in": query
#             }
#
#     def get_flow(self):
#         """
#         Entry point to retrieve the full service flow structure.
#         """
#         if not self.query["service__in"]:
#             return self.error_handling()
#
#         pages = self.get_pages()
#         categories = self.get_categories(pages)
#         fields = self.get_fields(categories)
#
#         return self.format_response(pages, categories, fields)
#
#     def get_pages(self):
#         return Page.objects.filter(
#             service__code__in=self.query["service__in"],
#             active_ind=True
#         ).only("id", "name", "sequence_number", "description").prefetch_related(
#             Prefetch('category_set', queryset=Category.objects.filter(active_ind=True))
#         )
#
#     def get_categories(self, pages):
#         return Category.objects.filter(
#             page__in=pages,
#             active_ind=True
#         ).prefetch_related('field_set')
#
#     def get_fields(self, categories):
#         """
#         Retrieve fields linked to the provided categories.
#         """
#         return Field.objects.filter(
#             _category__in=categories,
#             active_ind=True
#         ).select_related('_field_type')
#
#     def format_response(self, pages, categories, fields):
#         """
#         Format the response into a JSON-compatible structure.
#         """
#
#         def format_field(field):
#             # Function to format sub-fields recursively
#             def format_sub_fields(parent_field):
#                 sub_fields_data = []
#                 sub_fields = Field.objects.filter(_parent_field=parent_field)
#                 for sub_field in sub_fields:
#                     sub_fields_data.append({
#                         "name": sub_field._field_name,
#                         "field_id": sub_field.id,
#                         "display_name": sub_field._field_display_name,
#                         "display_name_ara": sub_field._field_display_name_ara,
#                         "field_type": sub_field._field_type.name if sub_field._field_type else None,
#                         "mandatory": sub_field._mandatory,
#                         "lookup": sub_field._lookup.name if sub_field._lookup else None,
#                         "max_length": sub_field._max_length,
#                         "min_length": sub_field._min_length,
#                         "value_greater_than": sub_field._value_greater_than,
#                         "value_less_than": sub_field._value_less_than,
#                         "date_greater_than": sub_field._date_greater_than,
#                         "size_greater_than": sub_field._size_greater_than,
#                         "size_less_than": sub_field._size_less_than,
#                         "only_positive": sub_field._only_positive,
#                         "is_hidden": sub_field._is_hidden,
#                         "is_disabled": sub_field._is_disabled,
#                         "visibility_conditions": get_visibility_conditions(sub_field),
#                         "sub_fields": format_sub_fields(sub_field),
#                     })
#                 return sub_fields_data
#
#             def get_visibility_conditions(field):
#                 conditions = Condition.objects.filter(target_field=field, active_ind=True)
#                 return [
#                     {
#                         "condition_logic": condition.condition_logic
#                     }
#                     for condition in conditions
#                 ]
#
#             # Call the recursive sub-field formatting
#             sub_fields_data = format_sub_fields(field)
#
#             # Format allowed lookups based on parent lookup
#             allowed_lookups_data = [
#                 {
#                     "name": lookup.name,
#                     "id": lookup.id,
#                     "code": lookup.code,
#                     "icon": lookup.icon
#                 }
#                 for lookup in field.allowed_lookups.all()
#             ]
#
#             return {
#                 "name": field._field_name,
#                 "field_id": field.id,
#                 "display_name": field._field_display_name,
#                 "display_name_ara": field._field_display_name_ara,
#                 "field_type": field._field_type.name if field._field_type else None,
#                 "mandatory": field._mandatory,
#                 "lookup": field._lookup.name if field._lookup else None,
#                 "allowed_lookups": allowed_lookups_data,
#                 "sub_fields": sub_fields_data,
#                 "max_length": field._max_length,
#                 "min_length": field._min_length,
#                 "value_greater_than": field._value_greater_than,
#                 "value_less_than": field._value_less_than,
#                 "date_greater_than": field._date_greater_than,
#                 "size_greater_than": field._size_greater_than,
#                 "size_less_than": field._size_less_than,
#                 "only_positive": field._only_positive,
#                 "is_hidden": field._is_hidden,
#                 "is_disabled": field._is_disabled,
#                 "visibility_conditions": get_visibility_conditions(field),
#             }
#
#         def format_category(category):
#             category_fields = [
#                 format_field(field)
#                 for field in fields if category in field._category.all()
#             ]
#             return {
#                 "id": category.id,
#                 "name": category.name,
#                 "name_ara": category.name_ara,
#                 "repeatable": category.is_repeatable,
#                 "fields": category_fields,
#             }
#
#         def format_page(page):
#             page_categories = page.category_set.all()
#             return {
#                 "sequence_number": page.sequence_number.code if page.sequence_number else None,
#                 "name": page.name,
#                 "name_ara": page.name_ara,
#                 "description": page.description,
#                 "description_ara": page.description_ara,
#                 "is_hidden_page": not page.active_ind,
#                 "page_id": page.id,
#                 "categories": [format_category(category) for category in page_categories],
#             }
#
#         return {"service_flow": [format_page(page) for page in pages]}
#
#     def error_handling(self):
#         """
#         Return an error response if no service is provided.
#         """
#         return {"error": "Select at least one service before continuing."}


# class DynamicFlowHelper:
#     def __init__(self, query):
#         try:
#             self.query = {
#                 "service__in": query.get("service__in", []),
#                 "user": query.get("user"),
#             }
#         except AttributeError:
#             self.query = {
#                 "service__in": query
#             }
#
#     def get_flow(self):
#         """
#         Entry point to retrieve the full service flow structure.
#         """
#         if not self.query["service__in"]:
#             return self.error_handling()
#
#         pages = self.get_pages()
#         categories = self.get_categories(pages)
#         fields = self.get_fields(categories)
#
#         return self.format_response(pages, categories, fields)
#
#     def get_pages(self):
#         return Page.objects.filter(
#             service__code__in=self.query["service__in"],
#             active_ind=True
#         ).only("id", "name", "sequence_number", "description").prefetch_related(
#             Prefetch('category_set', queryset=Category.objects.filter(active_ind=True))
#         )
#
#     def get_categories(self, pages):
#         return Category.objects.filter(
#             page__in=pages,
#             active_ind=True
#         ).prefetch_related('field_set')
#
#     def get_fields(self, categories):
#         """
#         Retrieve fields linked to the provided categories.
#         """
#         return Field.objects.filter(
#             _category__in=categories,
#             active_ind=True
#         ).select_related('_field_type')
#
#     def format_response(self, pages, categories, fields):
#         """
#         Format the response into a JSON-compatible structure.
#         """
#
#         def format_field(field):
#             # Function to format sub-fields recursively
#             def format_sub_fields(parent_field):
#                 sub_fields_data = []
#                 # Retrieve sub-fields by filtering on the parent field (ForeignKey)
#                 sub_fields = Field.objects.filter(_parent_field=parent_field)
#                 for sub_field in sub_fields:
#                     sub_fields_data.append({
#                         "name": sub_field._field_name,
#                         "field_id": sub_field.id,
#                         "display_name": sub_field._field_display_name,
#                         "display_name_ara": sub_field._field_display_name_ara,
#                         "field_type": sub_field._field_type.name
#                         if sub_field._field_type else None,
#                         "mandatory": sub_field._mandatory,
#                         "lookup": sub_field._lookup.name if sub_field._lookup else None,
#                         "max_length": sub_field._max_length,
#                         "min_length": sub_field._min_length,
#                         "value_greater_than": sub_field._value_greater_than,
#                         "value_less_than": sub_field._value_less_than,
#                         "date_greater_than": sub_field._date_greater_than,
#                         "size_greater_than": sub_field._size_greater_than,
#                         "size_less_than": sub_field._size_less_than,
#                         "only_positive": sub_field._only_positive,
#                         "is_hidden": sub_field._is_hidden,
#                         "is_disabled": sub_field._is_disabled,
#                         # Recursively fetch the sub-fields of the current sub-field
#                         "sub_fields": format_sub_fields(sub_field),
#                     })
#                 return sub_fields_data
#
#             # Call the recursive sub-field formatting
#             sub_fields_data = format_sub_fields(field)
#
#             # Format allowed lookups based on parent lookup
#             allowed_lookups_data = [
#                 {
#                     "name": lookup.name,
#                     "id": lookup.id,
#                     "code": lookup.code,
#                     "icon": lookup.icon
#                 }
#                 # Retrieve the allowed lookups for the field
#                 for lookup in field.allowed_lookups.all()
#             ]
#
#             return {
#                 "name": field._field_name,
#                 "field_id": field.id,
#                 "display_name": field._field_display_name,
#                 "display_name_ara": field._field_display_name_ara,
#                 "field_type": field._field_type.name if field._field_type else None,
#                 "mandatory": field._mandatory,
#                 "lookup": field._lookup.name if field._lookup else None,
#                 "allowed_lookups": allowed_lookups_data,
#                 # Include the recursively formatted sub-fields
#                 "sub_fields": sub_fields_data,
#                 "max_length": field._max_length,
#                 "min_length": field._min_length,
#                 "value_greater_than": field._value_greater_than,
#                 "value_less_than": field._value_less_than,
#                 "date_greater_than": field._date_greater_than,
#                 "size_greater_than": field._size_greater_than,
#                 "size_less_than": field._size_less_than,
#                 "only_positive": field._only_positive,
#                 "is_hidden": field._is_hidden,
#                 "is_disabled": field._is_disabled,
#             }
#
#         def format_category(category):
#             category_fields = [
#                 format_field(field)
#                 for field in fields if category in field._category.all()
#             ]
#             return {
#                 "id": category.id,
#                 "name": category.name,
#                 "name_ara": category.name_ara,
#                 "repeatable": category.is_repeatable,
#                 "fields": category_fields,
#             }
#
#         def format_page(page):
#             page_categories = page.category_set.all()
#             return {
#                 "sequence_number": page.sequence_number.code
#                 if page.sequence_number else None,
#                 "name": page.name,
#                 "name_ara": page.name_ara,
#                 "description": page.description,
#                 "description_ara": page.description_ara,
#                 "is_hidden_page": not page.active_ind,
#                 "page_id": page.id,
#                 "categories": [format_category(category)
#                                for category in page_categories],
#             }
#
#         return {"service_flow": [format_page(page) for page in pages]}
#
#     def error_handling(self):
#         """
#         Return an error response if no service is provided.
#         """
#         return {"error": "Select at least one service before continuing."}

# THIS THE LATEST ONE THAT WORKED
# class DynamicFlowHelper:
#     def __init__(self, query):
#         try:
#             self.query = {
#                 "service__in": query.get("service__in"),
#                 "user": query.get("user"),
#             }
#
#         except:
#             self.query = {
#                 "service__in": query
#             }
#
#     def get_flow(self):
#         """
#         Entry point to retrieve the full service flow structure.
#         """
#         if not self.query["service__in"]:
#             return self.error_handling()
#
#         pages = self.get_pages()
#         categories = self.get_categories(pages)
#         fields = self.get_fields(categories)
#
#         return self.format_response(pages, categories, fields)
#
#     def get_pages(self):
#         return Page.objects.filter(
#             service__code__in=self.query["service__in"],
#             active_ind=True
#         ).only("id", "name", "sequence_number",
#         "description").prefetch_related(
#             Prefetch('category_set',
#             queryset=Category.objects.filter(active_ind=True))
#         )
#
#     def get_categories(self, pages):
#         return Category.objects.filter(
#             page__in=pages,
#             active_ind=True
#         ).prefetch_related('field_set')
#
#     def get_fields(self, categories):
#         """
#         Retrieve fields linked to the provided categories.
#         """
#         return Field.objects.filter(
#             _category__in=categories,
#             active_ind=True
#         ).select_related('_field_type')
#
#     def format_response(self, pages, categories, fields):
#         """
#         Format the response into a JSON-compatible structure.
#         """
#
#         def format_field(field):
#             return {
#                 "name": field._field_name,
#                 "field_id": field.id,
#                 "display_name": field._field_display_name,
#                 "display_name_ara": field._field_display_name_ara,
#                 "field_type": field._field_type.name if field._field_type else None,
#                 "mandatory": field._mandatory,
#                 "max_length": field._max_length,
#                 "min_length": field._min_length,
#                 "value_greater_than": field._value_greater_than,
#                 "value_less_than": field._value_less_than,
#                 "date_greater_than": field._date_greater_than,
#                 "size_greater_than": field._size_greater_than,
#                 "size_less_than": field._size_less_than,
#                 "only_positive": field._only_positive,
#                 "is_hidden": field._is_hidden,
#                 "is_disabled": field._is_disabled,
#             }
#
#         def format_category(category):
#             category_fields = [
#                 format_field(field)
#                 for field in fields if category in field._category.all()
#             ]
#             return {
#                 "id": category.id,
#                 "name": category.name,
#                 "name_ara": category.name_ara,
#                 "repeatable": category.is_repeatable,
#                 "fields": category_fields,
#             }
#
#         def format_page(page):
#             page_categories = page.category_set.all()
#             return {
#                 "sequence_number": page.sequence_number.code \
#                 if page.sequence_number else None,
#                 "name": page.name,
#                 "name_ara": page.name_ara,
#                 "description": page.description,
#                 "description_ara": page.description_ara,
#                 "is_hidden_page": not page.active_ind,
#                 "page_id": page.id,
#                 "categories": [format_category(category) \
#                 for category in page_categories],
#             }
#
#         return {"service_flow": [format_page(page) for page in pages]}

    # def format_response(self, pages, categories, fields):
    #     """
    #     Format the response as a JSON-compatible structure.
    #     """
    #     flow_details_list = []
    #
    #     for page in pages:
    #         page_categories = page.category_set.all()
    #         flow_details_list.append({
    #             "sequence_number": page.sequence_number.code \
#                       if page.sequence_number else None,
    #             "name": page.name,
    #             "name_ara": page.name_ara,
    #             "description": page.description,
    #             "description_ara": page.description_ara,
    #             "is_hidden_page": not page.active_ind,
    #             "page_id": page.id,
    #             "categories": [
    #                 {
    #                     "id": category.id,
    #                     "name": category.name,
    #                     "name_ara": category.name_ara,
    #                     "repeatable": category.is_repeatable,
    #                     "fields": [
    #                         {
    #                             "name": field._field_name,
    #                             "field_id": field.id,
    #                             "display_name": field._field_display_name,
    #                             "display_name_ara": field._field_display_name_ara,
    #                             "field_type": field._field_type.name \
#                                           if field._field_type else None,
    #                             "mandatory": field._mandatory,
    #                             "max_length": field._max_length,
    #                             "min_length": field._min_length,
    #                             "value_greater_than": field._value_greater_than,
    #                             "value_less_than": field._value_less_than,
    #                             "date_greater_than": field._date_greater_than,
    #                             "size_greater_than": field._size_greater_than,
    #                             "size_less_than": field._size_less_than,
    #                             "only_positive": field._only_positive,
    #                             "is_hidden": field._is_hidden,
    #                             "is_disabled": field._is_disabled,
    #                         }
    #                         for field in fields if category in field._category.all()
    #                     ]
    #                 }
    #                 for category in page_categories
    #             ]
    #         })
    #
    #     return {"service_flow": flow_details_list}
