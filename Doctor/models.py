# Doctor/models.py
from django.db import models
from django.core.validators import MinValueValidator
from Authentication.models import Doctor as AuthDoctor
from Receptionist.models import Patient, Appointment
from decimal import Decimal


class Consultation(models.Model):
    """
    Doctor consultation records with patient
    """
    
    consultation_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        primary_key=True,
        db_column='consultation_id'
    )
    
    # Links to other apps
    doctor = models.ForeignKey(
        AuthDoctor,
        on_delete=models.CASCADE,
        related_name='consultations',
        db_column='doctor_id',
        help_text="Doctor from Authentication app"
    )
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='consultations',
        db_column='patient_id',
        help_text="Patient from Receptionist app"
    )
    
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='consultations',
        db_column='appointment_id',
        help_text="Optional link to appointment"
    )
    
    # Consultation details
    symptoms = models.TextField(db_column='symptoms')
    diagnosis = models.TextField(db_column='diagnosis')
    notes = models.TextField(blank=True, db_column='notes')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    is_active = models.IntegerField(default=1, db_column='is_active')
    
    class Meta:
        db_table = 'doctor_consultation'
        ordering = ['-created_at']
        verbose_name = 'Consultation'
        verbose_name_plural = 'Consultations'
    
    def save(self, *args, **kwargs):
        """Auto-generate consultation ID and add to patient history"""
        if not self.consultation_id:
            # Generate consultation ID
            from datetime import datetime
            today = datetime.now()
            prefix = f'CONS{today.strftime("%Y%m%d")}'
            
            # Get last consultation for today
            last_consultation = Consultation.objects.filter(
                consultation_id__startswith=prefix
            ).order_by('-consultation_id').first()
            
            if last_consultation:
                try:
                    last_number = int(last_consultation.consultation_id[-4:])
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            
            self.consultation_id = f'{prefix}{new_number:04d}'
        
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # AUTOMATION: Auto-add to patient medical history
        if is_new:
            print(f"✅ AUTOMATION: Consultation {self.consultation_id} added to {self.patient.full_name}'s medical history")
    
    def __str__(self):
        return f"{self.consultation_id} - {self.patient.full_name} with Dr. {self.doctor.doctor_name}"
    
    @property
    def has_prescription(self):
        """Check if consultation has any prescriptions"""
        return self.prescriptions.filter(
            medicine_name__isnull=False
        ).exclude(
            medicine_name=''
        ).exists()
    
    @property
    def doctor_name(self):
        """Get doctor name"""
        return self.doctor.doctor_name if self.doctor else 'N/A'
    
    @property
    def patient_name(self):
        """Get patient name"""
        return self.patient.full_name if self.patient else 'N/A'


class MedicinePrescription(models.Model):
    """
    Medicine prescriptions by doctors
    """
    
    class FulfillmentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending at Pharmacy'
        PARTIALLY_FULFILLED = 'partial', 'Partially Fulfilled'
        FULFILLED = 'fulfilled', 'Fulfilled'
        CANCELLED = 'cancelled', 'Cancelled'
    
    prescription_id = models.CharField(
        max_length=20,
        unique=True,
        editable=False,
        primary_key=True,
        db_column='prescription_id'
    )
    
    # Link to consultation
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name='prescriptions',
        db_column='consultation_id',
        help_text="Link to consultation record"
    )
    
    # Medicine details
    medicine_name = models.CharField(
        max_length=200,
        blank=True,
        db_column='medicine_name',
        help_text="Name of medicine prescribed"
    )
    
    dosage = models.CharField(
        max_length=100,
        blank=True,
        db_column='dosage',
        help_text="e.g., 500mg"
    )
    
    frequency = models.CharField(
        max_length=100,
        blank=True,
        db_column='frequency',
        help_text="e.g., 3 times daily"
    )
    
    duration_days = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1)],
        db_column='duration_days',
        help_text="Duration in days"
    )
    
    # Pharmacy fulfillment tracking
    fulfillment_status = models.CharField(
        max_length=20,
        choices=FulfillmentStatus.choices,
        default='pending',
        db_column='fulfillment_status',
        help_text="Pharmacy fulfillment status"
    )
    
    dispensed_quantity = models.IntegerField(
        null=True,
        blank=True,
        db_column='dispensed_quantity',
        help_text="Actual quantity dispensed by pharmacist"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    is_active = models.IntegerField(default=1, db_column='is_active')
    
    class Meta:
        db_table = 'doctor_medicineprescription'
        ordering = ['-created_at']
        verbose_name = 'Medicine Prescription'
        verbose_name_plural = 'Medicine Prescriptions'
    
    def save(self, *args, **kwargs):
        """Auto-generate prescription ID"""
        if not self.prescription_id:
            # Generate prescription ID
            from datetime import datetime
            today = datetime.now()
            prefix = f'RX{today.strftime("%Y%m%d")}'
            
            # Get last prescription for today
            last_prescription = MedicinePrescription.objects.filter(
                prescription_id__startswith=prefix
            ).order_by('-prescription_id').first()
            
            if last_prescription:
                try:
                    last_number = int(last_prescription.prescription_id[-4:])
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            
            self.prescription_id = f'{prefix}{new_number:04d}'
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.prescription_id} - {self.medicine_name or 'Empty'}"
    
    @property
    def is_pending_pharmacy(self):
        """Check if prescription is pending at pharmacy"""
        return (
            self.fulfillment_status == 'pending' and 
            bool(self.medicine_name) and 
            self.medicine_name.strip() != ''
        )
    
    @property
    def patient_name(self):
        """Get patient name"""
        return self.consultation.patient.full_name if self.consultation else 'N/A'
    
    @property
    def doctor_name(self):
        """Get doctor name"""
        return self.consultation.doctor.doctor_name if self.consultation else 'N/A'
    
    @property
    def is_fulfilled(self):
        """Check if prescription is fully fulfilled"""
        return self.fulfillment_status == 'fulfilled'
    
    @property
    def is_partial(self):
        """Check if prescription is partially fulfilled"""
        return self.fulfillment_status == 'partial'
