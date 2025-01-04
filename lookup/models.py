from django.db import models
from django.apps import apps

# Create your models here.


class Lookup(models.Model):
    class LookupTypeChoices(models.IntegerChoices):
        LOOKUP = 1
        LOOKUP_VALUE = 2

    parent_lookup = models.ForeignKey('self',
                                      null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name='lookup_children')
    type = models.IntegerField(
        choices=LookupTypeChoices.choices,
        default=LookupTypeChoices.LOOKUP_VALUE,
    )
    name = models.CharField(max_length=50, null=True, blank=True)
    name_ara = models.CharField(max_length=50, null=True, blank=True)
    code = models.CharField(max_length=20, null=True, blank=True)
    icon = models.CharField(max_length=100, null=True, blank=True)
    is_category = models.BooleanField(default=False)
    active_ind = models.BooleanField(default=True, null=True, blank=True)

    def __str__(self):
        return self.name


class LookupConfig(models.Model):
    """
    A configuration model to map specific model fields to lookup categories
    """
    model_name = models.CharField(max_length=50)
    field_name = models.CharField(max_length=50)
    # This will be the name of the lookup category
    lookup_category = models.CharField(max_length=100)

    def __str__(self):
        return (f"{self.model_name} - "
                f"{self.field_name} -> {self.lookup_category}")

    @staticmethod
    def get_model_choices():
        """
        Dynamically retrieve model choices from installed apps.
        """
        model_choices = []
        # Loop through all models in all installed apps
        for app_config in apps.get_app_configs():
            for model in app_config.get_models():
                # Add the model name to the model choices
                model_choices.append(
                    (model._meta.model_name, model._meta.verbose_name))
        return model_choices

    @staticmethod
    def get_lookup_category_choices():
        """
        Dynamically retrieve the available lookup categories based on type=LOOKUP.
        """
        lookup_categories = Lookup.objects.filter(
            type=Lookup.LookupTypeChoices.LOOKUP)
        return [(category.name, category.name) for category in lookup_categories]
