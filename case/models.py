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
