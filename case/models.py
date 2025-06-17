import importlib
import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.db.models import Max


class Case(models.Model):
    """
    Case model with static fields and dynamic
    JSON field for additional case-specific data.
    """

    # Static Fields
    applicant = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,  # Reference to the custom user model
        on_delete=models.CASCADE,
        related_name="cases",
        verbose_name=_("Beneficiary")
    )
    applicant_type = models.ForeignKey(
        to="lookup.Lookup",
        related_name="case_applicant_type",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"parent_lookup__name": "Applicant Type"},
        verbose_name=_("Applicant Type"),
    )
    case_type = models.ForeignKey(
        to="lookup.Lookup",
        related_name="case_type",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"parent_lookup__name": "Service"},
        verbose_name=_("Case Type"),
    )
    serial_number = models.CharField(
        max_length=30,
        unique=True,
        editable=False,
        verbose_name=_("Serial Number")
    )
    assigned_group = models.ForeignKey(
        to="auth.Group",
        related_name="case_assigned_group",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Assigned Group"),
    )
    assigned_emp = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        related_name="case_assigned_emp",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Assigned Employee"),
    )
    current_approval_step = models.ForeignKey(
        to="conditional_approval.ApprovalStep",
        related_name="case_approval_step",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Current Approval Step"),
    )
    status = models.ForeignKey(
        to="lookup.Lookup",
        related_name="case_status",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"parent_lookup__name": "Case Status"},
        verbose_name=_("Status"),
    )
    sub_status = models.ForeignKey(
        to="lookup.Lookup",
        related_name="case_sub_status",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        limit_choices_to={"parent_lookup__name": "Case Sub Status"},
        verbose_name=_("Sub Status"),
    )
    last_action = models.ForeignKey(
        to="conditional_approval.Action",
        related_name="case_last_action",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        verbose_name=_("Last Action"),
    )
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True, verbose_name=_("Updated At")
    )
    created_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        related_name="created_cases",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Created By"),
    )
    updated_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        related_name="updated_cases",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Updated By"),
    )

    # Dynamic Data Field
    case_data = models.JSONField(
        null=True,
        blank=True,
        help_text=_("Store additional case-specific information."),
        verbose_name=_("Additional Data")
    )

    def save(self, *args, **kwargs):
        if not self.pk:  # Generate serial number only for new instances
            last_serial = Case.objects.filter(serial_number__isnull=False).aggregate(
                Max('serial_number')
            )['serial_number__max']
            self.serial_number = self.generate_serial_number(last_serial)

        super().save(*args, **kwargs)

    def generate_serial_number(self, last_serial):
        """
        Generate a new serial number based on the last serial number.
        """
        if last_serial:
            return str(int(last_serial) + 1).zfill(6)
        return "000001"

    def __str__(self):
        return f"Case #{self.serial_number}"


class ApprovalRecord(models.Model):
    case = models.ForeignKey(
        Case,
        on_delete=models.CASCADE,
        related_name='approval_records',
        help_text=_("The case associated with this approval record.")
    )
    approved_by = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='approval_records',
        help_text=_("The user who approved the case.")
    )
    approval_step = models.ForeignKey(
        to="conditional_approval.ApprovalStep",
        on_delete=models.CASCADE,
        related_name='approval_records',
        help_text=_("The approval step associated with this approval record.")
    )
    approved_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_("The timestamp when the approval was made.")
    )

    def __str__(self):
        return f"Approval by {self.approved_by} for {self.case} at step {self.approval_step}"



class CaseMapper(models.Model):
    """
    Defines the mapping configuration for a particular Case Type
    (and optionally sub-status or other criteria).
    """
    name = models.CharField(max_length=100, help_text="Name of this mapper config.")

    # Example linking to case_type (which might be a 'Lookup' or string)
    # You can adapt this to your needs
    case_type = models.CharField(
        max_length=100,
        help_text="Identifier or name of the case type. E.g. 'VacationRequest'."
    )
    version = models.PositiveIntegerField(default=1)  # version tracking
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='versions')  # link to previous version

    active_ind = models.BooleanField(default=True, help_text="Whether this mapper is active.")

    # Optionally, you can add sub_status, etc. if you want finer scoping:
    # sub_status = models.CharField(max_length=100, null=True, blank=True, ...)

    def __str__(self):
        return f"{self.name} (type={self.case_type})"


class MapperTarget(models.Model):
    """
    Specifies which model (via ContentType) to act upon
    and references optional custom finder/processor plugins.
    """
    id = models.UUIDField(primary_key=True,
                          default=uuid.uuid4,  # ✅ Auto-generate UUIDs
                          editable=False)

    case_mapper = models.ForeignKey(CaseMapper, on_delete=models.CASCADE, related_name="targets")

    # Which model to affect (dynamic)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)

    # Optional path to a function that will find existing records
    # (e.g. 'myapp.plugins.some_plugin.find_records')
    finder_function_path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Dotted path to a plugin function/class that will find existing objects."
    )

    # Optional path to a function that will create/update/delete
    # (e.g. 'myapp.plugins.some_plugin.process_records')
    processor_function_path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Dotted path to a plugin function/class that will handle creation/updating/deletion."
    )
    post_processor_path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional function path to run after mapping is completed."
    )
    root_path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional JSON path to a list of objects (e.g. 'children') to map multiple records."
    )
    filter_function_path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional function to filter each item in a JSON list before mapping (must return True/False)"
    )
    parent_target = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="children",
        on_delete=models.CASCADE
    )

    active_ind = models.BooleanField(default=True, help_text="Whether this target is active.")

    # You could store more info if needed, e.g. an 'operation' field, or
    # even a JSON of custom parameters.

    def __str__(self):
        return f"MapperTarget for {self.case_mapper.name} -> {self.content_type} "

    def clean(self):
        for path in [
            ("finder_function_path", self.finder_function_path),
            ("processor_function_path", self.processor_function_path),
            ("post_processor_path", self.post_processor_path)
        ]:
            if path[1]:
                try:
                    module_path, func_name = path[1].rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    if not hasattr(module, func_name):
                        raise ValidationError({path[0]: f"Function '{func_name}' not found in module '{module_path}'"})
                except Exception as e:
                    raise ValidationError({path[0]: f"Invalid function path: {str(e)}"})

# (Optional) Example for storing "field rules" if you want a fully declarative approach
# that doesn't require a custom plugin for simpler scenarios.
class MapperFieldRule(models.Model):
    mapper_target = models.ForeignKey("MapperTarget", on_delete=models.CASCADE, related_name='field_rules')
    target_field = models.CharField(max_length=100)
    json_path = models.CharField(max_length=255, help_text="e.g. 'vacation.start_date'")
    transform_function_path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional function to transform the extracted value."
    )

    # ✅ NEW: Conditional logic
    condition_path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Optional: JSON path to evaluate (e.g. citizen.age)"
    )
    condition_value = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Value to compare against"
    )
    condition_operator = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        choices=[
            ("==", "Equal"),
            ("!=", "Not equal"),
            (">", "Greater than"),
            ("<", "Less than"),
            ("in", "In"),
            ("not_in", "Not in"),
        ]
    )
    condition_expression = models.TextField(null=True, blank=True)
    default_value = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Fallback value if the condition fails or path is missing."
    )
    source_lookup = models.ForeignKey(
        "lookup.Lookup", null=True, blank=True, on_delete=models.SET_NULL,
        related_name='source_lookup_rules',
        help_text="Parent Lookup category of source value, used to translate input values."
    )
    target_lookup = models.ForeignKey(
        "lookup.Lookup", null=True, blank=True, on_delete=models.SET_NULL,
        related_name='target_lookup_rules',
        help_text="Parent Lookup category from which the final value should be fetched."
    )

    def __str__(self):
        return f"{self.mapper_target} - {self.target_field} <- {self.json_path}"

    def clean(self):
        if self.transform_function_path:
            try:
                module_path, func_name = self.transform_function_path.rsplit(".", 1)
                module = importlib.import_module(module_path)
                if not hasattr(module, func_name):
                    raise ValidationError({
                        "transform_function_path": f"Function '{func_name}' not found in module '{module_path}'"
                    })
            except Exception as e:
                raise ValidationError({
                    "transform_function_path": f"Invalid transform function path: {str(e)}"
                })

    def save(self, *args, **kwargs):
        from case.models import MapperFieldRuleLog
        user = kwargs.pop('user', None)

        if self.pk:  # If existing, compare for changes
            old_instance = MapperFieldRule.objects.get(pk=self.pk)
            old_data = {
                'target_field': old_instance.target_field,
                'json_path': old_instance.json_path,
                'default_value': old_instance.default_value,
                'transform_function_path': old_instance.transform_function_path,
                'condition_path': old_instance.condition_path,
                'condition_operator': old_instance.condition_operator,
                'condition_value': old_instance.condition_value,
            }
        else:
            old_data = {}

        super().save(*args, **kwargs)

        new_data = {
            'target_field': self.target_field,
            'json_path': self.json_path,
            'default_value': self.default_value,
            'transform_function_path': self.transform_function_path,
            'condition_path': self.condition_path,
            'condition_operator': self.condition_operator,
            'condition_value': self.condition_value,
        }

        if old_data != new_data:
            MapperFieldRuleLog.objects.create(
                rule=self,
                user=user,
                old_data=old_data,
                new_data=new_data,
            )

class MapperFieldRuleLog(models.Model):
    rule = models.ForeignKey('MapperFieldRule', on_delete=models.CASCADE, related_name='change_logs')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    changed_at = models.DateTimeField(auto_now_add=True)

    # Snapshot of old and new values
    old_data = models.JSONField()
    new_data = models.JSONField()

    def __str__(self):
        return f"ChangeLog for Rule {self.rule_id} at {self.changed_at}"

class MapperExecutionLog(models.Model):
    case = models.ForeignKey("Case", on_delete=models.CASCADE, related_name="mapper_logs")
    mapper_target = models.ForeignKey("MapperTarget", on_delete=models.SET_NULL, null=True)
    executed_at = models.DateTimeField(default=timezone.now)
    success = models.BooleanField(default=False)
    result_data = models.JSONField(default=dict)  # store full trace: parent/child mappings
    error_trace = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-executed_at']

    def __str__(self):
        return f"ExecutionLog: Case {self.case_id} → Target {self.mapper_target_id}"

# Add this new model

class MapperFieldCondition(models.Model):
    rule = models.ForeignKey("MapperFieldRule", related_name="field_conditions", on_delete=models.CASCADE)
    path = models.CharField(max_length=255, help_text="JSON path in the case data or context")
    operator = models.CharField(max_length=20, choices=[
        ('==', 'Equals'),
        ('!=', 'Not Equals'),
        ('>', 'Greater Than'),
        ('<', 'Less Than'),
        ('in', 'Contains'),
        ('not_in', 'Does Not Contain'),
    ])
    value = models.CharField(max_length=255, help_text="Expected value to compare against")
    logic_type = models.CharField(max_length=3, choices=[('AND', 'AND'), ('OR', 'OR')], default='AND')
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class MapperFieldRuleCondition(models.Model):
    """
    A reusable condition rule to be attached to a MapperFieldRule.
    Can be expression-based or path/operator-based.
    """
    field_rule = models.ForeignKey("MapperFieldRule", on_delete=models.CASCADE, related_name="rule_conditions")
    group = models.CharField(max_length=50, default="default", help_text="Group name to combine logic (e.g. AND group)")

    # Condition expression
    condition_expression = models.TextField(null=True, blank=True)

    # Fallback legacy condition
    condition_path = models.CharField(max_length=255, null=True, blank=True)
    condition_operator = models.CharField(
        max_length=20,
        choices=[
            ("==", "Equal"),
            ("!=", "Not equal"),
            (">", "Greater than"),
            ("<", "Less than"),
            ("in", "Contains"),
            ("not_in", "Does not contain"),
        ],
        null=True, blank=True
    )
    condition_value = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self):
        return f"Condition ({self.group}) on rule {self.field_rule_id}"
