from django.apps import AppConfig


class SalesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'applications.sales'

    def ready(self):
        import applications.sales.signals  # ← Esto carga los signals