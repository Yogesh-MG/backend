from django.apps import AppConfig


class PaymentConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.payment'
    
    def ready(self):
        """Called when Django starts."""
        # Import and configure ICICI client
        try:
            from .icici_client import configure_from_settings
            configure_from_settings()
        except Exception:
            # Don't fail startup if ICICI is not configured
            pass
