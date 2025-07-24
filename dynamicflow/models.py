from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
# Create your models here.
import re
from django.core.exceptions import ValidationError
class Workflow(models.Model):
    """Container model for workflow definitions"""
    name = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    service = models.ForeignKey(
        to='lookup.Lookup',
        limit_choices_to={'parent_lookup__name': 'Service'},
        related_name='workflows',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    service_code = models.CharField(max_length=50, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_draft = models.BooleanField(default=False)
    version = models.IntegerField(default=1)

    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    canvas_state = models.JSONField(default=dict, blank=True)  # Store zoom, pan, etc.

    # Tracking
    created_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_workflows'
    )
    updated_by = models.ForeignKey(
        'authentication.CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        related_name='updated_workflows'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = [('service', 'name', 'version')]

    def __str__(self):
        return f"{self.name} v{self.version}"

    def clone_as_new_version(self):
        """Create a new version of this workflow"""
        new_version = self.version + 1
        new_workflow = Workflow.objects.create(
            name=self.name,
            description=self.description,
            service=self.service,
            service_code=self.service_code,
            version=new_version,
            is_draft=True,
            metadata=self.metadata,
            canvas_state=self.canvas_state,
            created_by=self.updated_by
        )
        return new_workflow


class FieldType(models.Model):
    name = models.CharField(max_length=50, null=True, blank=True)
    name_ara = models.CharField(max_length=50, null=True, blank=True)
    code = models.CharField(max_length=20, null=True, blank=True)
    active_ind = models.BooleanField(default=True, null=True, blank=True)

    def __str__(self):
        return self.name


class Page(models.Model):
    class Meta:
        verbose_name = _('Page')
        ordering = ('sequence_number__code',)

    service = models.ForeignKey(
        to='lookup.Lookup',
        limit_choices_to={'parent_lookup__name': 'Service'},
        related_name='page_service', blank=True, null=True,
        on_delete=models.CASCADE)
    sequence_number = models.ForeignKey(
        to='lookup.Lookup',
        limit_choices_to={'parent_lookup__name': 'Flow Step'},
        related_name='seq_number', blank=True, null=True,
        on_delete=models.CASCADE)
    applicant_type = models.ForeignKey(
        to='lookup.Lookup',
        limit_choices_to={
            'parent_lookup__name': 'Service Applicant Type'},
        related_name='page_service_applicant_type',
        blank=True, null=True,
        on_delete=models.CASCADE)
    workflow = models.ForeignKey(
        'Workflow',
        on_delete=models.CASCADE,
        related_name='pages',
        null=True,  # Null for backward compatibility
        blank=True
    )

    name = models.CharField(max_length=50, null=True, blank=True)
    name_ara = models.CharField(max_length=50, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    description_ara = models.TextField(null=True, blank=True)
    is_review_page = models.BooleanField(default=False)
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
    is_expanded = models.BooleanField(default=False)
    active_ind = models.BooleanField(default=True, null=True, blank=True)

    def __str__(self):
        return f"{str(self.service.name)} | {self.sequence_number} | {self.name}"

    def get_json(self):
        result = {
            'service': self.service.name,
        }
        return result


class Category(models.Model):
    name = models.CharField(max_length=50, null=True, blank=True)
    name_ara = models.CharField(max_length=50, null=True, blank=True)
    page = models.ManyToManyField('Page', blank=True)
    is_repeatable = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    code = models.CharField(max_length=20, null=True, blank=True)
    workflow = models.ForeignKey(
        'Workflow',
        on_delete=models.CASCADE,
        related_name='categories',
        null=True,
        blank=True
    )
    relative_position_x = models.FloatField(default=0)
    relative_position_y = models.FloatField(default=0)
    active_ind = models.BooleanField(default=True, null=True, blank=True)

    def __str__(self):
        return self.name


class Field(models.Model):
    _parent_field = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        related_name='sub_fields',
        null=True, blank=True,
        help_text=_("The parent field for hierarchical structuring. Used for nested fields.")
    )
    _field_name = models.CharField(
        'Field Name',
        max_length=50, null=True, blank=True,
        help_text=_("The internal name of the field.")
    )
    service = models.ManyToManyField(
        to='lookup.Lookup',
        limit_choices_to={'parent_lookup__name': 'Service'},
        related_name='service_field', blank=True,
        help_text=_("The service(s) this field belongs to.")
    )
    _lookup = models.ForeignKey(
        'lookup.Lookup',
        null=True, blank=True,
        limit_choices_to={'is_category': True},
        on_delete=models.SET_NULL,
        related_name='field_lookups',
        help_text=_("The lookup associated with this field for predefined choices.")
    )
    _sequence = models.IntegerField(
        null=True, blank=True,
        help_text=_("The sequence number to determine the field's display order.")
    )
    _category = models.ManyToManyField(
        'Category', blank=True,
        help_text=_("The categories this field belongs to.")
    )
    _field_display_name = models.CharField(
        'Field Display Name',
        max_length=100, null=True, blank=True,
        help_text=_("The display name of the field in English.")
    )
    _field_display_name_ara = models.CharField(
        'Field Display Name Ara',
        max_length=100, null=True, blank=True,
        help_text=_("The display name of the field in Arabic.")
    )
    _field_type = models.ForeignKey(
        'FieldType',
        max_length=50, null=True, blank=True,
        on_delete=models.CASCADE,
        help_text=_("The type of the field (e.g., text, number, date).")
    )

    # Text Validations
    _max_length = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("The maximum allowed length for text fields.")
    )
    _min_length = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("The minimum required length for text fields.")
    )
    _regex_pattern = models.CharField(
        max_length=255, null=True, blank=True,
        help_text=_("A regex pattern to enforce specific formats for text fields.")
    )
    _allowed_characters = models.CharField(
        max_length=255, null=True, blank=True,
        help_text=_("Allowed characters for text fields (e.g., alphanumeric only).")
    )
    _forbidden_words = models.TextField(
        blank=True, null=True,
        help_text=_("A list of words that are not allowed in text fields.")
    )

    # Number Validations
    _value_greater_than = models.FloatField(
        null=True, blank=True,
        help_text=_("The minimum allowed value for numeric fields.")
    )
    _value_less_than = models.FloatField(
        null=True, blank=True,
        help_text=_("The maximum allowed value for numeric fields.")
    )
    _integer_only = models.BooleanField(
        default=False, null=True, blank=True,
        help_text=_("Restrict the field to integer values only.")
    )
    _positive_only = models.BooleanField(
        default=False, null=True, blank=True,
        help_text=_("Restrict the field to positive values only.")
    )

    # Date Validations
    _date_greater_than = models.DateField(
        null=True, blank=True,
        help_text=_("The earliest allowed date for date fields.")
    )
    _date_less_than = models.DateField(
        null=True, blank=True,
        help_text=_("The latest allowed date for date fields.")
    )
    _future_only = models.BooleanField(
        default=False, null=True, blank=True,
        help_text=_("Restrict the field to future dates only.")
    )
    _past_only = models.BooleanField(
        default=False, null=True, blank=True,
        help_text=_("Restrict the field to past dates only.")
    )

    # Boolean Default
    _default_boolean = models.BooleanField(
        default=False, null=True, blank=True,
        help_text=_("The default value for boolean fields.")
    )

    # File and Image Validations
    _file_types = models.CharField(
        max_length=255, null=True, blank=True,
        help_text=_("Allowed file types/extensions (e.g., .pdf, .docx).")
    )
    _max_file_size = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("The maximum allowed file size in bytes.")
    )
    _image_max_width = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("The maximum allowed image width in pixels.")
    )
    _image_max_height = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("The maximum allowed image height in pixels.")
    )

    # Lookup and Choice Validations
    allowed_lookups = models.ManyToManyField(
        'lookup.Lookup',
        blank=True,
        related_name='allowed_field_lookups',
        help_text=_("Allowed lookup values for choice fields.")
    )
    _max_selections = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("The maximum number of selections allowed for multi-choice fields.")
    )
    _min_selections = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("The minimum number of selections required for multi-choice fields.")
    )

    # Advanced Field Validations
    _precision = models.PositiveIntegerField(
        null=True, blank=True,
        help_text=_("The precision for decimal fields (number of decimal places).")
    )
    _unique = models.BooleanField(
        default=False, null=True, blank=True,
        help_text=_("Ensure the field value is unique.")
    )
    _default_value = models.CharField(
        max_length=255, null=True, blank=True,
        help_text=_("The default value for the field.")
    )

    # Geographical and Special Validations
    _coordinates_format = models.BooleanField(
        default=False, null=True, blank=True,
        help_text=_("Validate the field as geographical coordinates (latitude and longitude).")
    )
    _uuid_format = models.BooleanField(
        default=False, null=True, blank=True,
        help_text=_("Ensure the field value is a valid UUID.")
    )

    # Visibility Control
    _is_hidden = models.BooleanField(
        default=False, null=True, blank=True,
        help_text=_("Hide the field from display.")
    )
    _is_disabled = models.BooleanField(
        default=False, null=True, blank=True,
        help_text=_("Disable the field to prevent modifications.")
    )
    _mandatory = models.BooleanField(
        default=False, null=True, blank=True,
        help_text=_("Mark the field as mandatory.")
    )
    workflow = models.ForeignKey(
        'Workflow',
        on_delete=models.CASCADE,
        related_name='fields',
        null=True,
        blank=True
    )
    relative_position_x = models.FloatField(default=0)
    relative_position_y = models.FloatField(default=0)
    active_ind = models.BooleanField(
        default=True, null=True, blank=True,
        help_text=_("Indicate if the field is active.")
    )

    def __str__(self):
        return self._field_name

    def get_integrations_for_event(self, event):
        """
        Get all active integrations for a specific event
        """
        return self.field_integrations.filter(
            trigger_event=event,
            active=True
        ).order_by('order')

    def clean(self):
        super().clean()
        # Skip validations if the instance
        # is not saved yet (doesn't have a primary key)
        if not self.pk:
            return

        # Prevent a field from being its own parent
        if self._parent_field and self._parent_field == self:
            raise ValidationError(
                {'_parent_field': "A field cannot be its own parent."})

        # Prevent circular references by checking
        # if this field is already in its ancestor chain
        if (self._parent_field
                and self._parent_field.get_ancestor_ids().count(self.id)):
            raise ValidationError(
                {'_parent_field': "Circular relationships are not allowed."})

    def get_ancestor_ids(self):
        ancestors = []
        parent = self._parent_field
        while parent:
            ancestors.append(parent.id)
            parent = parent._parent_field
        return ancestors

    def get_descendant_ids(self):
        """
        Recursively fetch all descendant field IDs for the current field.
        """
        descendant_ids = set()
        for subfield in self.sub_fields.all():
            descendant_ids.add(subfield.id)
            descendant_ids.update(subfield.get_descendant_ids())
        return descendant_ids

    def serialize_sub_fields(self):
        """
        Serialize the sub-fields by extracting the names of the related fields.
        """
        return [sub_field._field_name for sub_field in self.sub_fields.all()]


class Condition(models.Model):
    target_field = models.ForeignKey(
        Field,
        on_delete=models.CASCADE,
        related_name='conditions',
        help_text="The field to show when the condition is true."
    )
    active_ind = models.BooleanField(
        default=True,
        help_text="Indicates whether this condition is active."
    )
    condition_logic = models.JSONField(
        help_text=(
            "Define the logic for this condition as a JSON array of operations. "
            "Example: [{'field': 'salary', 'operation': '+', 'value': 10000}]"
        )
    )  # e.g., [{"field": "salary", "operation": "+", "value": 10000}, ...]
    workflow = models.ForeignKey(
        'Workflow',
        on_delete=models.CASCADE,
        related_name='conditions',
        null=True,
        blank=True
    )
    position_x = models.FloatField(default=0)
    position_y = models.FloatField(default=0)
    condition_type = models.CharField(
        max_length=20,
        choices=[
            ('visibility', 'Visibility Condition'),
            ('calculation', 'Field Calculation'),
        ],
        default='visibility',
        help_text="Whether this condition controls visibility or calculates a value"
    )

def calculate_value(self, field_data):
    """
    Calculate the actual value for calculation-type conditions
    Returns the calculated value instead of boolean
    """
    try:
        from datetime import datetime, date

        for condition in self.condition_logic:
            field_name = condition['field']
            operation = condition['operation']
            value = condition.get('value', 0)

            field_value = field_data.get(field_name, 0)

            # Handle field references
            if isinstance(value, dict) and 'field' in value:
                value = field_data.get(value['field'], 0)

            # Convert to float for calculations (except for dates and conditionals)
            if operation not in ['age_conditional', 'if', 'if_equals']:
                try:
                    field_value = float(field_value)
                    if not isinstance(value, (list, dict)):
                        value = float(value)
                except (ValueError, TypeError):
                    pass

            # Perform calculations
            if operation == "+":
                return field_value + value
            elif operation == "-":
                return field_value - value
            elif operation == "*":
                return field_value * value
            elif operation == "/":
                return field_value / value if value != 0 else 0
            elif operation == "**":
                return field_value ** value
            elif operation == "sum":
                total = 0
                for field in value:
                    if field.startswith('-'):
                        total -= float(field_data.get(field[1:], 0))
                    else:
                        total += float(field_data.get(field, 0))
                return total
            # For direct value copy
            elif operation == "=" or operation == "copy":
                return field_value

            # NEW: Age-based conditional
            elif operation == "age_conditional":
                if field_value:
                    # Calculate age from DOB
                    if isinstance(field_value, str):
                        dob = datetime.strptime(field_value, "%Y-%m-%d").date()
                    else:
                        dob = field_value

                    today = date.today()
                    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

                    age_threshold = condition.get('age_threshold', 18)
                    if age < age_threshold:
                        under_field = condition.get('under_age_field')
                        return field_data.get(under_field, 0)
                    else:
                        over_field = condition.get('over_age_field')
                        return field_data.get(over_field, 0)
                return 0

            # NEW: Simple if-equals conditional
            elif operation == "if_equals":
                check_value = condition.get('check_value')
                then_value = condition.get('then_value', 0)
                else_value = condition.get('else_value', field_value)

                # Handle field references in then/else values
                if isinstance(then_value, dict) and 'field' in then_value:
                    then_value = field_data.get(then_value['field'], 0)
                if isinstance(else_value, dict) and 'field' in else_value:
                    else_value = field_data.get(else_value['field'], 0)

                if field_value == check_value:
                    return then_value
                else:
                    return else_value

            # NEW: General if conditional with any operator
            elif operation == "if":
                condition_op = condition.get('condition_operator', '=')
                check_value = condition.get('check_value')
                then_value = condition.get('then_value', 0)
                else_value = condition.get('else_value', field_value)

                # Handle field references
                if isinstance(then_value, dict) and 'field' in then_value:
                    then_value = field_data.get(then_value['field'], 0)
                if isinstance(else_value, dict) and 'field' in else_value:
                    else_value = field_data.get(else_value['field'], 0)

                # Evaluate condition
                if self._evaluate_single_condition(field_value, condition_op, check_value):
                    return then_value
                else:
                    return else_value

    except Exception as e:
        raise ValidationError(f"Error calculating value: {e}")

    return None

    def evaluate_condition(self, field_data):
        """
        Evaluates the condition based on provided field data.
        field_data: Dictionary of field names and their corresponding values.
        """
        try:
            result = True

            # Evaluate the dynamic condition logic stored in the condition_logic field
            for condition in self.condition_logic:
                field_name = condition['field']
                operation = condition['operation']
                value = condition['value']

                field_value = field_data.get(field_name, 0)

                # Perform the dynamic operation (addition, subtraction, comparison, etc.)
                if operation == "+":
                    result = result and (field_value + value)
                elif operation == "-":
                    result = result and (field_value - value)
                elif operation == "*":
                    result = result and (field_value * value)
                elif operation == "/":
                    result = result and (field_value / value if value != 0 else 0)
                elif operation == "**":
                    result = result and (field_value ** value)
                elif operation == "=":
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
                elif operation == "in":
                    result = result and (field_value in value)
                elif operation == "not in":
                    result = result and (field_value not in value)
                elif operation == "startswith":
                    result = result and str(field_value).startswith(str(value))
                elif operation == "endswith":
                    result = result and str(field_value).endswith(str(value))
                elif operation == "contains":
                    result = result and (str(value) in str(field_value))
                elif operation == "matches":
                    result = result and bool(re.match(value, str(field_value)))

                # Additional logical operators
                elif operation == "and":
                    result = result and value  # value should be a boolean or another condition check
                elif operation == "or":
                    result = result or value
                elif operation == "not":
                    result = not value  # value should be a boolean or another condition check
                elif operation == "sum":
                    total = 0
                    for item in value:  # Assuming value is a list of fields to sum
                        total += field_data.get(item, 0)
                    result = result and (field_value == total)
            # Additional checks
            if 'additional_checks' in self.condition_logic:
                for check in self.condition_logic['additional_checks']:
                    check_field = check['field']
                    check_value = check['value']
                    check_operator = check.get('operator', "=")

                    check_field_value = field_data.get(check_field, "")
                    if check_operator == "=":
                        result = result and (check_field_value == check_value)
                    elif check_operator == "startswith":
                        result = result and check_field_value.startswith(check_value)
                    elif check_operator == "endswith":
                        result = result and check_field_value.endswith(check_value)
                    elif check_operator == "contains":
                        result = result and (check_value in check_field_value)
                    elif check_operator == "matches":
                        result = result and bool(re.match(check_value, check_field_value))
                    elif check_operator == "before":
                        result = result and (check_field_value < check_value)
                    elif check_operator == "after":
                        result = result and (check_field_value > check_value)

            return result
        except Exception as e:
            raise ValidationError(f"Error evaluating condition: {e}")

    def __str__(self):
        return self.target_field._field_name

class WorkflowConnection(models.Model):
    """Store connections between workflow elements"""
    workflow = models.ForeignKey(
        'Workflow',
        on_delete=models.CASCADE,
        related_name='connections'
    )
    source_type = models.CharField(max_length=20)  # 'page', 'category', 'field', 'condition'
    source_id = models.IntegerField()
    target_type = models.CharField(max_length=20)
    target_id = models.IntegerField()
    connection_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [('workflow', 'source_type', 'source_id', 'target_type', 'target_id')]