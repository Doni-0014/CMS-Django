# Receptionist/models.py

from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, MinLengthValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import date, datetime, timedelta
import calendar

# Import Doctor model from teammate's Doctor app
# from Doctor.models import Doctor

def get_today_date():
    """Return today's date - used as default for registration_date"""
    return date.today()

# Temporary Doctor model for testing - will be replaced by Doctor app later

class DoctorManager(models.Manager):
    """Manager for Doctor model"""
    
    def available_doctors(self):
        """Get all available doctors"""
        return self.filter(is_available=True)
    
class Doctor(models.Model):
    """Doctor model - contains only doctor data, no booking logic"""
    
    doctor_id = models.CharField(max_length=20, unique=True, editable=False)
    full_name = models.CharField(max_length=100)
    specialization = models.CharField(max_length=100)
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2)
    daily_patient_limit = models.IntegerField(default=20)
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = DoctorManager()
    
    def save(self, *args, **kwargs):
        if not self.doctor_id:
            last_doctor = Doctor.objects.order_by('-id').first()
            if last_doctor and last_doctor.doctor_id:
                last_number = int(last_doctor.doctor_id[3:])
                self.doctor_id = f"DOC{last_number + 1:03d}"
            else:
                self.doctor_id = "DOC001"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.doctor_id} - Dr. {self.full_name}"
    
    class Meta:
        ordering = ['full_name']

class PatientManager(models.Manager):
    """Custom manager for Patient model with admin-friendly methods"""
    
    def active_patients(self):
        return self.filter(is_active=True)
    
    def senior_citizens(self):
        """Returns patients who are 60+ years old"""
        today = date.today()
        sixty_years_ago = today.replace(year=today.year - 60)
        return self.filter(date_of_birth__lte=sixty_years_ago)
    
    def registration_expired(self):
        """Returns patients with expired registration (beyond grace period)"""
        return self.filter(registration__registration_expired=True)
    
    def registration_in_grace(self):
        """Returns patients in 7-day grace period"""
        return self.filter(registration__in_grace_period=True)

class Patient(models.Model):
    """Patient model with PAT001 format"""
    
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'), 
        ('O', 'Other')
    ]
    
    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-')
    ]
    
    # Auto-generated Patient Registration Number (PAT001 format)
    patient_reg_number = models.CharField(
        max_length=20, 
        unique=True, 
        editable=False,
        help_text="Auto-generated format: PAT001"
    )
    
    # Basic fields - validation moved to serializers
    full_name = models.CharField(
        max_length=100, 
        validators=[MinLengthValidator(3, 'Name should have at least three characters')]
    )
    def clean(self):
        """Custom model validation - runs in both admin and API"""
        super().clean()
        
        if self.full_name and len(self.full_name.strip()) < 3:
            raise ValidationError({
                'full_name': 'Name should have at least three characters'
            })
    date_of_birth = models.DateField(
        validators=[MaxValueValidator(
            limit_value=date.today,  # Note: date.today (callable), not date.today()
            message='Date of birth cannot be in the future.'
        )]
    )
    blood_group = models.CharField(max_length=3, choices=BLOOD_GROUP_CHOICES)
    phone_number = models.CharField(max_length=10)
    address = models.TextField()
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    
    # Status field for enable/disable
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = PatientManager()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['patient_reg_number']),
            models.Index(fields=['phone_number']),
            models.Index(fields=['full_name']),
            models.Index(fields=['date_of_birth']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.patient_reg_number:
            # Generate patient registration number like PAT001, PAT002, etc.
            last_patient = Patient.objects.order_by('-id').first()
            if last_patient and last_patient.patient_reg_number:
                last_number = int(last_patient.patient_reg_number[3:])  # Remove 'PAT'
                self.patient_reg_number = f"PAT{last_number + 1:03d}"
            else:
                self.patient_reg_number = "PAT001"
        super().save(*args, **kwargs)
    
    @property
    def age(self):
        """Calculate current age"""
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    @property
    def is_senior_citizen(self):
        """Check if patient is 60+ years old for discount"""
        return self.age >= 60
    
    @property
    def registration_status(self):
        """Get current registration status"""
        try:
            return self.registration.status
        except Registration.DoesNotExist:
            return 'not_registered'
    
    @property
    def can_edit_name(self):
        """Check if name can be edited (no active/future appointments)"""
        return not self.appointments.filter(
            appointment_date__gte=date.today(),
            status__in=['phone_booked', 'confirmed'],
            is_active=True
        ).exists()
    
    def __str__(self):
        return f"{self.patient_reg_number} - {self.full_name}"

class RegistrationManager(models.Manager):
    """Custom manager for Registration model"""
    
    def expired_registrations(self):
        """Get all expired registrations (beyond grace period)"""
        return self.filter(registration_expired=True)
    
    def in_grace_period(self):
        """Get registrations in 7-day grace period"""
        return self.filter(in_grace_period=True)
    
    def due_for_renewal(self):
        """Get registrations expiring in next 7 days"""
        seven_days_ahead = date.today() + timedelta(days=7)
        return self.filter(
            expiry_date__lte=seven_days_ahead,
            expiry_date__gte=date.today(),
            is_active=True
        )

class Registration(models.Model):
    """Patient registration and renewal tracking"""
    
    REGISTRATION_TYPE_CHOICES = [
        ('initial', 'Initial Registration'),
        ('renewal', 'Renewal')
    ]
    
    patient = models.OneToOneField(
        Patient, 
        on_delete=models.CASCADE,
        related_name='registration'
    )
    
    registration_date = models.DateField(default=get_today_date)
    expiry_date = models.DateField(blank=True, null=True)
    
    registration_type = models.CharField(
        max_length=10, 
        choices=REGISTRATION_TYPE_CHOICES,
        default='initial'
    )
    
    fee_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=Decimal('300.00')
    )
    
    is_active = models.BooleanField(default=True)
    
    objects = RegistrationManager()
    
    class Meta:
        ordering = ['-registration_date']
    
    def save(self, *args, **kwargs):
        # Ensure registration_date is set
        if not self.registration_date:
            from django.utils import timezone
            self.registration_date = timezone.now().date()
        
        # Calculate expiry_date if not set
        if not self.expiry_date:
            self.expiry_date = self.registration_date + timedelta(days=90)
        
        super().save(*args, **kwargs)
    
    @property
    def days_until_expiry(self):
        """Days remaining until expiry"""
        return (self.expiry_date - date.today()).days
    
    @property
    def is_expired(self):
        """Check if registration is expired (beyond grace period)"""
        if self.expiry_date is None:
            return False  # New registrations are not expired
        
        grace_end = self.expiry_date + timedelta(days=7)
        return date.today() > grace_end
    
    @property
    def days_until_expiry(self):
        """Days remaining until expiry"""
        if self.expiry_date is None:
            return 0  # Or return a sensible default
        
        return (self.expiry_date - date.today()).days
    
    @property
    def in_grace_period(self):
        """Check if in 7-day grace period"""
        if self.expiry_date is None:
            return False  # New registrations are not in grace period
        
        return (
            date.today() > self.expiry_date and 
            date.today() <= self.expiry_date + timedelta(days=7)
        )
    
    @property
    def registration_expired(self):
        """For admin queries - expired beyond grace"""
        return self.is_expired
    
    @property
    def status(self):
        """Current registration status"""
        if self.expiry_date is None:
            return 'pending'  # New registration status
        
        if self.is_expired:
            return 'expired'
        elif self.in_grace_period:
            return 'grace_period'
        else:
            return 'active'
        
    def __str__(self):
        return f"{self.patient.patient_reg_number} - {self.get_registration_type_display()}"

class AppointmentManager(models.Manager):
    """Manager for Appointment model with token assignment logic"""
    
    def get_next_token(self, doctor, appointment_date):
        """
        Get next available token for doctor on given date.
        Reuses cancelled tokens first, then increments sequentially.
        Called by receptionist when booking appointments.
        """
        from django.db.models import Max, Q
        
        # Skip Sundays
        if appointment_date.weekday() == 6:
            raise ValueError("No appointments allowed on Sundays")
        
        # Get all appointments for this doctor on this date
        appointments = self.filter(
            doctor=doctor,
            appointment_date=appointment_date
        )
        
        # Get active (non-cancelled) tokens
        active_tokens = set(appointments.exclude(status='cancelled').values_list('token_number', flat=True))
        active_tokens.discard(None)  # Remove any None values
        
        # Get cancelled tokens that can be reused
        cancelled_tokens = set(appointments.filter(status='cancelled').values_list('token_number', flat=True))
        cancelled_tokens.discard(None)
        
        # Find lowest available cancelled token to reuse
        available_cancelled = sorted(cancelled_tokens - active_tokens)
        if available_cancelled:
            return available_cancelled[0]
        
        # No cancelled tokens available, assign next sequential number
        if active_tokens:
            next_token = max(active_tokens) + 1
        else:
            next_token = 1  # First appointment of the day starts from 1
        
        # Check against doctor's daily limit
        if next_token > doctor.daily_patient_limit:
            raise ValueError(f"Dr. {doctor.full_name} has reached maximum patient limit ({doctor.daily_patient_limit}) for {appointment_date.strftime('%d-%m-%Y')}")
        
        return next_token
    
    def get_available_tokens_for_date(self, doctor, appointment_date):
        """Get remaining token slots for doctor on given date"""
        if appointment_date.weekday() == 6:  # Sunday
            return 0
        
        # Count active appointments (non-cancelled)
        active_count = self.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            is_active=True
        ).exclude(status='cancelled').count()
        
        return max(0, doctor.daily_patient_limit - active_count)
    
    def get_booked_tokens_for_date(self, doctor, appointment_date):
        """Get list of booked tokens for doctor on given date"""
        return list(self.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            is_active=True
        ).exclude(status='cancelled').values_list('token_number', flat=True).order_by('token_number'))

class Appointment(models.Model):
    """Appointment model with token system"""
    
    STATUS_CHOICES = [
        ('phone_booked', 'Phone Booked'),
        ('confirmed', 'Confirmed'),
        ('completed', 'Completed'),
        ('no_show', 'No Show'),
        ('cancelled', 'Cancelled')
    ]
    
    appointment_id = models.CharField(max_length=20, unique=True, editable=False)
    patient = models.ForeignKey(
        Patient, 
        on_delete=models.CASCADE,
        related_name='appointments'
    )
    # Reference to Doctor app's Doctor model
    doctor = models.ForeignKey(
        Doctor, 
        on_delete=models.CASCADE,
        related_name='receptionist_appointments'  # Avoid conflicts with Doctor app
    )
    
    appointment_date = models.DateField()
    token_number = models.IntegerField()
    
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=15, 
        choices=STATUS_CHOICES, 
        default='phone_booked'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    objects = AppointmentManager()
    
    class Meta:
        unique_together = ['doctor', 'appointment_date', 'token_number']
        ordering = ['appointment_date', 'token_number']
        indexes = [
            models.Index(fields=['appointment_date', 'doctor']),
            models.Index(fields=['patient', 'appointment_date']),
        ]
    
    def save(self, *args, **kwargs):
        """Auto-assign token when receptionist creates appointment"""
        
        # Auto-assign token number for new appointments
        if not self.pk and self.token_number is None:
            try:
                # Receptionist books appointment → Token gets auto-assigned
                self.token_number = Appointment.objects.get_next_token(
                    self.doctor, 
                    self.appointment_date
                )
            except ValueError as e:
                from django.core.exceptions import ValidationError
                raise ValidationError(f"Token assignment failed: {str(e)}")
        
        # Generate appointment ID if not exists
        if not self.appointment_id:
            last_appointment = Appointment.objects.order_by('-id').first()
            if last_appointment and last_appointment.appointment_id:
                last_number = int(last_appointment.appointment_id[1:])
                self.appointment_id = f"A{last_number + 1:03d}"
            else:
                self.appointment_id = "A001"
        
        super().save(*args, **kwargs)
    
    @property
    def is_revisit(self):
        """Check if this is a revisit - with null safety"""
        if (self.status in ['phone_booked'] or 
            self.patient is None or 
            self.doctor is None or 
            self.appointment_date is None):
            return False
            
        last_visit = Appointment.objects.filter(
            patient=self.patient,
            doctor=self.doctor,
            appointment_date__lt=self.appointment_date,
            appointment_date__gte=self.appointment_date - timedelta(days=10),
            status='completed'
        ).exists()
        
        return last_visit
    
    @property
    def appointment_time_slot(self):
        """Get approximate time slot based on token"""
        # Handle None values safely
        if self.token_number is None or self.appointment_date is None:
            return None  # Or return "Not assigned" if you prefer
        
        token = self.token_number
        
        if token <= 10:
            # Before lunch: 9 AM to 12:30 PM
            base_time = datetime.strptime('09:00', '%H:%M')
            slot_minutes = (token - 1) * 21  # ~21 mins per patient
            appointment_time = base_time + timedelta(minutes=slot_minutes)
            return appointment_time.strftime('%H:%M')
        elif token <= 20:
            # After lunch: 1:30 PM to 5 PM  
            base_time = datetime.strptime('13:30', '%H:%M')
            slot_minutes = (token - 11) * 21  # ~21 mins per patient
            appointment_time = base_time + timedelta(minutes=slot_minutes)
            return appointment_time.strftime('%H:%M')
        else:
            return None  # Invalid token number
    
    def __str__(self):
        return f"{self.appointment_id} - {self.patient.full_name} with Dr. {self.doctor.full_name} (Token: {self.token_number})"

class BillManager(models.Manager):
    """Custom manager for Bill model with admin reports"""
    
    def daily_collection(self, date_filter=None):
        """Get daily collection summary for admin reports"""
        if date_filter is None:
            date_filter = date.today()
            
        bills = self.filter(
            created_at__date=date_filter,
            payment_status='paid'
        )
        
        return {
            'date': date_filter,
            'total_bills': bills.count(),
            'total_amount': sum(bill.total_amount for bill in bills),
            'registration_fees': sum(
                item.amount for bill in bills 
                for item in bill.bill_items.filter(item_type='registration')
            ),
            'consultation_fees': sum(
                item.amount for bill in bills
                for item in bill.bill_items.filter(item_type='consultation')
            ),
            'op_fees': sum(
                item.amount for bill in bills
                for item in bill.bill_items.filter(item_type='op_fee')
            ),
            'discounts': sum(
                item.amount for bill in bills
                for item in bill.bill_items.filter(item_type='discount')
            ),
        }
    
    def monthly_collection(self, year, month):
        """Get monthly collection for admin dashboard"""
        start_date = date(year, month, 1)
        end_date = date(year, month, calendar.monthrange(year, month)[1])
        
        return self.filter(
            created_at__date__range=[start_date, end_date],
            payment_status='paid'
        )

class Bill(models.Model):
    """Enhanced Bill model with auto-generation support"""
    
    BILL_TYPE_CHOICES = [
        ('registration', 'Registration Only'),
        ('registration_consultation', 'Registration + Consultation'),
        ('renewal', 'Renewal Only'),
        ('renewal_consultation', 'Renewal + Consultation'),
        ('consultation', 'Consultation Only'),
    ]
    # Auto-calculate max_length with buffer
    _MAX_BILL_TYPE_LENGTH = max(len(choice[0]) for choice in BILL_TYPE_CHOICES) + 5
    
    bill_type = models.CharField(
        max_length=_MAX_BILL_TYPE_LENGTH,  # Automatically 30 (25 + 5 buffer)
        choices=BILL_TYPE_CHOICES,
        default='consultation'
    )
    
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Payment Pending'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled')
    ]
    
    bill_number = models.CharField(max_length=20, unique=True, editable=False)
    
    # Link to either registration or appointment (or both)
    registration = models.ForeignKey(
        Registration, 
        on_delete=models.CASCADE,
        related_name='bills',
        null=True, blank=True
    )
    appointment = models.OneToOneField(
        Appointment, 
        on_delete=models.CASCADE,
        related_name='bill',
        null=True, blank=True
    )
    
    # Add default values to prevent NULL errors
    total_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')  # Add default value
    )
    discount_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')  # Add default value
    )
    final_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00')  # Add default value - this fixes the error
    )
    
    payment_status = models.CharField(
        max_length=10, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='pending'
    )
    payment_mode = models.CharField(
        max_length=10, 
        choices=[('cash', 'Cash'), ('card', 'Card'), ('upi', 'UPI'), ('online', 'Online')],
        blank=True, null=True
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    
    objects = BillManager()

    def _ensure_decimal(self, value):
        """
        Convert any numeric value to Decimal for financial calculations.
        Handles both float and Decimal inputs safely.
        """
        from decimal import Decimal
        
        if isinstance(value, Decimal):
            return value
        elif isinstance(value, (int, float)):
            return Decimal(str(value))
        else:
            return Decimal('0.00')

    def save(self, *args, **kwargs):
        """Generate bill number if not exists"""
        if not self.bill_number:
            last_bill = Bill.objects.order_by('-id').first()
            if last_bill and last_bill.bill_number:
                last_number = int(last_bill.bill_number[3:])
                self.bill_number = f"REC{last_number + 1:03d}"
            else:
                self.bill_number = "REC001"
        
        # Calculate final_amount if not set
        if self.final_amount == Decimal('0.00'):
            self.final_amount = self.total_amount - self.discount_amount
        
        super().save(*args, **kwargs)
    
    def generate_bill_items(self):
        """Generate bill items based on bill type and scenario"""
        # Clear existing items
        self.bill_items.all().delete()
        
        total = self._ensure_decimal(0.00)  # Now this method exists
        discount = self._ensure_decimal(0.00)
        patient = self.get_patient()
        
        # SCENARIO 1: Registration Only
        if self.bill_type == 'registration':
            registration_fee = self._ensure_decimal(self.registration.fee_amount)
            BillItem.objects.create(
                bill=self,
                item_type='registration',
                description='Initial Registration Fee',
                amount=registration_fee
            )
            total += registration_fee
        
        # SCENARIO 2: Registration + Consultation
        elif self.bill_type == 'registration_consultation':
            # Registration fee
            registration_fee = self._ensure_decimal(self.registration.fee_amount)
            BillItem.objects.create(
                bill=self,
                item_type='registration',
                description='Initial Registration Fee',
                amount=registration_fee
            )
            total += registration_fee
            
            # OP Fee (waived for revisits and grace period)
            if not self.appointment.is_revisit and not patient.registration.in_grace_period:
                op_fee = self._ensure_decimal(200.00)
                BillItem.objects.create(
                    bill=self,
                    item_type='op_fee',
                    description='OP Fee',
                    amount=op_fee
                )
                total += op_fee
            
            # Consultation Fee
            consultation_fee = self._ensure_decimal(self.appointment.doctor.consultation_fee)
            BillItem.objects.create(
                bill=self,
                item_type='consultation',
                description=f'Consultation - Dr. {self.appointment.doctor.full_name}',
                amount=consultation_fee
            )
            total += consultation_fee
            
            # Senior Citizen Discount (20% on consultation fee only)
            if patient.is_senior_citizen:
                discount = consultation_fee * self._ensure_decimal(0.20)
                BillItem.objects.create(
                    bill=self,
                    item_type='discount',
                    description='Senior Citizen Discount (20%)',
                    amount=-discount
                )
        
        # SCENARIO 3: Renewal Only
        elif self.bill_type == 'renewal':
            renewal_fee = self._ensure_decimal(self.registration.fee_amount)
            BillItem.objects.create(
                bill=self,
                item_type='registration',
                description='Registration Renewal Fee',
                amount=renewal_fee
            )
            total += renewal_fee
        
        # SCENARIO 4: Renewal + Consultation
        elif self.bill_type == 'renewal_consultation':
            # Renewal fee
            renewal_fee = self._ensure_decimal(self.registration.fee_amount)
            BillItem.objects.create(
                bill=self,
                item_type='registration',
                description='Registration Renewal Fee',
                amount=renewal_fee
            )
            total += renewal_fee
            
            # OP Fee and Consultation (same logic as registration_consultation)
            if not self.appointment.is_revisit and not patient.registration.in_grace_period:
                op_fee = self._ensure_decimal(200.00)
                BillItem.objects.create(
                    bill=self,
                    item_type='op_fee',
                    description='OP Fee',
                    amount=op_fee
                )
                total += op_fee
            
            consultation_fee = self._ensure_decimal(self.appointment.doctor.consultation_fee)
            BillItem.objects.create(
                bill=self,
                item_type='consultation',
                description=f'Consultation - Dr. {self.appointment.doctor.full_name}',
                amount=consultation_fee
            )
            total += consultation_fee
            
            if patient.is_senior_citizen:
                discount = consultation_fee * self._ensure_decimal(0.20)
                BillItem.objects.create(
                    bill=self,
                    item_type='discount',
                    description='Senior Citizen Discount (20%)',
                    amount=-discount
                )
        
        # SCENARIO 5: Consultation Only - FIX THE REGISTRATION ACCESS
        elif self.bill_type == 'consultation':
            # Safe registration access with try-except
            try:
                has_registration = hasattr(patient, 'registration') and patient.registration
                in_grace_period = has_registration and patient.registration.in_grace_period
            except Exception:
                has_registration = False
                in_grace_period = False
            
            # OP Fee (waived for revisits and grace period)
            if not self.appointment.is_revisit and not in_grace_period:
                op_fee = self._ensure_decimal(200.00)
                BillItem.objects.create(
                    bill=self,
                    item_type='op_fee',
                    description='OP Fee',
                    amount=op_fee
                )
                total += op_fee
            
            # Consultation Fee
            consultation_fee = self._ensure_decimal(self.appointment.doctor.consultation_fee)
            BillItem.objects.create(
                bill=self,
                item_type='consultation',
                description=f'Consultation - Dr. {self.appointment.doctor.full_name}',
                amount=consultation_fee
            )
            total += consultation_fee
        
        # Update bill totals
        self.total_amount = total
        self.discount_amount = discount
        self.final_amount = total - discount
        self.save()
    
    def get_patient(self):
        """Get patient from either registration or appointment"""
        if self.registration:
            return self.registration.patient
        elif self.appointment:
            return self.appointment.patient
        return None
    
    def __str__(self):
        patient = self.get_patient()
        return f"{self.bill_number} - {patient.full_name if patient else 'Unknown'} ({self.get_bill_type_display()})"


class BillItem(models.Model):
    """Individual line items in a bill"""
    
    ITEM_TYPE_CHOICES = [
        ('registration', 'Registration Fee'),
        ('op_fee', 'OP Fee'),
        ('consultation', 'Consultation Fee'),
        ('discount', 'Discount')
    ]
    
    bill = models.ForeignKey(
        Bill, 
        on_delete=models.CASCADE,
        related_name='bill_items'
    )
    
    item_type = models.CharField(max_length=15, choices=ITEM_TYPE_CHOICES)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['item_type']
    
    def __str__(self):
        return f"{self.bill.bill_number} - {self.get_item_type_display()}: ₹{self.amount}"
