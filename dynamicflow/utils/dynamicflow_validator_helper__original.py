from lookup.models import Lookup
from datetime import datetime, time
import re
import uuid
from urllib.parse import urlparse


class DynamicFlowValidator:
    def __init__(self, service_flow):
        """
        Initialize the validator with the expected service flow structure.
        :param service_flow: The dictionary structure returned by DynamicFlowHelper.
        """
        # Store the service flow passed to the validator
        self.service_flow = service_flow
        # Extract valid fields
        self.valid_fields = self.extract_valid_fields(service_flow)

    def extract_valid_fields(self, service_flow):
        valid_fields = {}
        for page in service_flow.get("service_flow", []):
            for category in page.get("categories", []):
                for field in category.get("fields", []):
                    valid_fields[field["name"]] = field
        return valid_fields

    def validate(self, received_data):
        validation_results = {
            "is_valid": True,
            "extra_keys": [],
            "missing_keys": [],
            "field_errors": {}
        }

        received_keys = set(received_data.get("case_data", {}).keys())
        valid_keys = set(self.valid_fields.keys())

        # Extra and missing keys
        validation_results["extra_keys"] = list(received_keys - valid_keys)
        validation_results["missing_keys"] = [
            field_name
            for field_name, field_info in self.valid_fields.items()
            if field_info.get("mandatory") and field_name not in received_keys
        ]

        for field_name, value in received_data.get("case_data", {}).items():
            if field_name in self.valid_fields:
                field_info = self.valid_fields[field_name]

                # Evaluate visibility conditions before validation
                if not self.evaluate_visibility_conditions(field_info, received_data.get("case_data", {})):
                    continue

                errors = self.validate_field_value(field_info, value)
                if errors:
                    validation_results["field_errors"][field_name] = errors

        if validation_results["field_errors"]:
            validation_results["is_valid"] = False

        # Remove extra keys from received data
        for key in validation_results["extra_keys"]:
            received_data["case_data"].pop(key, None)

        return validation_results  # Proceed even with missing keys

    def evaluate_visibility_conditions(self, field_info, case_data):
        """
        Evaluate visibility conditions for a field.
        :param field_info: The metadata for the field.
        :param case_data: The received data for the case.
        :return: True if the field should be visible, False otherwise.
        """
        visibility_conditions = field_info.get("visibility_conditions", [])
        for condition in visibility_conditions:
            condition_logic = condition.get("condition_logic", [])
            if not self.evaluate_condition_logic(condition_logic, case_data):
                return False
        return True

    def evaluate_condition_logic(self, condition_logic, case_data):
        """
        Evaluate a list of conditions in the condition logic.
        :param condition_logic: The list of conditions.
        :param case_data: The received data for the case.
        :return: True if all conditions are met, False otherwise.
        """
        try:
            result = True
            for condition in condition_logic:
                field_name = condition["field"]
                operation = condition["operation"]
                value = condition["value"]
                field_value = case_data.get(field_name)

                if operation == "=":
                    result = result and (field_value == value)
                elif operation == "!=":
                    result = result and (field_value != value)
                elif operation == ">":
                    result = result and (field_value > value)
                elif operation == "<":
                    result = result and (field_value < value)
                elif operation == ">=":
                    result = result and (field_value >= value)
                elif operation == "<=":
                    result = result and (field_value <= value)
                elif operation == "contains":
                    result = result and (str(value) in str(field_value))
                elif operation == "startswith":
                    result = result and str(field_value).startswith(str(value))
                elif operation == "endswith":
                    result = result and str(field_value).endswith(str(value))
                elif operation == "matches":
                    result = result and bool(re.match(value, str(field_value)))
                elif operation == "in":
                    result = result and (field_value in value)
                elif operation == "not in":
                    result = result and (field_value not in value)

            return result
        except Exception:
            return False

    def fetch_lookup_choices(self, lookup_field):
        """
        Fetch valid lookup choices for a given lookup field based on the Lookup model.
        :param lookup_field: The code or identifier for the lookup field.
        :return: A list of valid lookup IDs.
        """
        try:
            parent_lookup = Lookup.objects.get(
                name=lookup_field,
                type=Lookup.LookupTypeChoices.LOOKUP)
        except Lookup.DoesNotExist:
            return []  # Return an empty list if the parent lookup doesn't exist

        # Retrieve all active child lookups related to the parent lookup
        child_lookups = Lookup.objects.filter(
            parent_lookup=parent_lookup,
            active_ind=True,  # Only include active lookups
            type=Lookup.LookupTypeChoices.LOOKUP_VALUE
        )

        # Return the list of child lookup IDs
        return list(child_lookups.values_list('id', flat=True))

    def validate_field_value(self, field_info, value):
        """
        Validate a single field's value against the provided field metadata.
        :param field_info: Metadata for the field (e.g., mandatory, max length, etc.).
        :param value: The value of the field to validate.
        :return: A list of error messages, or an empty list if the field is valid.
        """
        errors = []

        # Extract field type
        field_type = field_info.get("field_type").lower()

        # Check for mandatory field
        if field_info.get("mandatory") and value is None:
            errors.append("This field is mandatory.")

        # General validations for string fields
        if field_type in {"text", "textarea", "rich_text",
                          "password", "slug", "email",
                          "url", "phone_number"}:
            if not isinstance(value, str):
                errors.append(
                    f"Expected a string for "
                    f"{field_type} but got {type(value).__name__}.")
            else:
                # Length checks
                max_length = field_info.get("max_length")
                min_length = field_info.get("min_length")
                regex_pattern = field_info.get("regex_pattern")
                allowed_characters = field_info.get("allowed_characters")
                forbidden_words = field_info.get("forbidden_words")

                if max_length and len(value) > max_length:
                    errors.append(f"Length must not exceed {max_length} characters.")
                if min_length and len(value) < min_length:
                    errors.append(f"Length must be at least {min_length} characters.")
                if regex_pattern and not re.match(regex_pattern, value):
                    errors.append("Value does not match the required pattern.")
                if allowed_characters and not re.match(f"^[{allowed_characters}]+$", value):
                    errors.append("Value contains invalid characters.")
                if forbidden_words and any(word in value for word in forbidden_words):
                    errors.append("Value contains forbidden words.")

        # Numeric fields validation
        if field_type in {"number", "decimal", "currency", "percentage", "rating"}:
            if not isinstance(value, (int, float)):
                errors.append("Expected a numeric value.")
            else:
                if field_info.get("positive_only") and value < 0:
                    errors.append("Value must be positive.")
                if field_info.get("integer_only") and not isinstance(value, int):
                    errors.append("Value must be an integer.")
                if field_info.get("value_greater_than") is not None and value <= field_info["value_greater_than"]:
                    errors.append(f"Value must be greater than {field_info['value_greater_than']}.")
                if field_info.get("value_less_than") is not None and value >= field_info["value_less_than"]:
                    errors.append(f"Value must be less than {field_info['value_less_than']}.")
                precision = field_info.get("precision")
                if precision is not None and isinstance(value, float):
                    if len(str(value).split(".")[-1]) > precision:
                        errors.append(f"Value must have at most {precision} decimal places.")

        # Email validation
        if field_type == "email":
            email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA0-9-]+\.[a-zA-Z0-9-.]+$"
            if not re.match(email_pattern, value):
                errors.append("Invalid email format.")

        # URL validation
        if field_type == "url":
            parsed = urlparse(value)
            if not (parsed.scheme and parsed.netloc):
                errors.append("Invalid URL format.")

        # Boolean validation
        if field_type == "boolean":
            if not isinstance(value, bool):
                errors.append(
                    f"Expected a boolean value but "
                    f"got {type(value).__name__}.")

        # Date and time validations
        if field_type in {"date", "datetime", "time"}:
            date_format = "%Y-%m-%d" \
                if field_type == "date" \
                else "%Y-%m-%d %H:%M:%S" \
                if field_type == "datetime" \
                else None
            try:
                if field_type == "date":
                    datetime.strptime(value, date_format)
                elif field_type == "datetime":
                    datetime.strptime(value, date_format)
                elif field_type == "time":
                    time.fromisoformat(value)
            except (ValueError, TypeError):
                errors.append(f"Invalid {field_type} format.")

        # Lookup and allowed lookups validation
        if field_type in {"choice", "multi_choice"}:
            parent_lookup_name = field_info.get("lookup", None)
            if parent_lookup_name:
                try:
                    parent_lookup = Lookup.objects.get(name=parent_lookup_name)
                    valid_choices = list(parent_lookup.lookup_children.filter(
                        type=Lookup.LookupTypeChoices.LOOKUP_VALUE,
                        active_ind=True
                    ).values_list('id', flat=True))

                    if field_type == "choice":
                        if value not in valid_choices:
                            errors.append(f"Invalid choice. "
                                          f"Allowed values: {valid_choices}.")
                    elif field_type == "multi_choice":
                        if not isinstance(value, list):
                            errors.append("Expected a list for multi-choice field.")
                        elif any(item not in valid_choices for item in value):
                            invalid_values = [
                                item for item in value
                                if item not in valid_choices]
                            errors.append(
                                f"Invalid multi-choice values: "
                                f"{invalid_values}. Allowed values: {valid_choices}.")
                except Lookup.DoesNotExist:
                    errors.append(
                        f"Field '{field_info.get('name')}' "
                        f"has an invalid lookup name '{parent_lookup_name}'.")
            else:
                errors.append(
                    f"Field '{field_info.get('name')}' "
                    f"is missing a valid lookup.")

        # File and image validations
        if field_type in {"file", "image"}:
            if not isinstance(value, str):
                errors.append("Expected a file path as a string.")
            # Add additional checks for file size,
            # format, etc., if metadata is available

        # JSON field validation (handling children_list)
        if field_type == "json":
            if isinstance(value, list):  # If the value is a list (children_list)
                sub_fields = field_info.get("sub_fields", [])
                grouped_errors = []  # To store errors by item index
                # Iterate through each item in the children_list
                for index, item in enumerate(value):
                    if isinstance(item, dict):  # Ensure each item is a dictionary
                        item_errors = []  # Collect errors for this item

                        # Now check the sub-fields for
                        # each dictionary in the children_list
                        for sub_field_info in sub_fields:
                            sub_field_name = sub_field_info.get("name")
                            # Get the value from the item
                            sub_field_value = item.get(sub_field_name)

                            # Handle missing sub-field values
                            if sub_field_value is None:
                                item_errors.append(
                                    {"Sub-field": sub_field_name,
                                     "errors": [
                                         f"Sub-field '{sub_field_name}' "
                                         f"in item {index} is missing."]}
                                )
                            else:
                                # Validate the sub-field value
                                sub_field_errors = self.validate_field_value(
                                    sub_field_info, sub_field_value)
                                if sub_field_errors:
                                    item_errors.append(
                                        {"Sub-field": sub_field_name,
                                         "errors": sub_field_errors}
                                    )
                        # Only add to grouped errors if
                        # there are any errors for this item
                        if item_errors:
                            grouped_errors.append({
                                "item_index": index,
                                "errors": item_errors
                            })

                    else:
                        errors.append(f"Expected a dictionary "
                                      f"for item {index} in the children_list.")

                # Add the grouped errors directly to
                # the children_list, no extra 'children_list' key
                if grouped_errors:
                    errors.append(grouped_errors)

            else:
                errors.append("Expected a list for JSON field validation.")

        # Array validation
        if field_type == "array":
            if not isinstance(value, list):
                errors.append("Expected an array (list).")

        # UUID validation
        if field_type == "uuid":
            try:
                uuid.UUID(value)
            except ValueError:
                errors.append("Invalid UUID format.")

        # Geographical validations
        if field_type == "coordinates":
            if not isinstance(value, (list, tuple)) or len(value) != 2:
                errors.append("Expected a list or tuple with "
                              "two elements (latitude, longitude).")
            else:
                lat, lon = value
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    errors.append("Invalid coordinates. "
                                  "Latitude must be between -90 and "
                                  "90, and longitude between -180 and 180.")

        # Handle disabled fields
        if field_info.get("is_disabled") and value is not None:
            errors.append("This field is disabled and cannot be modified.")

        return errors
