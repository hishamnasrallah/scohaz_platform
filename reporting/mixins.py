from ab_app.forms import DynamicFormBuilder
from ab_app.crud.managers import user_can
import json
from ab_app.utils.custom_validation import VALIDATOR_REGISTRY
from ab_app.utils.condition_evaluator import ConditionEvaluator
from datetime import datetime
from ab_app.middleware import get_current_user
from ab_app.logger import logger
from django.db import models
from django.core.exceptions import ValidationError
from django.apps import apps


class DynamicAdminMixin:
    context_name = "admin"

    # ---------------
    # PERMISSION CHECKS
    # ---------------
    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        object_id = obj.pk if obj else None
        return user_can(request.user, "read", self.model, self.context_name, object_id)

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True
        return user_can(request.user, "create", self.model, self.context_name)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        object_id = obj.pk if obj else None
        return user_can(request.user, "update", self.model, self.context_name, object_id)

    def has_delete_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        object_id = obj.pk if obj else None
        return user_can(request.user, "delete", self.model, self.context_name, object_id)

    # ---------------
    # DYNAMIC FORM GENERATION
    # ---------------
    def get_form(self, request, obj=None, **kwargs):
        """
        Return a dynamically built form class with Django admin widgets
        and field-level adjustments (e.g., DateTime split, file input, etc.).
        """
        from django import forms
        from django.db import models
        from django.contrib.admin.widgets import (
            AdminDateWidget,
            AdminSplitDateTime,
            AdminTimeWidget,
            FilteredSelectMultiple,
        )
        from django.utils.dateparse import parse_date, parse_time
        from datetime import datetime, date, time

        class CustomDynamicForm(DynamicFormBuilder):
            class Meta:
                model = self.model
                fields = "__all__"

            def __init__(self_inner, *args, **inner_kwargs):
                inner_kwargs.setdefault('user', request.user)
                super().__init__(*args, **inner_kwargs)

                for field_name, field in self_inner.fields.items():
                    try:
                        model_field = self.model._meta.get_field(field_name)

                        # Date-only field
                        if isinstance(model_field, models.DateField) and not isinstance(model_field, models.DateTimeField):
                            field.widget = AdminDateWidget()

                        # DateTime field with safe clean() and to_python()
                        elif isinstance(model_field, models.DateTimeField):
                            field.widget = AdminSplitDateTime()
                            original_clean = field.clean
                            original_to_python = field.to_python

                            # Patch .clean()
                            def split_clean(value, *args, **kwargs):
                                if isinstance(value, list) and len(value) == 2:
                                    date_value, time_value = value

                                    if isinstance(date_value, str):
                                        date_part = parse_date(date_value)
                                    elif isinstance(date_value, date):
                                        date_part = date_value
                                    else:
                                        date_part = None

                                    if isinstance(time_value, str):
                                        time_part = parse_time(time_value)
                                    elif isinstance(time_value, time):
                                        time_part = time_value
                                    else:
                                        time_part = None

                                    if date_part and time_part:
                                        return datetime.combine(date_part, time_part)

                                    return None  # Fail silently with None instead of calling original

                                return original_clean(value, *args, **kwargs)

                            # Patch .to_python() to support .has_changed() logic
                            def split_to_python(value):
                                if isinstance(value, list) and len(value) == 2:
                                    date_value, time_value = value

                                    if isinstance(date_value, str):
                                        date_part = parse_date(date_value)
                                    elif isinstance(date_value, date):
                                        date_part = date_value
                                    else:
                                        date_part = None

                                    if isinstance(time_value, str):
                                        time_part = parse_time(time_value)
                                    elif isinstance(time_value, time):
                                        time_part = time_value
                                    else:
                                        time_part = None

                                    if date_part and time_part:
                                        return datetime.combine(date_part, time_part)

                                    # If it's a list but we can't parse it, return None (not the original method)
                                    return None

                                # Only call the original if NOT a list
                                return original_to_python(value)

                            field.clean = split_clean
                            field.to_python = split_to_python

                        # Time-only field
                        elif isinstance(model_field, models.TimeField):
                            field.widget = AdminTimeWidget()

                        # Text area for long text
                        elif isinstance(model_field, models.TextField):
                            field.widget = forms.Textarea(attrs={'rows': 4})

                        # File/image upload
                        elif isinstance(model_field, models.FileField):
                            field.widget = forms.ClearableFileInput()

                        # ManyToMany fields with dual select box
                        elif isinstance(model_field, models.ManyToManyField):
                            related_model = model_field.remote_field.model
                            queryset = related_model.objects.all()

                            self_inner.fields[field_name] = forms.ModelMultipleChoiceField(
                                queryset=queryset,
                                required=not model_field.blank,
                                label=model_field.verbose_name,
                                widget=FilteredSelectMultiple(model_field.verbose_name, is_stacked=False)
                            )

                        # field.widget = FilteredSelectMultiple(model_field.verbose_name, is_stacked=False)

                        # Optional enhancements (UX improvements)
                        elif isinstance(model_field, models.EmailField):
                            field.widget = forms.EmailInput()
                        elif isinstance(model_field, models.URLField):
                            field.widget = forms.URLInput()
                        elif isinstance(model_field, models.IntegerField):
                            field.widget = forms.NumberInput()
                        elif isinstance(model_field, (models.DecimalField, models.FloatField)):
                            field.widget = forms.NumberInput(attrs={'step': 'any'})

                    except Exception:
                        # Skip virtual or dynamically excluded fields
                        continue

        return CustomDynamicForm

    # ---------------
    # SAVE MODEL
    # ---------------
    def save_model(self, request, obj, form, change):
        """
        Inject user into model context and trigger clean validation.
        """
        obj.set_validation_user(request.user)

        if not obj.created_by:
            obj.created_by = request.user
        obj.updated_by = request.user

        from django.core.exceptions import ValidationError as DjangoValidationError
        try:
            obj.full_clean()  # triggers your dynamic validation
            super().save_model(request, obj, form, change)
        except DjangoValidationError as e:
            form.add_error(None, e)
            raise e

# class DynamicAdminMixin:
#     context_name = "admin"
# 
#     # ---------------
#     # PERMISSION CHECKS
#     # ---------------
#     def has_view_permission(self, request, obj=None):
#         if request.user.is_superuser:
#             return True
#         object_id = obj.pk if obj else None
#         return user_can(request.user, "read", self.model, self.context_name, object_id)
# 
#     def has_add_permission(self, request):
#         if request.user.is_superuser:
#             return True
#         return user_can(request.user, "create", self.model, self.context_name)
# 
#     def has_change_permission(self, request, obj=None):
#         if request.user.is_superuser:
#             return True
#         object_id = obj.pk if obj else None
#         return user_can(request.user, "update", self.model, self.context_name, object_id)
# 
#     def has_delete_permission(self, request, obj=None):
#         if request.user.is_superuser:
#             return True
#         object_id = obj.pk if obj else None
#         return user_can(request.user, "delete", self.model, self.context_name, object_id)
# 
#     # ---------------
#     # DYNAMIC FORM GENERATION
#     # ---------------
#     def get_form(self, request, obj=None, **kwargs):
#         """
#         Return a dynamically built form class with Django admin widgets
#         and field-level adjustments (e.g., DateTime split, file input, etc.).
#         """
#         from django import forms
#         from django.db import models
#         from django.contrib.admin.widgets import (
#             AdminDateWidget,
#             AdminSplitDateTime,
#             AdminTimeWidget,
#             FilteredSelectMultiple,
#         )
#         from django.utils.dateparse import parse_date, parse_time
#         from datetime import datetime, date, time
# 
#         class CustomDynamicForm(DynamicFormBuilder):
#             class Meta:
#                 model = self.model
#                 fields = "__all__"
# 
#             def __init__(self_inner, *args, **inner_kwargs):
#                 inner_kwargs.setdefault('user', request.user)
#                 super().__init__(*args, **inner_kwargs)
# 
#                 for field_name, field in self_inner.fields.items():
#                     try:
#                         model_field = self.model._meta.get_field(field_name)
# 
#                         # Date-only field
#                         if isinstance(model_field, models.DateField) and not isinstance(model_field, models.DateTimeField):
#                             field.widget = AdminDateWidget()
# 
#                         # DateTime field with safe clean() and to_python()
#                         elif isinstance(model_field, models.DateTimeField):
#                             field.widget = AdminSplitDateTime()
#                             original_clean = field.clean
#                             original_to_python = field.to_python
# 
#                             # Patch .clean()
#                             def split_clean(value, *args, **kwargs):
#                                 if isinstance(value, list) and len(value) == 2:
#                                     date_value, time_value = value
# 
#                                     if isinstance(date_value, str):
#                                         date_part = parse_date(date_value)
#                                     elif isinstance(date_value, date):
#                                         date_part = date_value
#                                     else:
#                                         date_part = None
# 
#                                     if isinstance(time_value, str):
#                                         time_part = parse_time(time_value)
#                                     elif isinstance(time_value, time):
#                                         time_part = time_value
#                                     else:
#                                         time_part = None
# 
#                                     if date_part and time_part:
#                                         return datetime.combine(date_part, time_part)
# 
#                                     return None  # Fail silently with None instead of calling original
# 
#                                 return original_clean(value, *args, **kwargs)
# 
#                             # Patch .to_python() to support .has_changed() logic
#                             def split_to_python(value):
#                                 if isinstance(value, list) and len(value) == 2:
#                                     date_value, time_value = value
# 
#                                     if isinstance(date_value, str):
#                                         date_part = parse_date(date_value)
#                                     elif isinstance(date_value, date):
#                                         date_part = date_value
#                                     else:
#                                         date_part = None
# 
#                                     if isinstance(time_value, str):
#                                         time_part = parse_time(time_value)
#                                     elif isinstance(time_value, time):
#                                         time_part = time_value
#                                     else:
#                                         time_part = None
# 
#                                     if date_part and time_part:
#                                         return datetime.combine(date_part, time_part)
# 
#                                     # If it's a list but we can't parse it, return None (not the original method)
#                                     return None
# 
#                                 # Only call the original if NOT a list
#                                 return original_to_python(value)
# 
#                             field.clean = split_clean
#                             field.to_python = split_to_python
# 
#                         # Time-only field
#                         elif isinstance(model_field, models.TimeField):
#                             field.widget = AdminTimeWidget()
# 
#                         # Text area for long text
#                         elif isinstance(model_field, models.TextField):
#                             field.widget = forms.Textarea(attrs={'rows': 4})
# 
#                         # File/image upload
#                         elif isinstance(model_field, models.FileField):
#                             field.widget = forms.ClearableFileInput()
# 
#                         # ManyToMany fields with dual select box
#                         elif isinstance(model_field, models.ManyToManyField):
#                             field.widget = FilteredSelectMultiple(model_field.verbose_name, is_stacked=False)
# 
#                         # Optional enhancements (UX improvements)
#                         elif isinstance(model_field, models.EmailField):
#                             field.widget = forms.EmailInput()
#                         elif isinstance(model_field, models.URLField):
#                             field.widget = forms.URLInput()
#                         elif isinstance(model_field, models.IntegerField):
#                             field.widget = forms.NumberInput()
#                         elif isinstance(model_field, (models.DecimalField, models.FloatField)):
#                             field.widget = forms.NumberInput(attrs={'step': 'any'})
# 
#                     except Exception:
#                         # Skip virtual or dynamically excluded fields
#                         continue
# 
#         return CustomDynamicForm
# 
#     # ---------------
#     # SAVE MODEL
#     # ---------------
#     def save_model(self, request, obj, form, change):
#         """
#         Inject user into model context and trigger clean validation.
#         """
#         obj.set_validation_user(request.user)
# 
#         if not obj.created_by:
#             obj.created_by = request.user
#         obj.updated_by = request.user
# 
#         from django.core.exceptions import ValidationError as DjangoValidationError
#         try:
#             obj.full_clean()  # triggers your dynamic validation
#             super().save_model(request, obj, form, change)
#         except DjangoValidationError as e:
#             form.add_error(None, e)
#             raise e



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
        related_name="ab_app_created_%(class)s_set"
    )
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ab_app_updated_%(class)s_set"
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
        ValidationRuleModel = apps.get_model('ab_app', 'ValidationRule')
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
                    cond_eval = ConditionEvaluator(record_data)
                    evaluation_result = cond_eval.evaluate(rule.condition_logic)
                    if not evaluation_result:
                        # If the condition is not satisfied, do you want to skip this rule
                        # or block saving? Typically "skip" means "don't validate this rule."
                        # So we just continue:
                        raise ValidationError({rule.field_name: rule.error_message})
            elif rule.validator_type == 'function':
                # --- (c) apply the actual validation (regex, function, etc.) ---
                validator = VALIDATOR_REGISTRY[rule.function_name]
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
