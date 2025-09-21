from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, RegexValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
import uuid
from datetime import date

# Essential validator for Indian phone numbers
phone_validator = RegexValidator(
    regex=r'^[6-9]\d{9}$',
    message="Phone number must be exactly 10 digits and start with 6, 7, 8, or 9"
)

class MedicineCategory(models.Model):
    """Medicine categories for organization"""
    category_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    s_no = models.PositiveIntegerField(unique=True, editable=False, db_index=True)
    
    category_name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='categories_created')
    
    class Meta:
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
    """Core medicine model with essential validations"""
    medicine_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    s_no = models.PositiveIntegerField(unique=True, editable=False, db_index=True)
    
    category = models.ForeignKey(MedicineCategory, on_delete=models.CASCADE, related_name='medicines')
    
    # Essential medicine info
    medicine_code = models.CharField(max_length=20, unique=True)
    medicine_name = models.CharField(max_length=100)
    generic_name = models.CharField(max_length=100)
    company_name = models.CharField(max_length=100)
    
    # Stock and pricing
    quantity = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    low_stock_threshold = models.PositiveIntegerField(default=10)
    
    # Batch info
    batch_number = models.CharField(max_length=50)
    manufacturing_date = models.DateField()
    expiry_date = models.DateField()
    
    # Patient info (optional for prescription tracking)
    patient_reg_number = models.CharField(max_length=20, blank=True, null=True)
    patient_name = models.CharField(max_length=100, blank=True, null=True)
    patient_phone = models.CharField(max_length=10, validators=[phone_validator], blank=True, null=True)
    
    # Doctor and status
    prescribed_by_doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='prescribed_medicines')
    is_active = models.BooleanField(default=True)
    
    # Sales tracking for admin
    total_sold = models.PositiveIntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='medicines_created')
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='medicines_updated')
    
    class Meta:
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
    """Pharmacy billing with workflow"""
    bill_id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    bill_number = models.CharField(max_length=20, unique=True, editable=False)
    
    # Patient info
    patient_reg_number = models.CharField(max_length=20)
    patient_name = models.CharField(max_length=100)
    patient_phone = models.CharField(max_length=10, validators=[phone_validator])
    patient_dob = models.DateField()
    
    # Staff
    prescribing_doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescribed_bills')
    pharmacist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pharmacy_bills')
    
    # Amounts
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Payment workflow
    PAYMENT_STATUS_CHOICES = [
        ('PENDING_VERIFICATION', 'Pending Doctor Verification'),
        ('PAYMENT_PENDING', 'Payment Pending'),
        ('PAID', 'Paid'),
        ('CANCELLED', 'Cancelled')
    ]
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING_VERIFICATION')
    
    PAYMENT_METHOD_CHOICES = [
        ('CASH', 'Cash'),
        ('CARD', 'Card'),
        ('UPI', 'UPI'),
    ]
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHOD_CHOICES, blank=True, null=True)
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Workflow tracking
    doctor_verification_status = models.BooleanField(default=False)
    is_reported_to_admin = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    doctor_verified_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
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
            self.is_reported_to_admin = True
            
            # Auto-create sales record
            PharmacySales.create_from_bill(self)
        
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

class BillMedicine(models.Model):
    """Medicines in each bill"""
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='bill_medicines')
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE, related_name='bill_items')
    
    # Quantities
    prescribed_quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    dispensed_quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    
    # Instructions
    dosage_instructions = models.CharField(max_length=200)
    frequency = models.CharField(max_length=50)
    duration = models.CharField(max_length=50)
    
    # Pricing
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    
    # Doctor approval
    doctor_approved = models.BooleanField(default=False)
    doctor_notes = models.TextField(blank=True)
    
    class Meta:
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
    bill = models.OneToOneField(Bill, on_delete=models.CASCADE, related_name='pharmacy_sale')
    
    # Key info (denormalized for fast queries)
    patient_name = models.CharField(max_length=100)
    pharmacist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales_handled')
    prescribing_doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescription_sales')
    
    # Financial summary
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=15, choices=Bill.PAYMENT_METHOD_CHOICES)
    total_items = models.PositiveIntegerField(default=0)
    
    # Date tracking
    sale_date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
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
