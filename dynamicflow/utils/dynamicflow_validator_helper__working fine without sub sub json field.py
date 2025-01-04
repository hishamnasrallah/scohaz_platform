from icecream import ic

from lookup.models import Lookup
from datetime import datetime, time
import re
import uuid
from urllib.parse import urlparse
from typing import Any, Dict, List


class DynamicFlowValidator:
    def __init__(self, service_flow: Dict[str, Any], case_obj, received_data: Dict[str, Any], submit=False):
        """
        Initialize the validator with the expected service flow structure.
        :param service_flow: The dictionary structure returned by DynamicFlowHelper.
        """
        self.service_flow = service_flow
        self.received_data = received_data
        self.valid_fields = None
        self.submit = submit
        self.case_obj = case_obj
        self.merged_data = None
        self.merge_data()

    def merge_data(self):
        case_data = self.received_data.get("case_data", {})
        # Merge stored case data with request body (override stored values with request body values)
        self.merged_data = self.case_obj.case_data.copy() if self.case_obj else {}
        self.merged_data.update(case_data)
        self.valid_fields = self.extract_valid_fields(self.service_flow, self.merged_data)

    def extract_valid_fields(self, service_flow: Dict[str, Any], case_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Extract all valid fields from the service flow, excluding invisible fields based on visibility conditions.
        :param service_flow: The service flow definition.
        :param case_data: The current case data to evaluate visibility conditions.
        :return: A dictionary of valid and visible fields.
        """
        valid_fields = {}

        def process_fields(fields, path=""):
            for field in fields:
                field_name = field["name"]
                current_path = f"{path}.{field_name}" if path else field_name

                # Check if the field is visible based on its conditions
                if self.evaluate_visibility_conditions(field, case_data):
                    valid_fields[current_path] = field

                    sub_fields = field.get("sub_fields", [])
                    if sub_fields:
                        process_fields(sub_fields, path=current_path)

        for page in service_flow.get("service_flow", []):
            for category in page.get("categories", []):
                process_fields(category.get("fields", []))

        return valid_fields

    def validate(self) -> Dict[str, Any]:
        """
        Validate the received data against the expected fields.
        """
        validation_results = {
            "is_valid": True,
            "extra_keys": [],
            "missing_keys": [],
            "field_errors": {}
        }

        ic(self.merged_data)
        received_keys = set(self.merged_data.keys())

        valid_keys = set(self.valid_fields.keys())
        if "uploaded_files" not in valid_keys:
            valid_keys.add("uploaded_files")
        # Identify extra keys
        validation_results["extra_keys"] = list(received_keys - valid_keys)

        # Check for missing mandatory fields
        for field_path, field_info in self.valid_fields.items():
            if field_info.get("mandatory") and not self.is_parent_optional(self.merged_data, field_path):
                field_value = self.get_nested_value(self.merged_data, field_path)
                if field_value is None:
                    validation_results["missing_keys"].append(field_path)

        # Validate each field
        for field_path, value in self.merged_data.items():
            if field_path in self.valid_fields:
                field_info = self.valid_fields[field_path]

                # Check visibility conditions before validation
                evaluated_visibility_condition = self.evaluate_visibility_conditions(field_info, self.merged_data)

                if not evaluated_visibility_condition and not self.merged_data[field_info["name"]]:
                    continue
                elif not evaluated_visibility_condition and self.merged_data[field_info["name"]]:
                    validation_results["extra_keys"].append(field_info["name"])
                    continue
                else:
                    errors = self._validate_field_value(field_info, value)
                    if errors:
                        validation_results["field_errors"][field_path] = errors
        if self.submit:
            if validation_results["field_errors"] or validation_results["missing_keys"]:
                validation_results["is_valid"] = False
        else:
            if validation_results["field_errors"]:
                validation_results["is_valid"] = False

        # Remove extra keys from received data
        for key in validation_results["extra_keys"]:
            self.merged_data.pop(key, None)

        return validation_results

    def evaluate_visibility_conditions(self, field_info: Dict[str, Any], merged_data: Dict[str, Any]) -> bool:
        """
        Evaluate visibility conditions for a field.
        """
        visibility_conditions = field_info.get("visibility_conditions", [])
        for condition in visibility_conditions:
            condition_logic = condition.get("condition_logic", [])
            if not self._evaluate_condition_logic(condition_logic, merged_data):
                return False
        return True

    def _evaluate_condition_logic(self, condition_logic: List[Dict[str, Any]], merged_data: Dict[str, Any]) -> bool:
        """
        Evaluate a list of conditions in the condition logic.
        """
        try:
            result = True
            for condition in condition_logic:
                field_name = condition["field"]
                operation = condition["operation"]
                value = condition["value"]
                field_value = merged_data.get(field_name)

                result = result and self._evaluate_single_condition(field_value, operation, value)

            return result
        except Exception:
            return False

    def _evaluate_single_condition(self, field_value: Any, operation: str, value: Any) -> bool:
        """Evaluate a single condition."""
        operations = {
            "=": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            ">": lambda a, b: a > b,
            "<": lambda a, b: a < b,
            ">=": lambda a, b: a >= b,
            "<=": lambda a, b: a <= b,
            "contains": lambda a, b: str(b) in str(a),
            "startswith": lambda a, b: str(a).startswith(str(b)),
            "endswith": lambda a, b: str(a).endswith(str(b)),
            "matches": lambda a, b: bool(re.match(b, str(a))),
            "in": lambda a, b: a in b,
            "not in": lambda a, b: a not in b,
        }
        return operations.get(operation, lambda a, b: False)(field_value, value)

    def fetch_lookup_choices(self, lookup_field: str) -> List[int]:
        """Fetch valid lookup choices for a given lookup field."""
        try:
            parent_lookup = Lookup.objects.get(name=lookup_field, type=Lookup.LookupTypeChoices.LOOKUP)
        except Lookup.DoesNotExist:
            return []

        child_lookups = Lookup.objects.filter(
            parent_lookup=parent_lookup,
            active_ind=True,
            type=Lookup.LookupTypeChoices.LOOKUP_VALUE
        )

        return list(child_lookups.values_list('id', flat=True))

    def is_parent_optional(self, merged_data: Dict[str, Any], field_path: str) -> bool:
        """Check if the parent field of a given field is optional and not filled."""
        path_parts = field_path.split(".")
        for i in range(len(path_parts) - 1):
            parent_path = ".".join(path_parts[:i + 1])
            parent_value = self.get_nested_value(merged_data, parent_path)
            if parent_value is None:
                parent_field_info = self.valid_fields.get(parent_path)
                if parent_field_info and not parent_field_info.get("mandatory", False):
                    return True
        return False

    def get_nested_value(self, data: Dict[str, Any], field_path: str) -> Any:
        """Retrieve the value from nested data using a dot-separated path."""
        keys = field_path.split(".")
        for key in keys:
            if isinstance(data, dict) and key in data:
                data = data[key]
            else:
                return None
        return data

    def _validate_field_value(self, field_info: Dict[str, Any], value: Any) -> List[str]:
        """Validate a single field's value against the provided field metadata."""
        errors = []
        field_type = field_info.get("field_type", "").lower()

        # Check for mandatory field
        if field_info.get("mandatory") and value is None:
            errors.append("This field is mandatory.")

        # General field validation
        validation_method = getattr(self, f"_validate_{field_type}", None)
        print("validators: ", field_info["name"])
        if validation_method:
            errors.extend(validation_method(value, field_info))

        return errors

    # Add all field-specific validation methods here (e.g., _validate_text, _validate_number, etc.)

    def _validate_text(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        errors = []
        if not isinstance(value, str):
            errors.append("Expected a string value.")
        errors.extend(self._validate_string_constraints(value, field_info))
        return errors


    def _validate_number(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        if not isinstance(value, (int, float)):
            return ["Expected a numeric value."]
        return self._validate_numeric_constraints(value, field_info)


    def _validate_boolean(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        if not isinstance(value, bool):
            return ["Expected a boolean value."]
        return []


    def _validate_email(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        if not isinstance(value, str) or not re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", value):
            return ["Invalid email format."]
        return []


    def _validate_url(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        if not isinstance(value, str) or not urlparse(value).scheme:
            return ["Invalid URL format."]
        return []


    def _validate_date(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        errors = []
        try:
            datetime.strptime(value, "%Y-%m-%d")
            errors.extend(self._validate_date_constraints(value, field_info))
        except (ValueError, TypeError):
            errors.append("Invalid date format. Expected YYYY-MM-DD.")
        return errors


    def _validate_datetime(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        try:
            datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        except (ValueError, TypeError):
            return ["Invalid datetime format. Expected YYYY-MM-DD HH:MM:SS."]
        return []


    def _validate_time(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        try:
            time.fromisoformat(value)
        except (ValueError, TypeError):
            return ["Invalid time format. Expected HH:MM:SS."]
        return []


    def _validate_uuid(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        try:
            uuid.UUID(value)
        except (ValueError, TypeError):
            return ["Invalid UUID format."]
        return []


    def _validate_choice(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        errors = []
        if not isinstance(value, (str, int)):
            errors.append("Expected a valid choice (string or integer).")
        else:
            valid_choices = self.fetch_lookup_choices(field_info.get("lookup"))
            if value not in valid_choices:
                errors.append(f"Invalid choice. Allowed values: {valid_choices}.")
        return errors


    def _validate_multi_choice(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        errors = []
        if not isinstance(value, list):
            errors.append("Expected a list for multi-choice field.")
        else:
            valid_choices = self.fetch_lookup_choices(field_info.get("lookup"))
            invalid_values = [item for item in value if item not in valid_choices]
            if invalid_values:
                errors.append(f"Invalid multi-choice values: {invalid_values}. Allowed values: {valid_choices}.")
        return errors


    def _validate_file(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        if not isinstance(value, str):
            return ["Expected a file path as a string."]
        return self._validate_file_constraints(value, field_info)

    def _validate_json(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        """
        Validate JSON fields with nested sub-fields recursively.
        """
        errors = []
        if not isinstance(value, list):
            return ["Expected a list for JSON field validation."]


        # Check constraints on the number of items
        max_items = field_info.get("max_length")  # Maximum number of objects allowed
        min_items = field_info.get("min_length")  # Minimum number of objects required

        if max_items is not None and len(value) > max_items:
            errors.append(f"List exceeds the maximum allowed number of items ({max_items}).")

        if min_items is not None and len(value) < min_items:
            errors.append(f"List has fewer items than the minimum required ({min_items}).")

        # Validate each item in the list
        sub_fields = field_info.get("sub_fields", [])
        for index, item in enumerate(value):
            if not isinstance(item, dict):
                errors.append(f"Expected a dictionary for item at index {index}.")
                continue

            # Recursively validate sub-fields
            errors.extend(self._validate_nested_fields(item, sub_fields, f"Item {index}"))

        return errors

    def _validate_nested_fields(self, data: Dict[str, Any], sub_fields: List[Dict[str, Any]], context: str) -> List[str]:
        """
        Recursively validate nested fields.
        :param data: The current level of data to validate.
        :param sub_fields: The list of sub-fields to validate at this level.
        :param context: The context for error messages (e.g., "Item 0", "Item 0.Sub-field").
        :return: A list of validation error messages.
        """
        errors = []
        for sub_field_info in sub_fields:
            sub_field_name = sub_field_info["name"]
            sub_field_value = data.get(sub_field_name)

            # Check if the sub-field is mandatory and missing
            if sub_field_value is None and sub_field_info.get("mandatory"):
                errors.append(f"{context}: Sub-field '{sub_field_name}' is missing.")

            # If sub-field has nested sub-fields, validate recursively
            nested_sub_fields = sub_field_info.get("sub_fields", [])
            if nested_sub_fields and sub_field_value is not None:
                if not isinstance(sub_field_value, list):
                    errors.append(f"{context}: Sub-field '{sub_field_name}' should be a list.")
                else:
                    for idx, nested_item in enumerate(sub_field_value):
                        if not isinstance(nested_item, dict):
                            errors.append(f"{context}.{sub_field_name}[{idx}]: Expected a dictionary.")
                            continue

                        nested_context = f"{context}.{sub_field_name}[{idx}]"
                        errors.extend(self._validate_nested_fields(nested_item, nested_sub_fields, nested_context))

            # Validate the current sub-field value if it exists
            elif sub_field_value is not None:
                sub_field_errors = self._validate_field_value(sub_field_info, sub_field_value)
                if sub_field_errors:
                    errors.append(f"{context}: Errors in sub-field '{sub_field_name}': {sub_field_errors}")

        return errors

    # def _validate_json(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
    #     errors = []
    #     if not isinstance(value, list):
    #         return ["Expected a list for JSON field validation."]
    #
    #     sub_fields = field_info.get("sub_fields", [])
    #     for index, item in enumerate(value):
    #         if not isinstance(item, dict):
    #             errors.append(f"Expected a dictionary for item at index {index}.")
    #             continue
    #
    #         for sub_field_info in sub_fields:
    #             sub_field_name = sub_field_info["name"]
    #             sub_field_value = item.get(sub_field_name)
    #             if sub_field_value is None and sub_field_info.get("mandatory"):
    #                 errors.append(f"Sub-field '{sub_field_name}' in item {index} is missing.")
    #             elif sub_field_value is not None:
    #                 sub_errors = self._validate_field_value(sub_field_info, sub_field_value)
    #                 if sub_errors:
    #                     errors.append(f"Errors in sub-field '{sub_field_name}' in item {index}: {sub_errors}")
    #
    #     return errors


    def _validate_array(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        if not isinstance(value, list):
            return ["Expected an array (list)."]
        return []


    def _validate_coordinates(self, value: Any, field_info: Dict[str, Any]) -> List[str]:
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            return ["Expected a list or tuple with two elements (latitude, longitude)."]

        lat, lon = value
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return ["Invalid coordinates. Latitude must be between -90 and 90, and longitude between -180 and 180."]
        return []


    # Helper methods for constraints

    def _validate_string_constraints(self, value: str, field_info: Dict[str, Any]) -> List[str]:
        errors = []
        max_length = field_info.get("max_length")
        min_length = field_info.get("min_length")
        regex_pattern = field_info.get("regex_pattern")

        if max_length and len(value) > max_length:
            errors.append(f"Length must not exceed {max_length} characters.")
        if min_length and len(value) < min_length:
            errors.append(f"Length must be at least {min_length} characters.")
        if regex_pattern and not re.match(regex_pattern, value):
            errors.append("Value does not match the required pattern.")

        return errors


    def _validate_numeric_constraints(self, value: float, field_info: Dict[str, Any]) -> List[str]:
        errors = []
        if field_info.get("positive_only") and value < 0:
            errors.append("Value must be positive.")
        if field_info.get("integer_only") and not isinstance(value, int):
            errors.append("Value must be an integer.")
        return errors
    def _validate_date_constraints(self, value: str, field_info: Dict[str, Any]) -> List[str]:
        errors = []
        date_format = "%Y-%m-%d"

        try:
            parsed_date = datetime.strptime(value, date_format)
            date_greater_than = field_info.get("date_greater_than")
            date_less_than = field_info.get("date_less_than")
            future_only = field_info.get("future_only")
            past_only = field_info.get("past_only")

            if date_greater_than and parsed_date <= date_greater_than:
                errors.append(f"Date must be after {date_greater_than.strftime(date_format)}.")
            if date_less_than and parsed_date >= date_less_than:
                errors.append(f"Date must be before {date_less_than.strftime(date_format)}.")
            if future_only and parsed_date <= datetime.now():
                errors.append("Date must be in the future.")
            if past_only and parsed_date >= datetime.now():
                errors.append("Date must be in the past.")
        except ValueError:
            errors.append("Invalid date format. Expected YYYY-MM-DD.")

        return errors

    def _validate_file_constraints(self, value: str, field_info: Dict[str, Any]) -> List[str]:
        errors = []
        allowed_file_types = field_info.get("file_types")
        max_file_size = field_info.get("max_file_size")

        # Check file extension
        if allowed_file_types:
            allowed_extensions = allowed_file_types.split(",")
            if not any(value.lower().endswith(ext.strip()) for ext in allowed_extensions):
                errors.append(f"Invalid file type. Allowed types: {allowed_extensions}.")

        # Note: To check file size, the actual file object would be needed.
        # This would typically be handled in the serializer rather than here.

        return errors
