# Receptionist/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Patient, Registration, Appointment, Bill

@receiver(post_save, sender=Registration)
def create_registration_bill(sender, instance, created, **kwargs):
    """Create bill for registration fee when patient registers"""
    if created:
        # Use correct bill type names that match generate_bill_items()
        bill_type = 'registration' if instance.registration_type == 'initial' else 'renewal'
        
        bill = Bill.objects.create(
            registration=instance,
            bill_type=bill_type  # This matches your billing logic
        )
        bill.generate_bill_items()

@receiver(post_save, sender=Appointment) 
def create_appointment_bill(sender, instance, created, **kwargs):
    """Create or update bill when appointment is booked"""
    if created and instance.status in ['phone_booked', 'confirmed']:
        # Check if patient already has a pending registration bill
        existing_bill = Bill.objects.filter(
            registration__patient=instance.patient,
            payment_status='pending'
        ).first()
        
        if existing_bill:
            # Convert to combined bill with correct bill type
            existing_bill.appointment = instance
            
            #  Use correct combined bill types
            if existing_bill.bill_type == 'registration':
                existing_bill.bill_type = 'registration_consultation'
            elif existing_bill.bill_type == 'renewal':
                existing_bill.bill_type = 'renewal_consultation'
            
            existing_bill.save()
            existing_bill.generate_bill_items()
        else:
            # Create new bill for appointment only
            bill = Bill.objects.create(
                appointment=instance,
                bill_type='consultation'  # This matches your billing logic
            )
            bill.generate_bill_items()
