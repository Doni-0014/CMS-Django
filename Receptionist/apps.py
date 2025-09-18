# Receptionist/apps.py

from django.apps import AppConfig

class ReceptionistConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'Receptionist'
    
    def ready(self):
        import Receptionist.signals  # Import signals when app is ready
