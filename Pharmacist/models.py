# Pharmacist/models.py
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid
from datetime import date
from decimal import Decimal

# Import from other apps for cross-app integration
from Authentication.models import Doctor as AuthDoctor
from Receptionist.models import Patient as ReceptionistPatient
from Doctor.models import MedicinePrescription

# Essential validator for Indian phone numbers
phone_validator = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message="Phone number must be exactly 10 digits and start with 6, 7, 8, or 9"
)


class MedicineCategory(models.Model):
    """Medicine categories for organization"""
    category_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    s_no = models.PositiveIntegerField(unique=True, editable=False, db_index=True)
    
    category_name = models.CharField(max_length=100, unique=True, db_column='category_name')
    description = models.TextField(blank=True, db_column='description')
    is_active = models.IntegerField(default=1, db_column='is_active')  # Match DB integer type
    
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories_created', db_column='created_by_id')
    
    class Meta:
        db_table = 'pharmacist_medicinecategory'
        ordering = ['s_no']
        verbose_name_plural = "Medicine Categories"
    
    def save(self, *args, **kwargs):
        if not self.s_no:
            last_category = MedicineCategory.objects.order_by('-s_no').first()
            self.s_no = (last_category.s_no + 1) if last_category else 1
        super().save(*args, **kwargs)
    
    def clean(self):
        if self.category_name and len(self.category_name.strip()) < 3:
            raise ValidationError({'category_name': 'Category name must have at least 3 characters'})
    
    def __str__(self):
        return f"CAT{self.s_no:03d} - {self.category_name}"


class Medicine(models.Model):
    """Core medicine model - INVENTORY ONLY (no patient/doctor info)"""
    medicine_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    s_no = models.PositiveIntegerField(unique=True, editable=False, db_index=True)
    
    category = models.ForeignKey(MedicineCategory, on_delete=models.CASCADE, related_name='medicines', db_column='category_id')
    
    # Essential medicine info
    medicine_code = models.CharField(max_length=20, unique=True, db_column='medicine_code')
    medicine_name = models.CharField(max_length=100, db_column='medicine_name')
    generic_name = models.CharField(max_length=100, db_column='generic_name')
    company_name = models.CharField(max_length=100, db_column='company_name')
    
    # Stock and pricing
    quantity = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)], db_column='quantity')
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)], db_column='price')
    low_stock_threshold = models.PositiveIntegerField(default=10, db_column='low_stock_threshold')
    
    # Batch info
    batch_number = models.CharField(max_length=50, db_column='batch_number')
    manufacturing_date = models.DateField(db_column='manufacturing_date')
    expiry_date = models.DateField(db_column='expiry_date')
    
    # DEPRECATED: Keep in DB for backward compatibility but DON'T use in forms
    # These fields now belong in Bill model (when medicine is dispensed)
    patient_reg_number = models.CharField(
        max_length=20, 
        blank=True, 
        null=True, 
        db_column='patient_reg_number',
        editable=False,  # Hide from forms
        help_text="DEPRECATED - Use Bill.patient instead"
    )
    patient_name = models.CharField(
        max_length=100, 
        blank=True, 
        null=True, 
        db_column='patient_name',
        editable=False,  # Hide from forms
        help_text="DEPRECATED - Use Bill.patient instead"
    )
    patient_phone = models.CharField(
        max_length=10, 
        validators=[phone_validator], 
        blank=True, 
        null=True, 
        db_column='patient_phone',
        editable=False,  # Hide from forms
        help_text="DEPRECATED - Use Bill.patient instead"
    )
    prescribed_by_doctor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='prescribed_medicines',
        db_column='prescribed_by_doctor_id',
        editable=False,  # Hide from forms
        help_text="DEPRECATED - Use Bill.prescribing_doctor instead"
    )
    
    is_active = models.IntegerField(default=1, db_column='is_active')
    
    # Sales tracking for admin
    total_sold = models.PositiveIntegerField(default=0, db_column='total_sold', editable=False)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0, db_column='total_revenue', editable=False)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medicines_created', db_column='created_by_id')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='medicines_updated', db_column='updated_by_id')
    
    class Meta:
        db_table = 'pharmacist_medicine'
        ordering = ['s_no']
        indexes = [
            models.Index(fields=['s_no']),
            models.Index(fields=['medicine_code']),
            models.Index(fields=['expiry_date']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.s_no:
            last_medicine = Medicine.objects.order_by('-s_no').first()
            self.s_no = (last_medicine.s_no + 1) if last_medicine else 1
        super().save(*args, **kwargs)
    
    def clean(self):
        # Essential business validations
        if self.expiry_date and self.expiry_date <= date.today():
            raise ValidationError({'expiry_date': 'Expiry date must be in the future'})
        
        if self.manufacturing_date and self.expiry_date and self.manufacturing_date >= self.expiry_date:
            raise ValidationError({'expiry_date': 'Expiry date must be after manufacturing date'})
        
        if self.price and self.price > 50000:
            raise ValidationError({'price': 'Price cannot exceed ₹50,000'})
        
        if self.quantity and self.quantity > 9999:
            raise ValidationError({'quantity': 'Quantity cannot exceed 9,999'})
        
        # Field length validations
        if len(self.medicine_name.strip()) < 3:
            raise ValidationError({'medicine_name': 'Medicine name must have at least 3 characters'})
        
        if len(self.medicine_code.strip()) < 3:
            raise ValidationError({'medicine_code': 'Medicine code must have at least 3 characters'})
    
    def __str__(self):
        return f"MED{self.s_no:06d} - {self.medicine_name}"
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_threshold
    
    @property
    def is_expiring_soon(self):
        return (self.expiry_date - date.today()).days <= 30


class Bill(models.Model):
    """Pharmacy billing with workflow (INTEGRATED)"""
    bill_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    bill_number = models.CharField(max_length=20, unique=True, editable=False, db_column='bill_number')
    
    # INTEGRATED: Link to Receptionist.Patient
    patient = models.ForeignKey(
        ReceptionistPatient,
        on_delete=models.CASCADE,
        related_name='pharmacy_bills',
        null=True,
        blank=True,
        db_column='patient_id',
        help_text="Patient from Receptionist app"
    )
    
    # Keep old patient fields for backward compatibility
    patient_reg_number = models.CharField(max_length=20, db_column='patient_reg_number')
    patient_name = models.CharField(max_length=100, db_column='patient_name')
    patient_phone = models.CharField(max_length=10, validators=[phone_validator], db_column='patient_phone')
    patient_dob = models.DateField(db_column='patient_dob')
    
    # INTEGRATED: Links to Authentication.Doctor
    prescribing_doctor = models.ForeignKey(
        AuthDoctor,
        on_delete=models.CASCADE,
        related_name='prescribed_bills',
        null=True,
        blank=True,
        db_column='prescribing_doctor_id',
        help_text="Doctor who prescribed from Authentication app"
    )
    
    # INTEGRATED: Link to Doctor app prescription
    prescription = models.ForeignKey(
        MedicinePrescription,
        on_delete=models.SET_NULL,
        related_name='pharmacy_bills',
        null=True,
        blank=True,
        db_column='prescription_id',
        help_text="Link to doctor's prescription"
    )
    
    pharmacist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pharmacy_bills', db_column='pharmacist_id')
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='subtotal')
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='tax_amount')
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='discount_amount')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='total_amount')
    
    # Payment workflow (Using TextChoices for modern Django)
    class PaymentStatus(models.TextChoices):
        PENDING_VERIFICATION = 'PENDING_VERIFICATION', 'Pending Doctor Verification'
        PAYMENT_PENDING = 'PAYMENT_PENDING', 'Payment Pending'
        PAID = 'PAID', 'Paid'
        CANCELLED = 'CANCELLED', 'Cancelled'
    
    payment_status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default='PENDING_VERIFICATION',
        db_column='payment_status'
    )
    
    class PaymentMethod(models.TextChoices):
        CASH = 'CASH', 'Cash'
        CARD = 'CARD', 'Card'
        UPI = 'UPI', 'UPI'
    
    payment_method = models.CharField(
        max_length=15,
        choices=PaymentMethod.choices,
        blank=True,
        null=True,
        db_column='payment_method'
    )
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_column='paid_amount')
    
    # Workflow tracking
    doctor_verification_status = models.IntegerField(default=0, db_column='doctor_verification_status')  # Match DB integer
    is_reported_to_admin = models.IntegerField(default=0, db_column='is_reported_to_admin')  # Match DB integer
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    doctor_verified_at = models.DateTimeField(null=True, blank=True, db_column='doctor_verified_at')
    paid_at = models.DateTimeField(null=True, blank=True, db_column='paid_at')
    
    # Keep old PAYMENT_STATUS_CHOICES for serializer backward compatibility
    PAYMENT_STATUS_CHOICES = PaymentStatus.choices
    PAYMENT_METHOD_CHOICES = PaymentMethod.choices
    
    class Meta:
        db_table = 'pharmacist_bill'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['bill_number']),
            models.Index(fields=['patient_reg_number']),
        ]
    
    def save(self, *args, **kwargs):
        # Auto-generate bill number
        if not self.bill_number:
            last_bill = Bill.objects.order_by('-created_at').first()
            num = int(last_bill.bill_number.split('BILL')[1]) + 1 if last_bill else 1
            self.bill_number = f"BILL{num:06d}"
        
        # Workflow status updates
        if self.payment_status == 'PAID' and not self.paid_at:
            self.paid_at = timezone.now()
            self.is_reported_to_admin = 1
        
        super().save(*args, **kwargs)
    
    def clean(self):
        if len(self.patient_name.strip()) < 3:
            raise ValidationError({'patient_name': 'Patient name must have at least 3 characters'})
        
        if self.total_amount < 0:
            raise ValidationError({'total_amount': 'Total amount cannot be negative'})
        
        if self.paid_amount > self.total_amount:
            raise ValidationError({'paid_amount': 'Paid amount cannot exceed total amount'})
    
    def __str__(self):
        return f"{self.bill_number} - {self.patient_name} - ₹{self.total_amount}"
    
    @property
    def patient_full_name(self):
        """Get patient name from Receptionist app if linked"""
        return self.patient.full_name if self.patient else self.patient_name
    
    @property
    def doctor_full_name(self):
        """Get doctor name from Authentication app if linked"""
        return self.prescribing_doctor.doctor_name if self.prescribing_doctor else 'N/A'


class BillMedicine(models.Model):
    """Medicines in each bill"""
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='bill_medicines', db_column='bill_id')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='bill_items', db_column='medicine_id')
    
    # Quantities
    prescribed_quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], db_column='prescribed_quantity')
    dispensed_quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)], db_column='dispensed_quantity')
    
    # Instructions
    dosage_instructions = models.CharField(max_length=200, db_column='dosage_instructions')
    frequency = models.CharField(max_length=50, db_column='frequency')
    duration = models.CharField(max_length=50, db_column='duration')
    
    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, db_column='unit_price')
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False, db_column='total_price')
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column='discount_percent')
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False, db_column='final_amount')
    
    # Doctor approval
    doctor_approved = models.IntegerField(default=0, db_column='doctor_approved')  # Match DB integer
    doctor_notes = models.TextField(blank=True, db_column='doctor_notes')
    
    class Meta:
        db_table = 'pharmacist_billmedicine'
        unique_together = ['bill', 'medicine']
    
    def save(self, *args, **kwargs):
        # Auto-calculate amounts
        self.total_price = self.dispensed_quantity * self.unit_price
        discount_amount = (self.total_price * self.discount_percent) / 100
        self.final_amount = self.total_price - discount_amount
        
        super().save(*args, **kwargs)
    
    def clean(self):
        if self.dispensed_quantity > self.prescribed_quantity:
            raise ValidationError({'dispensed_quantity': 'Cannot dispense more than prescribed'})
        
        if self.unit_price <= 0:
            raise ValidationError({'unit_price': 'Unit price must be positive'})
        
        if self.discount_percent < 0 or self.discount_percent > 100:
            raise ValidationError({'discount_percent': 'Discount must be between 0-100%'})
    
    def __str__(self):
        return f"{self.medicine.medicine_name} x {self.dispensed_quantity}"


class PharmacySales(models.Model):
    """Sales tracking for admin reports - auto-created when bills are paid"""
    sales_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    s_no = models.PositiveIntegerField(unique=True, editable=False, db_index=True)
    
    # Link to bill
    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name='pharmacy_sale', db_column='bill_id')
    
    # Key info (denormalized for fast queries)
    patient_name = models.CharField(max_length=100, db_column='patient_name')
    pharmacist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales_handled', db_column='pharmacist_id')
    
    # INTEGRATED: Link to Authentication.Doctor
    prescribing_doctor = models.ForeignKey(
        AuthDoctor,
        on_delete=models.CASCADE,
        related_name='prescription_sales',
        null=True,
        blank=True,
        db_column='prescribing_doctor_id'
    )
    
    # Financial summary
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, db_column='total_amount')
    payment_method = models.CharField(max_length=15, choices=Bill.PaymentMethod.choices, db_column='payment_method')
    total_items = models.PositiveIntegerField(default=0, db_column='total_items')
    
    # Date tracking
    sale_date = models.DateField(auto_now_add=True, db_column='sale_date')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    
    class Meta:
        db_table = 'pharmacist_sales'
        ordering = ['-sale_date']
        indexes = [
            models.Index(fields=['s_no']),
            models.Index(fields=['sale_date']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.s_no:
            last_sale = PharmacySales.objects.order_by('-s_no').first()
            self.s_no = (last_sale.s_no + 1) if last_sale else 1
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"SALES{self.s_no:06d} - {self.patient_name} - ₹{self.total_amount}"
    
    @classmethod
    def create_from_bill(cls, bill):
        """Auto-create sales record from paid bill"""
        if hasattr(bill, 'pharmacy_sale'):
            return bill.pharmacy_sale
        
        total_items = bill.bill_medicines.aggregate(
            total=models.Sum('dispensed_quantity')
        )['total'] or 0
        
        return cls.objects.create(
            bill=bill,
            patient_name=bill.patient_name,
            pharmacist=bill.pharmacist,
            prescribing_doctor=bill.prescribing_doctor,
            total_amount=bill.total_amount,
            payment_method=bill.payment_method,
            total_items=total_items
        )


# Signal to auto-create sales records
@receiver(post_save, sender=Bill)
def create_sales_record(sender, instance, **kwargs):
    if instance.payment_status == 'PAID' and not hasattr(instance, 'pharmacy_sale'):
        PharmacySales.create_from_bill(instance)
