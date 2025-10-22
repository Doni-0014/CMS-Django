# Receptionist/models.py
from decimal import Decimal
from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, datetime, timedelta
import calendar


def get_today_date():
    """Return today's date - used as default for registration_date"""
    return date.today()


# ==========================================
# PATIENT MODEL
# ==========================================
class PatientManager(models.Manager):
    """Manager for Patient model"""
    
    def active_patients(self):
        """Get all active patients"""
        return self.filter(is_active=True)


class Patient(models.Model):
    """Patient model - source of truth for patient data across all apps"""
    
    class BloodGroups(models.TextChoices):
        A_POSITIVE = 'A+', 'A+'
        A_NEGATIVE = 'A-', 'A-'
        B_POSITIVE = 'B+', 'B+'
        B_NEGATIVE = 'B-', 'B-'
        O_POSITIVE = 'O+', 'O+'
        O_NEGATIVE = 'O-', 'O-'
        AB_POSITIVE = 'AB+', 'AB+'
        AB_NEGATIVE = 'AB-', 'AB-'
    
    class Gender(models.TextChoices):
        MALE = 'M', 'Male'
        FEMALE = 'F', 'Female'
    
    # Fields
    patient_reg_number = models.CharField(max_length=20, unique=True, editable=False)
    full_name = models.CharField(max_length=100, validators=[MinLengthValidator(3)])
    date_of_birth = models.DateField()
    blood_group = models.CharField(max_length=3, choices=BloodGroups.choices)
    phone_number = models.CharField(
        max_length=10,
        validators=[RegexValidator(regex=r'^[6-9]\d{9}$', message='Invalid phone number')]
    )
    address = models.TextField()
    gender = models.CharField(max_length=1, choices=Gender.choices)
    is_active = models.IntegerField(default=1, db_column='is_active')  # IntegerField to match DB
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = PatientManager()
    
    class Meta:
        db_table = 'receptionist_patient'
        ordering = ['-created_at']
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
    
    def __str__(self):
        return f"{self.patient_reg_number} - {self.full_name}"
    
    @property
    def age(self):
        """Calculate age from date of birth"""
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    @property
    def is_senior_citizen(self):
        """Check if patient is senior citizen (60+)"""
        return self.age >= 60
    
    @property
    def registration_status(self):
        """Get registration status"""
        try:
            if self.registration.is_active and self.registration.expiry_date >= date.today():
                return 'Active'
            return 'Expired'
        except:
            return 'Not Registered'
    
    def save(self, *args, **kwargs):
        if not self.patient_reg_number:
            # Generate patient registration number
            last_patient = Patient.objects.order_by('-id').first()
            if last_patient and last_patient.patient_reg_number:
                try:
                    last_number = int(last_patient.patient_reg_number.split('P')[1])
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            self.patient_reg_number = f'P{new_number:05d}'
        super().save(*args, **kwargs)


# ==========================================
# REGISTRATION MODEL
# ==========================================
class Registration(models.Model):
    """Patient registration model"""
    
    class RegistrationType(models.TextChoices):
        INITIAL = 'initial', 'Initial Registration'
        RENEWAL = 'renewal', 'Renewal'
    
    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='registration')
    registration_date = models.DateField(default=get_today_date)
    expiry_date = models.DateField(null=True, blank=True)
    registration_type = models.CharField(max_length=10, choices=RegistrationType.choices, default='initial')
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.IntegerField(default=1, db_column='is_active')  # IntegerField to match DB
    
    class Meta:
        db_table = 'receptionist_registration'
        verbose_name = 'Registration'
        verbose_name_plural = 'Registrations'
    
    def __str__(self):
        return f"Registration - {self.patient.patient_reg_number} ({self.registration_type})"
    
    def save(self, *args, **kwargs):
        # Calculate expiry date based on registration type
        if not self.expiry_date:
            if self.registration_type == 'initial':
                self.expiry_date = self.registration_date + timedelta(days=365)
            elif self.registration_type == 'renewal':
                self.expiry_date = self.registration_date + timedelta(days=365)
        super().save(*args, **kwargs)


# ==========================================
# APPOINTMENT MODEL (LINKED TO AUTHENTICATION.DOCTOR)
# ==========================================
class Appointment(models.Model):
    """
    Appointment model - Links to Authentication.Doctor (not dummy doctor)
    """
    
    class AppointmentStatus(models.TextChoices):
        PHONE_BOOKED = 'phone_booked', 'Phone Booked'
        CONFIRMED = 'confirmed', 'Confirmed'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'
    
    appointment_id = models.CharField(max_length=20, unique=True, editable=False)
    
    # FIXED: Reference Authentication.Doctor instead of dummy doctor
    doctor = models.ForeignKey(
        'Authentication.Doctor',  # Links to real doctor model
        on_delete=models.CASCADE,
        related_name='appointments',
        db_column='doctor_id'  # Maps to existing column
    )
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    
    appointment_date = models.DateField()
    token_number = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=15, choices=AppointmentStatus.choices, default='phone_booked')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.IntegerField(default=1, db_column='is_active')  # IntegerField to match DB
    
    class Meta:
        db_table = 'receptionist_appointment'
        unique_together = ['doctor', 'appointment_date', 'token_number']
        ordering = ['appointment_date', 'token_number']
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
    
    def __str__(self):
        return f"{self.appointment_id} - {self.patient.full_name} with Dr. {self.doctor.doctor_name}"
    
    def save(self, *args, **kwargs):
        if not self.appointment_id:
            # Generate appointment ID
            today = date.today()
            prefix = f'APT{today.strftime("%Y%m%d")}'
            last_appointment = Appointment.objects.filter(
                appointment_id__startswith=prefix
            ).order_by('-appointment_id').first()
            
            if last_appointment:
                try:
                    last_number = int(last_appointment.appointment_id[-4:])
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            
            self.appointment_id = f'{prefix}{new_number:04d}'
        
        super().save(*args, **kwargs)


# ==========================================
# BILL & BILLITEM MODELS
# ==========================================
class Bill(models.Model):
    """Bill model for patient billing"""
    
    class BillType(models.TextChoices):
        REGISTRATION = 'registration', 'Registration Fee'
        RENEWAL = 'renewal', 'Renewal Fee'
        CONSULTATION = 'consultation', 'Consultation Fee'
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PAID = 'paid', 'Paid'
        CANCELLED = 'cancelled', 'Cancelled'
    
    class PaymentMode(models.TextChoices):
        CASH = 'cash', 'Cash'
        CARD = 'card', 'Card'
        UPI = 'upi', 'UPI'
        ONLINE = 'online', 'Online'
    
    bill_number = models.CharField(max_length=20, unique=True, editable=False)
    bill_type = models.CharField(max_length=30, choices=BillType.choices)
    
    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name='bills',
        null=True,
        blank=True
    )
    
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='bill',
        null=True,
        blank=True
    )
    
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default='pending')
    payment_mode = models.CharField(max_length=10, choices=PaymentMode.choices, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = 'receptionist_bill'
        ordering = ['-created_at']
        verbose_name = 'Bill'
        verbose_name_plural = 'Bills'
    
    def __str__(self):
        return f"{self.bill_number} - {self.bill_type} (₹{self.final_amount})"
    
    def save(self, *args, **kwargs):
        if not self.bill_number:
            # Generate bill number
            today = date.today()
            prefix = f'BILL{today.strftime("%Y%m%d")}'
            last_bill = Bill.objects.filter(
                bill_number__startswith=prefix
            ).order_by('-bill_number').first()
            
            if last_bill:
                try:
                    last_number = int(last_bill.bill_number[-4:])
                    new_number = last_number + 1
                except:
                    new_number = 1
            else:
                new_number = 1
            
            self.bill_number = f'{prefix}{new_number:04d}'
        
        # Calculate final amount
        self.final_amount = self.total_amount - self.discount_amount
        
        super().save(*args, **kwargs)
    
    def generate_bill_items(self):
        """Generate bill items based on bill type"""
        if self.bill_type == 'registration':
            BillItem.objects.create(
                bill=self,
                item_type='registration',
                description='Initial Registration Fee',
                amount=self.registration.fee_amount if self.registration else 0
            )
        elif self.bill_type == 'renewal':
            BillItem.objects.create(
                bill=self,
                item_type='registration',
                description='Registration Renewal Fee',
                amount=self.registration.fee_amount if self.registration else 0
            )
        elif self.bill_type == 'consultation':
            BillItem.objects.create(
                bill=self,
                item_type='consultation',
                description=f'Consultation with Dr. {self.appointment.doctor.doctor_name}',
                amount=self.appointment.doctor.consultation_fee if self.appointment else 0
            )
        
        # Update total amount
        self.total_amount = sum(item.amount for item in self.bill_items.all())
        self.save()


class BillItem(models.Model):
    """Bill items for detailed billing"""
    
    class ItemType(models.TextChoices):
        REGISTRATION = 'registration', 'Registration'
        CONSULTATION = 'consultation', 'Consultation'
        PROCEDURE = 'procedure', 'Procedure'
    
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='bill_items')
    item_type = models.CharField(max_length=15, choices=ItemType.choices)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'receptionist_billitem'
        verbose_name = 'Bill Item'
        verbose_name_plural = 'Bill Items'
    
    def __str__(self):
        return f"{self.bill.bill_number} - {self.description} (₹{self.amount})"
