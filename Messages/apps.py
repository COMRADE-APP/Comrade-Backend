from django.apps import AppConfig


class MessagesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Messages'
    verbose_name = 'Direct Messages'
    
    def ready(self):
        import Messages.signals  # noqa
