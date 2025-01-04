from django.core.exceptions import ValidationError
from django.db import models



class DynamicModel(models.Model):
    """
    Represents a dynamic model that can have dynamic fields.
    """
    name = models.CharField(max_length=255, unique=True)  # Table name
    verbose_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

    def get_dynamic_model_class(self):
        """
        Returns the dynamically created model class.
        """
        from dynamic_models.utils.utils import create_dynamic_model

        return create_dynamic_model(self)

class DynamicField(models.Model):
    """
    Represents a field for a dynamic model.
    """
    FIELD_TYPES = [
        ('CharField', 'CharField'),
        ('IntegerField', 'IntegerField'),
        ('BooleanField', 'BooleanField'),
        ('DateTimeField', 'DateTimeField'),
        ('TextField', 'TextField'),
        ('FloatField', 'FloatField'),
        ('DecimalField', 'DecimalField'),
        ('DateField', 'DateField'),
        ('TimeField', 'TimeField'),
        ('EmailField', 'EmailField'),
        ('URLField', 'URLField'),
        ('ForeignKey', 'ForeignKey'),
        ('OneToOneField', 'OneToOneField'),
        ('ManyToManyField', 'ManyToManyField'),
    ]
    ON_DELETE_OPTIONS = [
        ('CASCADE', 'CASCADE'),
        ('PROTECT', 'PROTECT'),
        ('SET_NULL', 'SET_NULL'),
        ('SET_DEFAULT', 'SET_DEFAULT'),
        ('DO_NOTHING', 'DO_NOTHING'),
    ]

    model = models.ForeignKey(DynamicModel, on_delete=models.CASCADE, related_name='fields')
    name = models.CharField(max_length=255)  # Field name
    field_type = models.CharField(max_length=50, choices=FIELD_TYPES)
    max_length = models.IntegerField(blank=True, null=True)  # Applicable for CharField/TextField
    null = models.BooleanField(default=False)
    blank = models.BooleanField(default=False)
    default_value = models.CharField(max_length=255, blank=True, null=True)  # Default value as a string
    unique = models.BooleanField(default=False)  # For unique constraints
    regex_pattern = models.CharField(max_length=255, blank=True, null=True)  # For CharField validations
    min_value = models.FloatField(blank=True, null=True)  # For IntegerField/FloatField
    max_value = models.FloatField(blank=True, null=True)  # For IntegerField/FloatField

    # Specific to DecimalField
    max_digits = models.IntegerField(blank=True, null=True)
    decimal_places = models.IntegerField(blank=True, null=True)

    # For relationships
    related_model = models.CharField(max_length=255, blank=True, null=True)  # Target model for relationships
    on_delete = models.CharField(
        max_length=20,
        choices=ON_DELETE_OPTIONS,
        blank=True,
        null=True,
        default='CASCADE',  # Default to CASCADE
        help_text="Behavior when the related object is deleted.",
    )
    previous_name = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Set this if the field has been renamed. It allows schema migration to handle renaming."
    )
    def __str__(self):
        return f"{self.name} ({self.field_type})"

    def clean(self):
        """
        Validate field attributes based on field type.
        """
        if self.field_type == 'DecimalField':
            if self.max_digits is None or self.decimal_places is None:
                raise ValidationError(
                    "DecimalField must define both 'max_digits' and 'decimal_places'."
                )

        if self.field_type in ['ForeignKey', 'OneToOneField']:
            if not self.related_model:
                raise ValidationError(f"{self.field_type} requires 'related_model' to be specified.")
        # Ensure this field belongs to a valid DynamicModel
        if not DynamicModel.objects.filter(id=self.model_id).exists():
            raise ValidationError(f"DynamicField '{self.name}' must be linked to a valid DynamicModel.")
        super().clean()