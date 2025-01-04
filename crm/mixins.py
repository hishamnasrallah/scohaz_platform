
from django.core.exceptions import ValidationError
from .utils.validators import VALIDATOR_REGISTRY


class DynamicValidationMixin:
    def clean(self):
        super().clean()

        # Import ValidationRule dynamically to avoid circular import
        from django.apps import apps
        ValidationRule = apps.get_model('crm', 'ValidationRule')

        # Get the model name
        model_name = self.__class__.__name__

        # Fetch validation rules for this model
        rules = ValidationRule.objects.filter(model_name=model_name)

        # Get the user from the instance's context
        user = getattr(self, '_validation_user', None)

        for rule in rules:
            # Skip rule if it's not a global rule and user-specific context is missing
            if not rule.global_rule and not user:
                continue

            # Role-Based Validation (handle JSONField 'user_roles')
            if rule.user_roles and user:
                user_groups = set(user.groups.values_list('name', flat=True))
                required_roles = set(rule.user_roles)
                if not user_groups.intersection(required_roles):
                    continue  # Skip rules that don't match the user's roles

            # Fetch the validator dynamically from the registry
            validator = VALIDATOR_REGISTRY.get(rule.rule_type)
            if not validator:
                raise ValidationError({
                    "__all__": f"Unknown validation rule type: {rule.rule_type}"
                })

            # Parse rule_value dynamically for specific validations
            try:
                if rule.rule_type == 'range':
                    params = [float(p) for p in rule.rule_value.split(',')]
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
        """Method to set the user for context-sensitive validation.""" 
        setattr(self, '_validation_user', user)
