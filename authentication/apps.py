from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'authentication'
    verbose_name = 'Users and Authentication'
    verbose_name_plural = 'Authentication'

    # def ready(self):
    #     import authentication.signals
