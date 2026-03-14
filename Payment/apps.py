from django.apps import AppConfig


class PaymentConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "Payment"

    def ready(self):
        import Payment.signals  # noqa: F401 — register post_save signals
