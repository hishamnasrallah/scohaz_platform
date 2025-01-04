from django.core.exceptions import FieldDoesNotExist
from rest_framework import serializers

from lookup.models import Lookup, LookupConfig
from django.db import models


class LookupCategoryMixin:
    def create_lookup_field(self, lookup_category, field_name):
        """
        Create a PrimaryKeyRelatedField dynamically for a specified lookup category.
        """
        # Get all lookup values under the given category
        lookup_values = Lookup.objects.filter(
            parent_lookup__name=lookup_category,
            type=Lookup.LookupTypeChoices.LOOKUP_VALUE
        )

        # Return the dynamic field
        return serializers.PrimaryKeyRelatedField(
            queryset=lookup_values,
            error_messages={
                'does_not_exist': f"This {field_name} does not exist in the "
                                  f"'{lookup_category}' category."
            }
        )

    def get_dynamic_lookup_fields(self, model_class):
        """
        Dynamically create lookup fields based on LookupConfig for a given model class.
        """
        fields = {}

        # Normalize model name to lowercase for consistent comparison
        model_name = model_class._meta.model_name

        # Fetch configurations for this model using case-insensitive filtering
        configs = LookupConfig.objects.filter(model_name__iexact=model_name)

        # Process each configuration
        for config in configs:
            field_name = config.field_name
            try:
                field = model_class._meta.get_field(field_name)

                # Ensure the field is a ForeignKey to the Lookup model
                if (isinstance(field, models.ForeignKey)
                        and field.related_model == Lookup):
                    fields[field_name] = self.create_lookup_field(
                        config.lookup_category, field_name)
            except FieldDoesNotExist:
                continue  # Skip if the field doesn't exist

        return fields


class GenericLookupsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lookup
        fields = ['id', 'parent_lookup', 'type', 'name', 'name_ara',
                  'code', 'icon', 'active_ind']
