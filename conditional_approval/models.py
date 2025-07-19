from django.db import models
from django.db.models import JSONField
from django_utils.choices import Choices, Choice
from django.utils.translation import gettext_lazy as _


class Action(models.Model):
    name = models.CharField(max_length=50, null=True, blank=True)
    name_ara = models.CharField(max_length=50, null=True, blank=True)
    groups = models.ManyToManyField(to="auth.Group", blank=True)
    services = models.ManyToManyField(
        to="lookup.Lookup",
        blank=True,
        related_name="case_services",
        limit_choices_to={"parent_lookup__name": "Service"},
        verbose_name=_("Services"),
    )
    notes_mandatory = models.BooleanField(
        default=False,
        help_text=_("If true, a note is required when this action is taken.")
    )
    code = models.CharField(max_length=20, null=True, blank=True)
    active_ind = models.BooleanField(default=True, null=True, blank=True)

    def __str__(self):
        return self.name


class ApprovalStep(models.Model):

    class STEP_TYPE(Choices):
        AUTO = Choice(1, _('Auto'))
        ACTION_BASED = Choice(2, _('Action Based'))

    # step_name = models.CharField(verbose_name='STEP NAME TILE', max_length=100)

    service_type = models.ForeignKey(
        to="lookup.Lookup",
        related_name='approval_step_case_type',
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        limit_choices_to={"parent_lookup__name": "Service"},
        verbose_name=_("Service Type")
    )
    seq = models.IntegerField(null=True, blank=True)
    step_type = models.IntegerField(
        'Step Type', choices=STEP_TYPE.choices,
        null=True, blank=True, default=STEP_TYPE.ACTION_BASED)
    status = models.ForeignKey(
        to="lookup.Lookup",
        related_name="approval_step_status",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        limit_choices_to={"parent_lookup__name": "Case Status"},
        verbose_name=_("Case Status")
    )
    group = models.ForeignKey(
        to="auth.Group", related_name="approval_step_current_group",
        null=True, blank=True, on_delete=models.SET_NULL)

    required_approvals = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("Number of approvals required for parallel approval.")
    )
    priority_approver_groups = models.ManyToManyField(
        to="auth.Group", blank=True,
        related_name="priority_approvers",
        help_text=_("Groups whose members can approve the case independently.")
    )
    active_ind = models.BooleanField(
        verbose_name='ACTIVE', null=True, blank=True, default=True)

    def __str__(self):
        try:
            return self.service_type.name + ' | ' + self.status.name + ' | '
        except AttributeError:
            return "%s object (%s)" % (self.__class__.__name__, self.pk)


class ParallelApprovalGroup(models.Model):
    approval_step = models.ForeignKey(
        ApprovalStep, on_delete=models.CASCADE,
        related_name='parallel_approval_groups',
        help_text=_("The approval step this parallel approval group is associated with.")
    )
    group = models.ForeignKey(
        to="auth.Group", on_delete=models.CASCADE,
        help_text=_("Group that can provide approval in this parallel approval step.")
    )

    def __str__(self):
        return f"{self.approval_step} - {self.group}"
    # def execute_action(self, case):
    #     if self.conditional_ind and not check_conditions(case, self):
    #         return "Conditions not met"


class ActionStep(models.Model):
    approval_step = models.ForeignKey(
        ApprovalStep, related_name='actions', on_delete=models.CASCADE)
    action = (models.ForeignKey
              (verbose_name='ACTION', to="conditional_approval.Action",
               related_name='approval_step_action',
               blank=True, null=True, on_delete=models.CASCADE))
    to_status = models.ForeignKey(
        to="lookup.Lookup",
        related_name="action_step_status",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        limit_choices_to={"parent_lookup__name": "Case Status"},
        verbose_name=_("To Status")
    )
    sub_status = models.ForeignKey(
        to="lookup.Lookup",
        related_name="action_step_sub_status",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        limit_choices_to={"parent_lookup__name": "Case Sub Status"},
        verbose_name=_("Sub Status")
    )
    active_ind = models.BooleanField(
        verbose_name='ACTIVE', null=True, blank=True, default=True)


class ApprovalStepCondition(models.Model):
    class APPROVAL_STEP_CONDITIONAL_TYPE(models.IntegerChoices):
        CONDITION = 1, _('Condition')
        AUTO_ACTION = 2, _('Automatic Action')

    approval_step = models.ForeignKey(ApprovalStep, on_delete=models.CASCADE)
    type = models.IntegerField(
        'Type',
        choices=APPROVAL_STEP_CONDITIONAL_TYPE.choices,
        null=True,
        blank=True,
        default=APPROVAL_STEP_CONDITIONAL_TYPE.CONDITION
    )
    condition_logic = models.JSONField(
        verbose_name=_("Condition Logic"),
        blank=True,
        null=True,
        help_text=_("Define conditions to evaluate in the format: "
                    "[{'field': 'field_name', 'operation': '=', 'value': 'some_value'}]")
    )
    to_status = models.ForeignKey(
        to="lookup.Lookup",
        related_name="approval_step_condition_status",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        limit_choices_to={"parent_lookup__name": "Case Status"},
        verbose_name=_("To Status")
    )
    sub_status = models.ForeignKey(
        to="lookup.Lookup",
        related_name="approval_step_condition_sub_status",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        limit_choices_to={"parent_lookup__name": "Case Sub Status"},
        verbose_name=_("Sub Status")
    )
    active_ind = models.BooleanField(
        verbose_name='ACTIVE', null=True, blank=True, default=True)


class APICallCondition(models.Model):

    approval_step = models.ForeignKey(
        to="conditional_approval.ApprovalStep", on_delete=models.CASCADE)
    case_expression = JSONField(null=True, blank=True, default=dict)
    case_field = models.CharField(
        max_length=100)  # Name of the field in the Case model
    expected_value = models.CharField(max_length=100)  # The value to match
    operator = models.CharField(
        max_length=10, choices=[('equals', 'Equals'), ('not_equals', 'Not Equals')])

    def __str__(self):
        return (f"{self.approval_step} - "
                f"{self.case_expression} {self.operator} {self.expected_value}")
