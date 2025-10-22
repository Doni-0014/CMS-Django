# Doctor/signals.py
"""
Automation for Doctor app workflows
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import Consultation, MedicinePrescription

@receiver(post_save, sender=Consultation)
def auto_mark_appointment_completed(sender, instance, created, **kwargs):
    """
    AUTOMATION 1: When doctor saves consultation, mark appointment as 'completed'
    """
    if instance.appointment and instance.appointment.status != 'completed':
        instance.appointment.status = 'completed'
        instance.appointment.save(update_fields=['status'])
        print(f"✅ AUTOMATION: Appointment {instance.appointment.appointment_id} marked as COMPLETED")


@receiver(post_save, sender=Consultation)
def auto_create_prescription_form(sender, instance, created, **kwargs):
    """
    AUTOMATION 2: Auto-create empty prescription when consultation is created
    (Optional - doctor can choose to use it or not)
    """
    if created:
        # Check if prescription already exists
        if not MedicinePrescription.objects.filter(consultation=instance).exists():
            MedicinePrescription.objects.create(
                consultation=instance,
                medicine_name="",  # Empty - doctor will fill
                dosage="",
                frequency="",
                duration_days=None
            )
            print(f"✅ AUTOMATION: Empty prescription form created for consultation {instance.consultation_id}")


@receiver(post_save, sender=MedicinePrescription)
def notify_pharmacist_new_prescription(sender, instance, created, **kwargs):
    """
    AUTOMATION 3: When doctor creates/updates prescription with medicine name,
    notify pharmacist (shows in pending prescriptions)
    """
    if instance.medicine_name:  # Only notify if medicine is specified
        print(f"✅ AUTOMATION: New prescription ready for pharmacy")
        print(f"   Patient: {instance.consultation.patient.full_name}")
        print(f"   Medicine: {instance.medicine_name}")
        print(f"   Doctor: Dr. {instance.consultation.doctor.doctor_name}")
        # In production: Create notification record for pharmacist dashboard
