from django.core.exceptions import ValidationError
from django.db import models
from django.core.validators import RegexValidator
# Use the built-in JSONField that works on all DBs in Django 3.1+
try:
    from django.db.models import JSONField
except ImportError:
    # If someone is on older Django, they'd have to adapt. For modern Django 3.1+, this code is fine.
    from django.contrib.postgres.fields import JSONField

class ApplicationDefinition(models.Model):
    """
    Stores one entire dynamic application definition, including flags for the create_app command.
    """
    app_name = models.CharField(
        max_length=100,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z_]\w*$',
                message="App name must be a valid Python identifier."
            )
        ]
    )
    overwrite = models.BooleanField(default=False)
    skip_admin = models.BooleanField(default=False)
    skip_tests = models.BooleanField(default=False)
    skip_urls = models.BooleanField(default=False)
    erd_json = models.JSONField(default=dict, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.app_name

    def compile_schema(self):
        """
        Build a list of dicts describing each model. This matches what create_app expects.
        """
        schema = []
        # Use .select_related() or .prefetch_related() if needed
        for mdef in self.modeldefinition_set.all().order_by('id'):
            schema.append(mdef.compile_model_definition())
        return schema


class ModelDefinition(models.Model):
    """
    Each ModelDefinition represents a Django model. Supports advanced metadata.
    """
    application = models.ForeignKey(ApplicationDefinition, on_delete=models.CASCADE)
    model_name = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z_]\w*$',
                message="Model name must be a valid Python identifier."
            )
        ]
    )
    db_table = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional custom table name."
    )
    verbose_name = models.CharField(max_length=200, blank=True)
    verbose_name_plural = models.CharField(max_length=200, blank=True)
    ordering = models.CharField(
        max_length=200,
        blank=True,
        help_text="Comma-separated. Example: '-created_at,name'"
    )
    unique_together = JSONField(
        blank=True,
        null=True,
        help_text="List of lists. Example: [['field1','field2'], ['field3','field4']]."
    )
    indexes = JSONField(
        blank=True,
        null=True,
        help_text=(
            "List of indexes. Each item can be a list of field names "
            "or a dict with 'fields' and 'name' etc."
        )
    )
    constraints = JSONField(
        blank=True,
        null=True,
        help_text=(
            "List of constraints. Example: "
            "[{'check': 'price__gte=0', 'name': 'price_positive'}, "
            "{'unique': ['email','phone'], 'name': 'unique_email_phone'}]."
        )
    )

    def __str__(self):
        return f"{self.application.app_name}.{self.model_name}"

    def compile_model_definition(self):
        compiled_fields = []
        for fdef in self.fielddefinition_set.all().order_by('id'):
            compiled_fields.append(fdef.compile_field())

        compiled_relationships = []
        for rdef in self.relationshipdefinition_set.all().order_by('id'):
            compiled_relationships.append(rdef.compile_relationship())

        meta_data = {}
        if self.db_table.strip():
            meta_data["db_table"] = self.db_table
        if self.verbose_name.strip():
            meta_data["verbose_name"] = self.verbose_name
        if self.verbose_name_plural.strip():
            meta_data["verbose_name_plural"] = self.verbose_name_plural
        if self.ordering.strip():
            ordering_list = [x.strip() for x in self.ordering.split(',') if x.strip()]
            meta_data["ordering"] = ordering_list
        if self.unique_together:
            meta_data["unique_together"] = self.unique_together
        if self.indexes:
            meta_data["indexes"] = self.indexes
        if self.constraints:
            meta_data["constraints"] = self.constraints

        return {
            "name": self.model_name,
            "fields": compiled_fields,
            "relationships": compiled_relationships,
            "meta": meta_data
        }


class FieldDefinition(models.Model):
    """
    A single field (CharField, etc.) in the model, with optional choices.
    """

    FIELD_TYPE_CHOICES = [
        ("AutoField", "AutoField"),
        ("BigAutoField", "BigAutoField"),
        ("SmallAutoField", "SmallAutoField"),
        ("BooleanField", "BooleanField"),
        ("CharField", "CharField"),
        ("CommaSeparatedIntegerField", "CommaSeparatedIntegerField"),  # Deprecated in Django 3.1, consider using CharField with validation
        ("DateField", "DateField"),
        ("DateTimeField", "DateTimeField"),
        ("DecimalField", "DecimalField"),
        ("DurationField", "DurationField"),
        ("EmailField", "EmailField"),
        ("FilePathField", "FilePathField"),
        ("FloatField", "FloatField"),
        ("IntegerField", "IntegerField"),
        ("BigIntegerField", "BigIntegerField"),
        ("SmallIntegerField", "SmallIntegerField"),
        ("IPAddressField", "IPAddressField"),
        ("GenericIPAddressField", "GenericIPAddressField"),
        ("PositiveBigIntegerField", "PositiveBigIntegerField"),
        ("PositiveIntegerField", "PositiveIntegerField"),
        ("PositiveSmallIntegerField", "PositiveSmallIntegerField"),
        ("SlugField", "SlugField"),
        ("TextField", "TextField"),
        ("TimeField", "TimeField"),
        ("URLField", "URLField"),
        ("BinaryField", "BinaryField"),
        ("UUIDField", "UUIDField"),
        ("JSONField", "JSONField"),  # JSONField was added in Django 3.1 and is useful for storing JSON data
    ]


    model_definition = models.ForeignKey(ModelDefinition, on_delete=models.CASCADE)
    field_name = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z_]\w*$',
                message="Field name must be a valid Python identifier."
            )
        ]
    )
    field_type = models.CharField(max_length=50, choices=FIELD_TYPE_CHOICES)
    options = models.CharField(
        max_length=250,
        blank=True,
        help_text="""Comma-separated Django field options. Example: max_length=100,unique=True\n
        field_options_help = {
    "CharField": {
        "mandatory": {"max_length": "ex: max_length=5 (Maximum length of the string)"},
        "optional": {
            "blank": "ex: blank=True (Allow blank values in forms)",
            "null": "ex: null=True (Allow NULL values in the database)",
            "default": "ex: default='hello' (Default value for the field)",
            "unique": "ex: unique=True (Ensure unique values in the database)",
            "choices": "ex: choices=[('A', 'Option A'), ('B', 'Option B')] (Set predefined options)",
        },
    },
    "TextField": {
        "mandatory": {},
        "optional": {
            "blank": "ex: blank=True (Allow blank values in forms)",
            "null": "ex: null=True (Allow NULL values in the database)",
            "default": "ex: default='Description' (Default value for the field)",
        },
    },
    "IntegerField": {
        "mandatory": {},
        "optional": {
            "blank": "ex: blank=True (Allow blank values in forms)",
            "null": "ex: null=True (Allow NULL values in the database)",
            "default": "ex: default=1 (Default value for the field)",
        },
    },
    "DecimalField": {
        "mandatory": {
            "max_digits": "ex: max_digits=5 (Maximum total digits allowed)",
            "decimal_places": "ex: decimal_places=2 (Maximum decimal places)",
        },
        "optional": {
            "blank": "ex: blank=True (Allow blank values in forms)",
            "null": "ex: null=True (Allow NULL values in the database)",
            "default": "ex: default=0.0 (Default value for the field)",
        },
    },
    "DateField": {
        "mandatory": {},
        "optional": {
            "blank": "ex: blank=True (Allow blank values in forms)",
            "null": "ex: null=True (Allow NULL values in the database)",
            "default": "ex: default=datetime.date.today (Set a default date)",
            "auto_now": "ex: auto_now=True (Set the current date on save)",
            "auto_now_add": "ex: auto_now_add=True (Set the current date when created)",
        },
    },
    "ForeignKey": {
        "mandatory": {"on_delete": "ex: on_delete=models.CASCADE (Behavior on delete of related object)"},
        "optional": {
            "related_name": "ex: related_name='related_objects' (Reverse relation name)",
            "null": "ex: null=True (Allow NULL values in the database)",
            "blank": "ex: blank=True (Allow blank values in forms)",
            "to_field": "ex: to_field='field_name' (Use a specific field as the relationship key)",
        },
    },
    "ManyToManyField": {
        "mandatory": {},
        "optional": {
            "related_name": "ex: related_name='related_objects' (Reverse relation name)",
            "blank": "ex: blank=True (Allow blank values in forms)",
            "through": "ex: through='ModelName' (Custom intermediate model for the relationship)",
        },
    },
    "BooleanField": {
        "mandatory": {},
        "optional": {
            "default": "ex: default=True (Set a default value for the field)",
        },
    },
    "JSONField": {
        "mandatory": {},
        "optional": {
            "blank": "ex: blank=True (Allow blank values in forms)",
            "null": "ex: null=True (Allow NULL values in the database)",
            "default": "ex: default=dict (Set a default dictionary value)",
        },
    },
    "EmailField": {
        "mandatory": {},
        "optional": {
            "max_length": "ex: max_length=255 (Maximum length of the email address)",
            "blank": "ex: blank=True (Allow blank values in forms)",
            "null": "ex: null=True (Allow NULL values in the database)",
            "default": "ex: default='example@example.com' (Set a default email address)",
        },
    },
}

"""

    )
    has_choices = models.BooleanField(default=False)
    choices_json = JSONField(
        blank=True,
        null=True,
        help_text="List of [value,label] pairs. Example: [['draft','Draft'],['published','Published']]"
    )
    # Field options help dictionary
    def clean(self):
        """
        Custom validation to ensure mandatory options are present and valid for the specified field type.
        """
        # Field options help dictionary
        field_options_help = {
            "CharField": {
                "mandatory": ["max_length"],
                "optional": ["blank", "null", "default", "unique", "choices"],
            },
            "TextField": {
                "mandatory": [],
                "optional": ["blank", "null", "default"],
            },
            "IntegerField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "FloatField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "DecimalField": {
                "mandatory": ["max_digits", "decimal_places"],
                "optional": ["blank", "null", "default", "unique"],
            },
            "DateField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "auto_now", "auto_now_add"],
            },
            "DateTimeField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "auto_now", "auto_now_add"],
            },
            "BooleanField": {
                "mandatory": [],
                "optional": ["default"],
            },
            "JSONField": {
                "mandatory": [],
                "optional": ["blank", "null", "default"],
            },
            "EmailField": {
                "mandatory": [],
                "optional": ["max_length", "blank", "null", "default", "unique"],
            },
            "URLField": {
                "mandatory": [],
                "optional": ["max_length", "blank", "null", "default", "unique"],
            },
            "SlugField": {
                "mandatory": [],
                "optional": ["max_length", "blank", "null", "default", "unique", "allow_unicode"],
            },
            "PositiveIntegerField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "BigIntegerField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "PositiveSmallIntegerField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "SmallIntegerField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "ForeignKey": {
                "mandatory": ["on_delete"],
                "optional": [
                    "related_name",
                    "related_query_name",
                    "null",
                    "blank",
                    "to_field",
                    "limit_choices_to",
                    "db_constraint",
                ],
            },
            "OneToOneField": {
                "mandatory": ["on_delete"],
                "optional": [
                    "related_name",
                    "related_query_name",
                    "null",
                    "blank",
                    "to_field",
                    "db_constraint",
                ],
            },
            "ManyToManyField": {
                "mandatory": [],
                "optional": [
                    "related_name",
                    "related_query_name",
                    "blank",
                    "limit_choices_to",
                    "through",
                    "through_fields",
                    "db_constraint",
                ],
            },
            "FileField": {
                "mandatory": ["upload_to"],
                "optional": ["blank", "null", "default", "unique", "max_length"],
            },
            "ImageField": {
                "mandatory": ["upload_to"],
                "optional": ["blank", "null", "default", "unique", "max_length"],
            },
            "UUIDField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "DurationField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "TimeField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "auto_now", "auto_now_add"],
            },
            "GenericIPAddressField": {
                "mandatory": [],
                "optional": ["protocol", "unpack_ipv4", "blank", "null", "default", "unique"],
            },
        }

        # Validate field_type
        if self.field_type not in field_options_help:
            raise ValidationError(f"Invalid field type: {self.field_type}")

        # Parse options
        try:
            option_dict = {k.strip(): v.strip() for k, v in (opt.split("=") for opt in self.options.split(","))}
        except ValueError:
            raise ValidationError(f"Options must be valid key=value pairs. Example: max_length=100, unique=True")

        # Validate mandatory options
        mandatory_options = field_options_help[self.field_type]["mandatory"]
        for option in mandatory_options:
            if option not in option_dict:
                raise ValidationError(f"Mandatory option '{option}' is missing for field type '{self.field_type}'.")

            # Check for

            # Validate field_type
            if self.field_type not in field_options_help:
                raise ValidationError(f"Invalid field type: {self.field_type}")

            # Parse options
            try:
                option_dict = {k.strip(): v.strip() for k, v in (opt.split("=") for opt in self.options.split(","))}
            except ValueError:
                raise ValidationError(f"Options must be valid key=value pairs. Example: max_length=100, unique=True")

            # Validate mandatory options
            mandatory_options = field_options_help[self.field_type]["mandatory"]
            for option in mandatory_options:
                if option not in option_dict:
                    raise ValidationError(f"Mandatory option '{option}' is missing for field type '{self.field_type}'.")

            # Check for unknown options
            valid_options = mandatory_options + field_options_help[self.field_type]["optional"]
            for option in option_dict:
                if option not in valid_options:
                    raise ValidationError(f"Invalid option '{option}' for field type '{self.field_type}'.")

    def __str__(self):
        return f"{self.field_name} ({self.field_type})"

    def compile_field(self):
        data = {
            "name": self.field_name,
            "type": self.field_type,
            "options": self.options
        }
        if self.has_choices and self.choices_json:
            data["choices"] = self.choices_json
        return data


class RelationshipDefinition(models.Model):
    """
    A relationship (ForeignKey, OneToOneField, ManyToManyField).
    """
    RELATION_TYPE_CHOICES = [
        ("ForeignKey", "ForeignKey"),
        ("OneToOneField", "OneToOneField"),
        ("ManyToManyField", "ManyToManyField")
    ]

    model_definition = models.ForeignKey(ModelDefinition, on_delete=models.CASCADE)
    relation_name = models.CharField(
        max_length=100,
        validators=[
            RegexValidator(
                regex=r'^[A-Za-z_]\w*$',
                message="Relation name must be a valid Python identifier."
            )
        ]
    )
    relation_type = models.CharField(max_length=50, choices=RELATION_TYPE_CHOICES)
    related_model = models.CharField(max_length=200, help_text="Example: 'auth.User' or 'myapp.OtherModel'")
    options = models.CharField(
        max_length=250,
        blank=True,
        help_text="Comma-separated options. Example: on_delete=models.CASCADE,null=True,blank=True"
    )
    def clean(self):
        """
        Custom validation to ensure mandatory options are present and valid for the specified field type.
        """
        # Field options help dictionary
        field_options_help = {
            "CharField": {
                "mandatory": ["max_length"],
                "optional": ["blank", "null", "default", "unique", "choices"],
            },
            "TextField": {
                "mandatory": [],
                "optional": ["blank", "null", "default"],
            },
            "IntegerField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "FloatField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "DecimalField": {
                "mandatory": ["max_digits", "decimal_places"],
                "optional": ["blank", "null", "default", "unique"],
            },
            "DateField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "auto_now", "auto_now_add"],
            },
            "DateTimeField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "auto_now", "auto_now_add"],
            },
            "BooleanField": {
                "mandatory": [],
                "optional": ["default"],
            },
            "JSONField": {
                "mandatory": [],
                "optional": ["blank", "null", "default"],
            },
            "EmailField": {
                "mandatory": [],
                "optional": ["max_length", "blank", "null", "default", "unique"],
            },
            "URLField": {
                "mandatory": [],
                "optional": ["max_length", "blank", "null", "default", "unique"],
            },
            "SlugField": {
                "mandatory": [],
                "optional": ["max_length", "blank", "null", "default", "unique", "allow_unicode"],
            },
            "PositiveIntegerField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "BigIntegerField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "PositiveSmallIntegerField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "SmallIntegerField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "ForeignKey": {
                "mandatory": ["on_delete"],
                "optional": [
                    "related_name",
                    "related_query_name",
                    "null",
                    "blank",
                    "to_field",
                    "limit_choices_to",
                    "db_constraint",
                ],
            },
            "OneToOneField": {
                "mandatory": ["on_delete"],
                "optional": [
                    "related_name",
                    "related_query_name",
                    "null",
                    "blank",
                    "to_field",
                    "db_constraint",
                ],
            },
            "ManyToManyField": {
                "mandatory": [],
                "optional": [
                    "related_name",
                    "related_query_name",
                    "blank",
                    "limit_choices_to",
                    "through",
                    "through_fields",
                    "db_constraint",
                ],
            },
            "FileField": {
                "mandatory": ["upload_to"],
                "optional": ["blank", "null", "default", "unique", "max_length"],
            },
            "ImageField": {
                "mandatory": ["upload_to"],
                "optional": ["blank", "null", "default", "unique", "max_length"],
            },
            "UUIDField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "DurationField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "unique"],
            },
            "TimeField": {
                "mandatory": [],
                "optional": ["blank", "null", "default", "auto_now", "auto_now_add"],
            },
            "GenericIPAddressField": {
                "mandatory": [],
                "optional": ["protocol", "unpack_ipv4", "blank", "null", "default", "unique"],
            },
        }

        # Validate relation_type
        if self.relation_type not in field_options_help:
            raise ValidationError(f"Invalid field type: {self.relation_type}")

        # Parse options
        try:
            option_dict = {k.strip(): v.strip() for k, v in (opt.split("=") for opt in self.options.split(","))}
        except ValueError:
            raise ValidationError(f"Options must be valid key=value pairs. Example: max_length=100, unique=True")

        # Validate mandatory options
        mandatory_options = field_options_help[self.relation_type]["mandatory"]
        for option in mandatory_options:
            if option not in option_dict:
                raise ValidationError(f"Mandatory option '{option}' is missing for field type '{self.relation_type}'.")

            # Check for

            # Validate field_type
            if self.relation_type not in field_options_help:
                raise ValidationError(f"Invalid field type: {self.relation_type}")

            # Parse options
            try:
                option_dict = {k.strip(): v.strip() for k, v in (opt.split("=") for opt in self.options.split(","))}
            except ValueError:
                raise ValidationError(f"Options must be valid key=value pairs. Example: max_length=100, unique=True")

            # Validate mandatory options
            mandatory_options = field_options_help[self.relation_type]["mandatory"]
            for option in mandatory_options:
                if option not in option_dict:
                    raise ValidationError(f"Mandatory option '{option}' is missing for field type '{self.relation_type}'.")

            # Check for unknown options
            valid_options = mandatory_options + field_options_help[self.relation_type]["optional"]
            for option in option_dict:
                if option not in valid_options:
                    raise ValidationError(f"Invalid option '{option}' for field type '{self.relation_type}'.")

    def __str__(self):
        return f"{self.relation_name} -> {self.related_model} ({self.relation_type})"

    def compile_relationship(self):
        return {
            "name": self.relation_name,
            "type": self.relation_type,
            "related_model": self.related_model,
            "options": self.options
        }
