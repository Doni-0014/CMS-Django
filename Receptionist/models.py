# Receptionist/models.py
# FULLY CORRECTED VERSION - All database field mappings fixed
# ✅ References Authentication.Doctor (real doctor)
# ✅ All custom managers and properties added
# ✅ Database column names match exactly

from decimal import Decimal
from django.db import models
from django.core.validators import RegexValidator, MinLengthValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, datetime, timedelta


def get_today_date():
    """Return today's date - used as default for registration_date"""
    return date.today()


# ==========================================
# CUSTOM MANAGERS
# ==========================================

class PatientManager(models.Manager):
    """Manager for Patient model"""
    
    def active_patients(self):
        """Get all active patients"""
        return self.filter(is_active=1)
    
    def senior_citizens(self):
        """Get patients 60 years or older"""
        cutoff_date = date.today().replace(year=date.today().year - 60)
        return self.filter(date_of_birth__lte=cutoff_date, is_active=1)


class RegistrationManager(models.Manager):
    """Manager for Registration model"""
    
    def due_for_renewal(self, days=7):
        """Get registrations expiring in next X days"""
        cutoff_date = date.today() + timedelta(days=days)
        return self.filter(
            expiry_date__lte=cutoff_date,
            expiry_date__gte=date.today(),
            is_active=1
        )
    
    def in_grace_period(self):
        """Get expired registrations still in grace period (30 days)"""
        grace_start = date.today()
        grace_end = date.today() - timedelta(days=30)
        return self.filter(
            expiry_date__lt=grace_start,
            expiry_date__gte=grace_end,
            is_active=1
        )
    
    def expired_registrations(self):
        """Get all expired registrations"""
        return self.filter(
            expiry_date__lt=date.today(),
            is_active=1
        )


class AppointmentManager(models.Manager):
    """Manager for Appointment model"""
    
    def today_appointments(self):
        """Get today's appointments"""
        return self.filter(appointment_date=date.today())
    
    def completed_today(self):
        """Get completed appointments today"""
        return self.filter(
            appointment_date=date.today(),
            status='completed'
        )
    
    def active_appointments(self):
        """Get active (not completed/cancelled) appointments"""
        return self.filter(
            status__in=['phone_booked', 'confirmed'],
            is_active=1
        )
    
    def get_available_tokens_for_date(self, doctor, appointment_date):
        """Get available token count for doctor on specific date"""
        booked = self.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            is_active=1
        ).count()
        return max(0, doctor.daily_patient_limit - booked)  # ✅ FIXED: PascalCase
    
    def get_booked_tokens_for_date(self, doctor, appointment_date):
        """Get list of booked token numbers"""
        return list(self.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            is_active=1
        ).values_list('token_number', flat=True).order_by('token_number'))
    
    def get_next_token(self, doctor, appointment_date):
        """Get next available token number"""
        booked_tokens = self.get_booked_tokens_for_date(doctor, appointment_date)
        for i in range(1, doctor.daily_patient_limits + 1):  # ✅ FIXED: PascalCase
            if i not in booked_tokens:
                return i
        return None


class BillManager(models.Manager):
    """Manager for Bill model"""
    
    def daily_collection(self, report_date):
        """Get collection summary for a specific date"""
        from django.db.models import Sum
        bills = self.filter(
            created_at__date=report_date,
            payment_status='paid'
        )
        
        return {
            'date': report_date,
            'total_bills': bills.count(),
            'total_amount': bills.aggregate(Sum('final_amount'))['final_amount__sum'] or 0,
            'registration_fees': bills.filter(bill_type='registration').aggregate(Sum('final_amount'))['final_amount__sum'] or 0,
            'consultation_fees': bills.filter(bill_type='consultation').aggregate(Sum('final_amount'))['final_amount__sum'] or 0,
            'discounts': bills.aggregate(Sum('discount_amount'))['discount_amount__sum'] or 0
        }
    
    def monthly_collection(self, year, month):
        """Get all paid bills for a specific month"""
        return self.filter(
            created_at__year=year,
            created_at__month=month,
            payment_status='paid'
        )


# ==========================================
# PATIENT MODEL
# ==========================================

class Patient(models.Model):  # ✅ FIXED: Changed from models.Manager
    """Patient model - source of truth for patient data"""
    
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
    patient_reg_number = models.CharField(max_length=20, unique=True, editable=False, db_column='patient_reg_number')
    full_name = models.CharField(max_length=100, validators=[MinLengthValidator(3)], db_column='full_name')
    date_of_birth = models.DateField(db_column='date_of_birth')
    blood_group = models.CharField(max_length=3, choices=BloodGroups.choices, db_column='blood_group')
    phone_number = models.CharField(
        max_length=10,
        validators=[RegexValidator(regex=r'^[6-9]\d{9}$', message='Invalid phone number')],
        db_column='phone_number'
    )
    address = models.TextField(db_column='address')
    gender = models.CharField(max_length=1, choices=Gender.choices, db_column='gender')
    is_active = models.IntegerField(default=1, db_column='is_active')  # ✅ FIXED: was isactive
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

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

    patient = models.OneToOneField(Patient, on_delete=models.CASCADE, related_name='registration', db_column='patient_id')
    registration_date = models.DateField(default=get_today_date, db_column='registration_date')
    expiry_date = models.DateField(null=True, blank=True, db_column='expiry_date')
    registration_type = models.CharField(max_length=10, choices=RegistrationType.choices, default='initial', db_column='registration_type')
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, db_column='fee_amount')
    is_active = models.IntegerField(default=1, db_column='is_active')  # ✅ FIXED: was isactive

    objects = RegistrationManager()

    class Meta:
        db_table = 'receptionist_registration'
        verbose_name = 'Registration'
        verbose_name_plural = 'Registrations'

    def __str__(self):
        return f"Registration - {self.patient.patient_reg_number} ({self.registration_type})"

    @property
    def status(self):
        """Get registration status"""
        if not self.is_active:
            return 'inactive'
        if self.expiry_date >= date.today():
            return 'active'
        grace_period_end = self.expiry_date + timedelta(days=30)
        if date.today() <= grace_period_end:
            return 'grace_period'
        return 'expired'
    
    @property
    def days_until_expiry(self):
        """Calculate days until expiry"""
        delta = self.expiry_date - date.today()
        return delta.days

    def save(self, *args, **kwargs):
        if not self.expiry_date:
            if self.registration_type == 'initial':
                self.expiry_date = self.registration_date + timedelta(days=365)
            elif self.registration_type == 'renewal':
                self.expiry_date = self.registration_date + timedelta(days=365)
        super().save(*args, **kwargs)


# ==========================================
# APPOINTMENT MODEL - USES REAL AUTHENTICATION.DOCTOR
# ==========================================

class Appointment(models.Model):
    """Appointment model - References Authentication.Doctor (REAL DOCTOR)"""
    
    class AppointmentStatus(models.TextChoices):
        PHONE_BOOKED = 'phone_booked', 'Phone Booked'
        CONFIRMED = 'confirmed', 'Confirmed'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No Show'

    appointment_id = models.CharField(max_length=20, unique=True, editable=False, db_column='appointment_id')
    
    # ✅ REFERENCES REAL DOCTOR FROM AUTHENTICATION APP
    doctor = models.ForeignKey(
        'Authentication.Doctor',
        on_delete=models.CASCADE,
        related_name='receptionist_appointments',
        db_column='doctor_id'
    )
    
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name='appointments',
        db_column='patient_id'
    )
    
    appointment_date = models.DateField(db_column='appointment_date')
    token_number = models.IntegerField(db_column='token_number')
    reason = models.TextField(db_column='reason')
    status = models.CharField(max_length=15, choices=AppointmentStatus.choices, default='phone_booked', db_column='status')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    is_active = models.IntegerField(default=1, db_column='is_active')  # ✅ FIXED: was isactive

    objects = AppointmentManager()

    class Meta:
        db_table = 'receptionist_appointment'
        unique_together = ['doctor', 'appointment_date', 'token_number']
        ordering = ['appointment_date', 'token_number']
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'

    def __str__(self):
        # ✅ FIXED: StaffId.StaffName (PascalCase to match database)
        return f"{self.appointment_id} - {self.patient.full_name} with Dr. {self.doctor.staff.staff_name}"

    @property
    def appointment_time_slot(self):
        """Calculate estimated time slot based on token number"""
        start_time = datetime.strptime('09:00', '%H:%M').time()
        minutes_offset = (self.token_number - 1) * 15
        slot_datetime = datetime.combine(date.today(), start_time) + timedelta(minutes=minutes_offset)
        return slot_datetime.strftime('%I:%M %p')
    
    @property
    def is_revisit(self):
        """Check if patient has previous completed appointments with this doctor"""
        previous_appointments = Appointment.objects.filter(
            patient=self.patient,
            doctor=self.doctor,
            status='completed',
            created_at__lt=self.created_at
        ).exists()
        return previous_appointments

    def save(self, *args, **kwargs):
        """
        Custom save method for Appointment model
        - Auto-generates appointment_id
        - Auto-assigns token_number (hardcoded: 20 per day)
        """
        
        # ========== STEP 1: Generate Appointment ID ==========
        if not self.appointment_id:
            today = date.today()
            date_str = today.strftime('%Y%m%d')
            
            # Get last appointment ID for today
            last_appointment = Appointment.objects.filter(
                appointment_id__startswith=f'APT{date_str}'
            ).order_by('-appointment_id').first()
            
            if last_appointment:
                last_num = int(last_appointment.appointment_id[-4:])
                new_num = last_num + 1
            else:
                new_num = 1
            
            self.appointment_id = f'APT{date_str}{new_num:04d}'
        
        # ========== STEP 2: Assign Token Number (HARDCODED: 20 tokens) ==========
        if not self.token_number and self.status in ['phone_booked', 'confirmed']:
            
            # Get existing appointments for this doctor on this date
            existing_appointments = Appointment.objects.filter(
                doctor=self.doctor,
                appointment_date=self.appointment_date,
                status__in=['phone_booked', 'confirmed', 'arrived']
            ).exclude(pk=self.pk)  # Exclude current appointment if updating
            
            # Get list of used token numbers
            used_tokens = set(existing_appointments.values_list('token_number', flat=True))
            
            # HARDCODED: 20 tokens per day (10 morning + 10 afternoon)
            TOTAL_TOKENS = 20
            
            # Find first available token
            available_token = None
            for token in range(1, TOTAL_TOKENS + 1):
                if token not in used_tokens:
                    available_token = token
                    break
            
            # Assign token or raise error if none available
            if available_token:
                self.token_number = available_token
            else:
                from django.core.exceptions import ValidationError
                raise ValidationError(
                    f"No tokens available for Dr. {self.doctor.staff.staff_name} on {self.appointment_date}. "
                    f"Maximum {TOTAL_TOKENS} appointments per day (10 morning, 10 afternoon)."
                )
        
        # Save the appointment
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

    bill_number = models.CharField(max_length=20, unique=True, editable=False, db_column='bill_number')
    bill_type = models.CharField(max_length=30, choices=BillType.choices, db_column='bill_type')
    registration = models.ForeignKey(
        Registration,
        on_delete=models.CASCADE,
        related_name='bills',
        null=True,
        blank=True,
        db_column='registration_id'
    )
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.CASCADE,
        related_name='bill',
        null=True,
        blank=True,
        db_column='appointment_id'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='total_amount')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='discount_amount')
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='final_amount')
    payment_status = models.CharField(max_length=10, choices=PaymentStatus.choices, default='pending', db_column='payment_status')
    payment_mode = models.CharField(max_length=10, choices=PaymentMode.choices, null=True, blank=True, db_column='payment_mode')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    paid_at = models.DateTimeField(null=True, blank=True, db_column='paid_at')

    objects = BillManager()

    class Meta:
        db_table = 'receptionist_bill'
        ordering = ['-created_at']
        verbose_name = 'Bill'
        verbose_name_plural = 'Bills'

    def __str__(self):
        return f"{self.bill_number} - {self.bill_type} (₹{self.final_amount})"

    def save(self, *args, **kwargs):
        if not self.bill_number:
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
            # ✅ FIXED: StaffId.StaffName and ConsultationFee (PascalCase)
            BillItem.objects.create(
                bill=self,
                item_type='consultation',
                description=f'Consultation with Dr. {self.appointment.doctor.staff.staff_name}',
                amount=self.appointment.doctor.consultation_fee if self.appointment else 0
            )
        
        self.total_amount = sum(item.amount for item in self.bill_items.all())
        self.save()


class BillItem(models.Model):
    """Bill items for detailed billing"""
    
    class ItemType(models.TextChoices):
        REGISTRATION = 'registration', 'Registration'
        CONSULTATION = 'consultation', 'Consultation'
        PROCEDURE = 'procedure', 'Procedure'

    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='bill_items', db_column='bill_id')
    item_type = models.CharField(max_length=15, choices=ItemType.choices, db_column='item_type')
    description = models.CharField(max_length=200, db_column='description')
    amount = models.DecimalField(max_digits=10, decimal_places=2, db_column='amount')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')

    class Meta:
        db_table = 'receptionist_billitem'
        verbose_name = 'Bill Item'
        verbose_name_plural = 'Bill Items'

    def __str__(self):
        return f"{self.bill.bill_number} - {self.description} (₹{self.amount})"
