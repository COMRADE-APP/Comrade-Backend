from django.apps import AppConfig


class VerificationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Verification'
    
    def ready(self):
        import Verification.signals
