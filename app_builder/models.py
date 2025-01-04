from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

class Application(models.Model):
    """
    Represents an application to be built dynamically using the Application Builder.
    """
    name = models.CharField(max_length=255, unique=True, verbose_name=_("Application Name"))
    description = models.TextField(blank=True, null=True, verbose_name=_("Description"))
    created_by = models.ForeignKey(
        get_user_model(), on_delete=models.SET_NULL, null=True, related_name='created_applications'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class ModelDefinition(models.Model):
    """
    Defines a dynamic model to be created within an application.
    """
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='models')
    name = models.CharField(max_length=255, verbose_name=_("Model Name"))
    fields = models.JSONField(verbose_name=_("Fields Definition"))  # Field definitions in JSON format
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.application.name})"
