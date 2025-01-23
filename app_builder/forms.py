# app_builder/forms.py

from django import forms
from django.forms import (
    ModelForm,
    inlineformset_factory,
    BaseInlineFormSet
)
from .models import (
    ApplicationDefinition,
    ModelDefinition,
    FieldDefinition,
    RelationshipDefinition
)

class ApplicationDefinitionForm(ModelForm):
    class Meta:
        model = ApplicationDefinition
        fields = [
            'app_name',
            'overwrite',
            'skip_admin',
            'skip_tests',
            'skip_urls'
        ]

ModelDefinitionFormSet = inlineformset_factory(
    parent_model=ApplicationDefinition,
    model=ModelDefinition,
    fields=[
        'model_name',
        'db_table',
        'verbose_name',
        'verbose_name_plural',
        'ordering',
        'unique_together',
        'indexes',
        'constraints'
    ],
    extra=0,
    can_delete=True
)

FieldDefinitionFormSet = inlineformset_factory(
    parent_model=ModelDefinition,
    model=FieldDefinition,
    fields=[
        'field_name',
        'field_type',
        'options',
        'has_choices',
        'choices_json'
    ],
    extra=0,
    can_delete=True
)

RelationshipDefinitionFormSet = inlineformset_factory(
    parent_model=ModelDefinition,
    model=RelationshipDefinition,
    fields=[
        'relation_name',
        'relation_type',
        'related_model',
        'options'
    ],
    extra=0,
    can_delete=True
)
