from django.apps import AppConfig


class RoomsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Rooms'
    
    def ready(self):
        # Import signals to register them
        import Rooms.auto_creation
