#duplicated file

from django.db import models
<<<<<<< HEAD

class Doctor(models.Model):
    name = models.CharField(max_length=100)
    specialty = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name
=======
from django.utils import timezone
from Authentication.models import Doctor
from Receptionist.models import Appointment, Patient
# Create your models here.

class Consultation(models.Model):
    consultation_id = models.CharField(max_length=20, primary_key=True, editable=False)
    appointment = models.ForeignKey(Appointment, on_delete=models.SET_NULL)
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL)
    doctor = models.ForeignKey(Doctor, on_delete=models.SET_NULL)
    symptoms = models.TextField(blank=True)
    diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        if not self.consultation_id:
            last_id = Consultation.objects.all().order_by('created_at').last()
            if last_id:
                last_number = int(last_id.consultation_id.replace('CONID', ''))
                new_number = last_number + 1
            else:
                new_number = 1001
            self.consultation_id = f"CSTID{new_number}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Consultation #{self.consultation_id} - Patient: {self.patient.full_name} with Dr: {self.doctor.DocId}"

class MedicinePrescription(models.Model):
    prescription_id = models.CharField(max_length=20, primary_key=True, editable=False)
    consultation = models.ForeignKey(Consultation, on_delete=models.SET_NULL)
    medicine = models.ForeignKey()
    dosage = models.CharField(max_length=200)
    frequency = models.CharField(max_length=200)
    duration_days = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def save(self, *args, **kwargs):
        if not self.prescription_id:
            last = MedicinePrescription.objects.all().order_by('created_at').last()
            if last:
                last_number = int(last.prescription_id.replace('MEDPR', ''))
                new_number = last_number + 1
            else:
                new_number = 1001
            self.prescription_id = f"MEDPR{new_number}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"(Medicine) for consultation: {self.consultation.consultation_id}"
>>>>>>> c7f23ddb54f0b42c7ea05877b0e8c8fbfbfa92b5
