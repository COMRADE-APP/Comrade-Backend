from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Authentication'
    
    def ready(self):
        """Import signals to register receivers"""
        import Authentication.signals  # noqa
        
        # Connect global file scanner to all models
        from django.apps import apps
        from django.db.models.signals import post_save
        from comrade.signals import global_file_scan_receiver
        
        for model in apps.get_models():
            post_save.connect(global_file_scan_receiver, sender=model)
