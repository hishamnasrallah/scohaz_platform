from django.apps import AppConfig

class CrmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crm'

    def ready(self):
        # Custom initialization logic for crm
        import crm.signals
        print('App crm is ready!')
