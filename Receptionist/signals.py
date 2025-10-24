# Receptionist/signals.py
# IMPROVED VERSION - Handles all scenarios correctly

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
from .models import Patient, Registration, Appointment, Bill, BillItem


@receiver(post_save, sender=Appointment)
def auto_generate_appointment_bill(sender, instance, created, **kwargs):
    """
    Auto-generate bill when appointment is created
    
    SCENARIOS:
    1. New patient (no registration) → Create registration + consultation bill
    2. Expired registration → Create renewal + consultation bill
    3. Valid registration → Create consultation-only bill
    """
    
    # Only run when appointment is first created
    if not created:
        return
    
    # Don't create duplicate bills
    if hasattr(instance, 'bill'):
        return
    
    # Only for confirmed/phone_booked appointments
    if instance.status not in ['phone_booked', 'confirmed']:
        return
    
    patient = instance.patient
    doctor = instance.doctor
    
    # Configuration (you can move these to settings.py)
    REGISTRATION_FEE = Decimal('100.00')
    RENEWAL_FEE = Decimal('50.00')
    
    # Check patient's registration status
    try:
        registration = patient.registration
        has_registration = True
        is_expired = registration.expiry_date < date.today()
    except Registration.DoesNotExist:
        has_registration = False
        is_expired = False
    
    
    # ==========================================
    # SCENARIO 1: NEW PATIENT (No Registration)
    # ==========================================
    if not has_registration:
        # Step 1: Create new registration
        registration = Registration.objects.create(
            patient=patient,
            registration_type='initial',
            fee_amount=REGISTRATION_FEE,
            registration_date=date.today(),
            expiry_date=date.today() + timedelta(days=365),
            is_active=1
        )
        
        # Step 2: Create combined bill
        bill = Bill.objects.create(
            bill_type='registration',  # Main type is registration
            registration=registration,
            appointment=instance,
            total_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            payment_status='pending'
        )
        
        # Step 3: Add bill items
        # Registration fee item
        BillItem.objects.create(
            bill=bill,
            item_type='registration',
            description='Initial Registration Fee (1 Year)',
            amount=REGISTRATION_FEE
        )
        
        # Consultation fee item
        BillItem.objects.create(
            bill=bill,
            item_type='consultation',
            description=f'Consultation with Dr. {doctor.staff.staff_name}',
            amount=doctor.consultation_fee
        )
        
        # Step 4: Calculate totals
        bill.total_amount = REGISTRATION_FEE + doctor.consultation_fee
        bill.final_amount = bill.total_amount - bill.discount_amount
        bill.save()
        
        print(f" Created NEW PATIENT bill: {bill.bill_number} (Registration ₹{REGISTRATION_FEE} + Consultation ₹{doctor.consultation_fee})")
    
    
    # ==========================================
    # SCENARIO 2: EXPIRED REGISTRATION
    # ==========================================
    elif is_expired:
        # Step 1: Update registration to renewal
        registration.registration_type = 'renewal'
        registration.fee_amount = RENEWAL_FEE
        registration.registration_date = date.today()
        registration.expiry_date = date.today() + timedelta(days=365)
        registration.save()
        
        # Step 2: Create combined bill
        bill = Bill.objects.create(
            bill_type='renewal',  # Main type is renewal
            registration=registration,
            appointment=instance,
            total_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            payment_status='pending'
        )
        
        # Step 3: Add bill items
        # Renewal fee item
        BillItem.objects.create(
            bill=bill,
            item_type='registration',
            description='Registration Renewal Fee (1 Year)',
            amount=RENEWAL_FEE
        )
        
        # Consultation fee item
        BillItem.objects.create(
            bill=bill,
            item_type='consultation',
            description=f'Consultation with Dr. {doctor.staff.staff_name}',
            amount=doctor.consultation_fee
        )
        
        # Step 4: Calculate totals
        bill.total_amount = RENEWAL_FEE + doctor.consultation_fee
        bill.final_amount = bill.total_amount - bill.discount_amount
        bill.save()
        
        print(f"✅ Created RENEWAL bill: {bill.bill_number} (Renewal ₹{RENEWAL_FEE} + Consultation ₹{doctor.consultation_fee})")
    
    
    # ==========================================
    # SCENARIO 3: VALID REGISTRATION
    # ==========================================
    else:
        # Step 1: Create consultation-only bill
        bill = Bill.objects.create(
            bill_type='consultation',
            registration=registration,  # Link to existing registration
            appointment=instance,
            total_amount=Decimal('0.00'),
            discount_amount=Decimal('0.00'),
            final_amount=Decimal('0.00'),
            payment_status='pending'
        )
        
        # Step 2: Add consultation fee item
        BillItem.objects.create(
            bill=bill,
            item_type='consultation',
            description=f'Consultation with Dr. {doctor.staff.staff_name}',
            amount=doctor.consultation_fee
        )
        
        # Step 3: Calculate totals
        bill.total_amount = doctor.consultation_fee
        bill.final_amount = bill.total_amount - bill.discount_amount
        bill.save()
        
        print(f"Created CONSULTATION bill: {bill.bill_number} (Consultation ₹{doctor.consultation_fee})")
