from django.apps import AppConfig


class WorkforceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'workforce'

    def ready(self):
        # Import payroll_models so Django registers them
        from . import payroll_models  # noqa: F401
