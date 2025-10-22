# Doctor/apps.py
from django.apps import AppConfig


class DoctorConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Doctor'
    
    def ready(self):
        """
        Import signals when app is ready to enable automation
        """
        import Doctor.signals
