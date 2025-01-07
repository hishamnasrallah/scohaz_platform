from datetime import datetime
from django.core.exceptions import ValidationError
import re

from crm.utils.conditions import ConditionEvaluator
from crm.utils.validators import VALIDATOR_REGISTRY

class DynamicValidationMixin:
    def clean(self):
        """
        The `clean` method runs the validation process based on the dynamically registered validation rules.
        """
        super().clean()

        # Import ValidationRule dynamically to avoid circular import
        from django.apps import apps
        ValidationRule = apps.get_model('crm', 'ValidationRule')

        # Get the model name
        model_name = self.__class__.__name__

        # Fetch validation rules for this model
        rules = ValidationRule.objects.filter(model_name=model_name)

        # Get the user from the instance's context (for context-sensitive validation)
        user = getattr(self, '_validation_user', None)

        # Debugging: Check if the user is set correctly
        if user:
            print(f"User found: {user.username}")
        else:
            print("No user set for validation. Make sure to call set_validation_user(user)")

        for rule in rules:
            # Skip rule if it's not a global rule and user-specific context is missing
            if not rule.global_rule and not user:
                continue

            # Debugging: Check if user roles are defined for the rule
            if rule.user_roles:
                print(f"Validating with roles: {rule.user_roles}")

            # Role-Based Validation (handle JSONField 'user_roles')
            if rule.user_roles and user:
                user_groups = set(user.groups.values_list('name', flat=True))
                required_roles = set(rule.user_roles)

                # Debugging: Print the user groups and the required roles to ensure proper matching
                print(f"User Groups: {user_groups}")
                print(f"Required Roles: {required_roles}")

                if not user_groups.intersection(required_roles):
                    print("Role validation failed. Skipping rule.")
                    continue  # Skip rules that don't match the user's roles

            # Condition-Based Validation using condition_logic (JSON)
            conditions = rule.condition_logic or []

            # Check if condition_logic is not empty, only then evaluate
            if conditions:
                condition_evaluator = ConditionEvaluator(self.__dict__)
                if not condition_evaluator.evaluate(conditions):
                    print("Condition logic failed. Skipping rule.")
                    continue  # Skip validation if conditions aren't met

            # Fetch the validator dynamically from the registry
            validator = VALIDATOR_REGISTRY.get(rule.rule_type)
            if not validator:
                raise ValidationError({
                    "__all__": f"Unknown validation rule type: {rule.rule_type}"
                })

            # Initialize params to ensure it's always defined
            params = []

            # Parse rule_value dynamically for specific validations
            try:
                if rule.rule_type == 'range':
                    # Handle range validation for dates
                    if ',' in rule.rule_value:
                        start_date_str, end_date_str = rule.rule_value.split(',')
                        start_date = datetime.strptime(start_date_str.strip(), '%Y-%m-%d').date()  # Convert to date
                        end_date = datetime.strptime(end_date_str.strip(), '%Y-%m-%d').date()  # Convert to date

                        # Get the actual value (e.g., due_date) from the model instance
                        field_value = getattr(self, rule.field_name, None)

                        # Ensure the value is of type `datetime.date` (convert if it's `datetime`)
                        if isinstance(field_value, datetime):
                            field_value = field_value.date()

                        # Validate if the field_value is within the range
                        if not (start_date <= field_value <= end_date):
                            raise ValidationError({
                                rule.field_name: f"Validation error: {rule.error_message}"
                            })

                        # Set params with start and end date for potential future use
                        params = [start_date, end_date]
                elif rule.rule_type == 'regex':
                    params = [rule.rule_value]  # The regex pattern to apply
                elif rule.rule_type == 'custom':
                    params = [rule.rule_value]  # The function path for custom validation
                elif rule.rule_type == 'choice':
                    params = [eval(rule.rule_value)]  # Safely parse the choices
                else:
                    params = [rule.rule_value]

                # Call the validator with appropriate arguments
                validator(
                    getattr(self, rule.field_name, None),
                    *params,
                    error_message=rule.error_message,
                    instance=self,
                    user=user
                )
            except Exception as e:
                raise ValidationError({
                    rule.field_name: f"Validation error: {str(e)}"
                })

    def set_validation_user(self, user):
        """
        Method to set the user for context-sensitive validation.
        """
        setattr(self, '_validation_user', user)
        # Debugging statement to confirm user is being set for validation
        print(f"User set for validation: {user.username}")

    def _evaluate_single_condition(self, field_value, operation, value):
        """
        Evaluate a single condition based on the operation.
        :param field_value: The current value of the field being validated.
        :param operation: The comparison operation.
        :param value: The value to compare against.
        :return: True if the condition is satisfied, False otherwise.
        """
        # Convert both field_value and value to comparable types
        if isinstance(field_value, datetime):
            field_value = field_value.date()  # Convert to date if it's a datetime object
        elif isinstance(value, str) and '-' in value:  # Check if it's a date string (yyyy-mm-dd)
            try:
                value = datetime.strptime(value, '%Y-%m-%d').date()
            except ValueError:
                pass  # Not a date, continue with string comparison

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

        # Apply the comparison operation
        return operations.get(operation, lambda a, b: False)(field_value, value)
