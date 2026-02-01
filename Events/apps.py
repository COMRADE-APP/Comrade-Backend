from django.apps import AppConfig


class EventsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Events'

    def ready(self):
        import Events.signals  # noqa: F401
