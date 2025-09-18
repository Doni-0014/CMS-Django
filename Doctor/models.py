from django.db import models
from django.utils import timezone
# Create your models here.

class Consultation(models.Model):
    consultation_id = models.AutoField(primary_key=True)
    appointment = models.ForeignKey()
    patient = models.ForeignKey()
    doctor = models.ForeignKey()
    symptoms = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Consultation #{self.id} - Patient (Patient ID) with Dr (Doctor ID)"

class MedicinePrescription(models.Model):
    prescription_id = models.AutoField(primary_key=True)
    consultation = models.ForeignKey()
    medicine = models.ForeignKey()
    dosage = models.CharField(max_length=200)
    frequency = models.CharField(max_length=200)
    duration_days = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"(Medicine) for consultation (self.consultation)"