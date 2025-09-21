from django.contrib import admin
from .models import Consultation, MedicinePrescription
# Register your models here.

admin.site.register(Consultation)
admin.site.register(MedicinePrescription)
