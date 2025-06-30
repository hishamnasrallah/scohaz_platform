
from datetime import datetime
from reporting.middleware import get_current_user
from django.db import models
from django.core.exceptions import ValidationError
from django.apps import apps


class ModelCommonMixin(models.Model):
    """
    A mixin that adds created_at, updated_at, plus dynamic validation logic in clean().
    """

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reporting_created_%(class)s_set"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reporting_updated_%(class)s_set"
    )

    class Meta:
        abstract = True

    def __str__(self):
        return self.name if self.name else f"{self.__class__.__name__} (ID: {self.id})"

    def clean(self):
        """
        The single source of truth for dynamic validation rules.
        Raises ValidationError if any rule fails.
        """
        super().clean()

        user = getattr(self, '_validation_user', None) or get_current_user()  # or another approach to get the current user
        if not user:
            raise ValidationError("User context is missing.")

        # 1) Grab relevant ValidationRule objects
        ValidationRuleModel = apps.get_model('reporting', 'ValidationRule')
        model_name = self.__class__.__name__
        rules = ValidationRuleModel.objects.filter(model_name=model_name)

        # 2) Build record_data for ConditionEvaluator
        record_data = {}
        for field in self._meta.fields:
            field_name = field.name
            record_data[field_name] = getattr(self, field_name, None)

        # 3) Loop over rules
        for rule in rules:
            # --- (a) check user_roles ---
            if rule.user_roles.exists():
                user_groups = set(user.groups.all())
                required_roles = set(rule.user_roles.all())

                # If you truly want to BLOCK the user from saving if they lack these roles, you can:
                if not user_groups.intersection(required_roles):
                    # Raise an error if this field requires a certain role
                    raise ValidationError({
                        rule.field_name: rule.error_message or "You do not have permission to modify this field."
                    })
                    # Or "skip" the rule if you only want to skip that rule's validation,
                    # but typically you'd raise an error if the user is unauthorized.
            if rule.validator_type == 'regex':
                pass
            elif rule.validator_type == 'condition':
                # --- (b) condition logic (skip or fail) ---
                if rule.condition_logic:
                    cond_eval = None #ConditionEvaluator(record_data)
                    evaluation_result = cond_eval.evaluate(rule.condition_logic)
                    if not evaluation_result:
                        # If the condition is not satisfied, do you want to skip this rule
                        # or block saving? Typically "skip" means "don't validate this rule."
                        # So we just continue:
                        raise ValidationError({rule.field_name: rule.error_message})
            elif rule.validator_type == 'function':
                # --- (c) apply the actual validation (regex, function, etc.) ---
                validator = None #VALIDATOR_REGISTRY[rule.function_name]
                if not validator:
                    raise ValidationError({
                        "__all__": f"Unknown validation rule type: {rule.validator_type}, {rule.function_name}"
                    })

                try:
                    params = self._prepare_validator_params(rule)
                    field_value = getattr(self, rule.field_name, None)

                    # If your validator fails, it should raise ValidationError itself
                    validator(
                        field_value,
                        rule,
                        **params,
                    )
                except ValidationError as ve:
                    # re-raise so admin shows it near `rule.field_name`
                    raise ValidationError({rule.field_name: ve.messages})
                except Exception as e:
                    raise ValidationError({rule.field_name: str(e)})

    def _prepare_validator_params(self, rule):
        """Helper to parse rule.params or validator_type to pass to validator."""
        rule_params = getattr(rule, 'function_params', {}) or {}
        validator_type = rule.validator_type

        if validator_type == 'max_length':
            return [rule_params.get('max_length')]
        elif validator_type == 'regex':
            return [rule_params.get('pattern')]
        elif validator_type == 'custom':
            return [rule_params.get('function_path')]
        elif validator_type == 'choice':
            return [rule_params.get('choices')]
        return rule_params

    def set_validation_user(self, user):
        """If needed, store the user for use in validations."""
        setattr(self, '_validation_user', user)
