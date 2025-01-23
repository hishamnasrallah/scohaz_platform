from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.conf import settings
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

    # Optionally, you can add sub_status, etc. if you want finer scoping:
    # sub_status = models.CharField(max_length=100, null=True, blank=True, ...)

    def __str__(self):
        return f"{self.name} (type={self.case_type})"


class MapperTarget(models.Model):
    """
    Specifies which model (via ContentType) to act upon
    and references optional custom finder/processor plugins.
    """
    id = models.UUIDField(primary_key=True, editable=False)
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

    # You could store more info if needed, e.g. an 'operation' field, or
    # even a JSON of custom parameters.

    def __str__(self):
        return f"MapperTarget for {self.case_mapper.name} -> {self.content_type} "


# (Optional) Example for storing "field rules" if you want a fully declarative approach
# that doesn't require a custom plugin for simpler scenarios.
class MapperFieldRule(models.Model):
    """
    If you want to let admin define simple JSON path -> model field mappings
    for scenarios that don't need complex logic.
    """
    mapper_target = models.ForeignKey(MapperTarget, on_delete=models.CASCADE, related_name='field_rules')

    # The field name on the model (like 'start_date', 'reason', etc.)
    target_field = models.CharField(max_length=100)

    # A JSON path or dotted path within case_data
    json_path = models.CharField(max_length=255, help_text="e.g. 'vacation.start_date'")

    # Optional transformation function path
    transform_function_path = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Dotted path to a function that can transform extracted data before assigning."
    )

    def __str__(self):
        return f"{self.mapper_target} - {self.target_field} <- {self.json_path}"