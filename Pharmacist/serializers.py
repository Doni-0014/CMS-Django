from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from datetime import date
from .models import MedicineCategory, Medicine, Bill, BillMedicine, PharmacySales

class MedicineCategorySerializer(serializers.ModelSerializer):
    """Medicine category with essential validations"""
    s_no = serializers.IntegerField(read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    medicine_count = serializers.IntegerField(source='medicines.count', read_only=True)
    
    class Meta:
        model = MedicineCategory
        fields = [
            'category_id', 's_no', 'category_name', 'description', 
            'is_active', 'medicine_count', 'created_by_name', 'created_at'
        ]
        read_only_fields = ['category_id', 's_no', 'created_at']
    
    def validate_category_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Category name must have at least 3 characters")
        return value.title().strip()
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return MedicineCategory.objects.create(**validated_data)

class MedicineSerializer(serializers.ModelSerializer):
    """Medicine with comprehensive validations"""
    s_no = serializers.IntegerField(read_only=True)
    category_name = serializers.CharField(source='category.category_name', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = Medicine
        fields = [
            'medicine_id', 's_no', 'category', 'category_name', 'medicine_code', 
            'medicine_name', 'generic_name', 'company_name', 'quantity', 'price',
            'low_stock_threshold', 'batch_number', 'manufacturing_date', 'expiry_date',
            'patient_reg_number', 'patient_name', 'patient_phone', 'prescribed_by_doctor',
            'is_active', 'total_sold', 'total_revenue', 'is_low_stock', 'is_expiring_soon',
            'created_by_name', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'medicine_id', 's_no', 'total_sold', 'total_revenue', 'created_at', 'updated_at'
        ]
    
    def validate_medicine_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Medicine name must have at least 3 characters")
        return value.title().strip()
    
    def validate_medicine_code(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Medicine code must have at least 3 characters")
        return value.upper().strip()
    
    def validate_expiry_date(self, value):
        if value <= date.today():
            raise serializers.ValidationError("Expiry date must be in the future")
        return value
    
    def validate_manufacturing_date(self, value):
        if value >= date.today():
            raise serializers.ValidationError("Manufacturing date cannot be in the future")
        return value
    
    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be positive")
        if value > 50000:
            raise serializers.ValidationError("Price cannot exceed ₹50,000")
        return value
    
    def validate_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative")
        if value > 9999:
            raise serializers.ValidationError("Quantity cannot exceed 9,999")
        return value
    
    def validate_patient_phone(self, value):
        if value and (not value.isdigit() or len(value) != 10 or value[0] not in '6789'):
            raise serializers.ValidationError("Phone number must be 10 digits starting with 6, 7, 8, or 9")
        return value
    
    def validate(self, attrs):
        manufacturing_date = attrs.get('manufacturing_date')
        expiry_date = attrs.get('expiry_date')
        
        if manufacturing_date and expiry_date and manufacturing_date >= expiry_date:
            raise serializers.ValidationError({
                'expiry_date': 'Expiry date must be after manufacturing date'
            })
        
        return attrs
    
    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
            validated_data['updated_by'] = request.user
        return Medicine.objects.create(**validated_data)
    
    def update(self, instance, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['updated_by'] = request.user
        
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance

class MedicineListSerializer(serializers.ModelSerializer):
    """Simplified medicine for list views"""
    s_no = serializers.IntegerField(read_only=True)
    category_name = serializers.CharField(source='category.category_name', read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    is_expiring_soon = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Medicine
        fields = [
            'medicine_id', 's_no', 'medicine_code', 'medicine_name', 
            'category_name', 'quantity', 'price', 'expiry_date',
            'is_active', 'is_low_stock', 'is_expiring_soon'
        ]

class BillMedicineSerializer(serializers.ModelSerializer):
    """Bill medicine items with validations"""
    medicine_name = serializers.CharField(source='medicine.medicine_name', read_only=True)
    medicine_s_no = serializers.IntegerField(source='medicine.s_no', read_only=True)
    
    class Meta:
        model = BillMedicine
        fields = [
            'id', 'medicine', 'medicine_name', 'medicine_s_no',
            'prescribed_quantity', 'dispensed_quantity', 'dosage_instructions',
            'frequency', 'duration', 'unit_price', 'total_price', 
            'discount_percent', 'final_amount', 'doctor_approved', 'doctor_notes'
        ]
        read_only_fields = ['total_price', 'final_amount']
    
    def validate_dispensed_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Dispensed quantity must be positive")
        return value
    
    def validate_prescribed_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Prescribed quantity must be positive")
        return value
    
    def validate_unit_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Unit price must be positive")
        return value
    
    def validate_discount_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("Discount percent must be between 0-100")
        return value
    
    def validate(self, attrs):
        prescribed_qty = attrs.get('prescribed_quantity')
        dispensed_qty = attrs.get('dispensed_quantity')
        
        if prescribed_qty and dispensed_qty and dispensed_qty > prescribed_qty:
            raise serializers.ValidationError({
                'dispensed_quantity': 'Cannot dispense more than prescribed'
            })
        
        return attrs

class BillSerializer(serializers.ModelSerializer):
    """Complete bill with workflow validations"""
    bill_medicines = BillMedicineSerializer(many=True)
    pharmacist_name = serializers.CharField(source='pharmacist.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='prescribing_doctor.get_full_name', read_only=True)
    
    class Meta:
        model = Bill
        fields = [
            'bill_id', 'bill_number', 'patient_reg_number', 'patient_name',
            'patient_phone', 'patient_dob', 'prescribing_doctor', 'doctor_name',
            'pharmacist', 'pharmacist_name', 'doctor_verification_status',
            'bill_medicines', 'subtotal', 'tax_amount', 'discount_amount',
            'total_amount', 'payment_status', 'payment_method', 'paid_amount',
            'created_at', 'doctor_verified_at', 'paid_at'
        ]
        read_only_fields = [
            'bill_id', 'bill_number', 'pharmacist', 'subtotal', 'total_amount',
            'created_at', 'doctor_verified_at', 'paid_at'
        ]
    
    def validate_patient_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Patient name must have at least 3 characters")
        return value.title().strip()
    
    def validate_patient_phone(self, value):
        if not value.isdigit() or len(value) != 10 or value[0] not in '6789':
            raise serializers.ValidationError("Phone number must be 10 digits starting with 6, 7, 8, or 9")
        return value
    
    def validate_patient_reg_number(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Patient registration number must be at least 3 characters")
        return value.upper().strip()
    
    def validate_paid_amount(self, value):
        if value < 0:
            raise serializers.ValidationError("Paid amount cannot be negative")
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        bill_medicines_data = validated_data.pop('bill_medicines')
        
        # Set pharmacist from request user
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['pharmacist'] = request.user
        
        # Create bill
        bill = Bill.objects.create(**validated_data)
        
        subtotal = 0
        
        # Create bill medicines with stock validation
        for medicine_data in bill_medicines_data:
            medicine = medicine_data['medicine']
            dispensed_qty = medicine_data['dispensed_quantity']
            
            # Stock validation
            if medicine.quantity < dispensed_qty:
                raise serializers.ValidationError({
                    'stock_error': f"Insufficient stock for {medicine.medicine_name}. "
                                 f"Available: {medicine.quantity}, Required: {dispensed_qty}"
                })
            
            # Set defaults if not provided
            medicine_data.setdefault('unit_price', medicine.price)
            
            # Create bill medicine item
            bill_medicine = BillMedicine.objects.create(bill=bill, **medicine_data)
            subtotal += bill_medicine.final_amount
        
        # Calculate totals
        tax_rate = 0.18  # 18% GST
        bill.subtotal = subtotal
        bill.tax_amount = subtotal * tax_rate
        bill.total_amount = bill.subtotal + bill.tax_amount - bill.discount_amount
        bill.save()
        
        return bill

class BillListSerializer(serializers.ModelSerializer):
    """Simplified bill for list views"""
    pharmacist_name = serializers.CharField(source='pharmacist.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='prescribing_doctor.get_full_name', read_only=True)
    medicine_count = serializers.IntegerField(source='bill_medicines.count', read_only=True)
    
    class Meta:
        model = Bill
        fields = [
            'bill_id', 'bill_number', 'patient_name', 'patient_reg_number',
            'pharmacist_name', 'doctor_name', 'total_amount', 'payment_status',
            'medicine_count', 'created_at'
        ]

class PharmacySalesSerializer(serializers.ModelSerializer):
    """Sales tracking with essential analytics"""
    s_no = serializers.IntegerField(read_only=True)
    bill_number = serializers.CharField(source='bill.bill_number', read_only=True)
    pharmacist_name = serializers.CharField(source='pharmacist.get_full_name', read_only=True)
    doctor_name = serializers.CharField(source='prescribing_doctor.get_full_name', read_only=True)
    
    class Meta:
        model = PharmacySales
        fields = [
            'sales_id', 's_no', 'bill_number', 'patient_name',
            'pharmacist_name', 'doctor_name', 'total_amount', 
            'payment_method', 'total_items', 'sale_date', 'created_at'
        ]
        read_only_fields = ['sales_id', 's_no', 'sale_date', 'created_at']

class PharmacySalesListSerializer(serializers.ModelSerializer):
    """Simplified sales for admin dashboards"""
    s_no = serializers.IntegerField(read_only=True)
    bill_number = serializers.CharField(source='bill.bill_number', read_only=True)
    pharmacist_name = serializers.CharField(source='pharmacist.get_full_name', read_only=True)
    
    class Meta:
        model = PharmacySales
        fields = [
            'sales_id', 's_no', 'bill_number', 'patient_name',
            'pharmacist_name', 'total_amount', 'payment_method', 'sale_date'
        ]

# Utility serializers
class PharmacistUserSerializer(serializers.ModelSerializer):
    """User info for JWT integration"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'full_name', 'is_active']

class DoctorListSerializer(serializers.ModelSerializer):
    """Doctor list for prescriptions"""
    full_name = serializers.CharField(source='get_full_name', read_only=True)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'full_name', 'email']

# Search serializers
class MedicineSearchSerializer(serializers.Serializer):
    """Medicine search parameters"""
    search_term = serializers.CharField(max_length=100, required=False)
    search_by = serializers.ChoiceField(
        choices=['s_no', 'medicine_code', 'medicine_name', 'patient_reg_number'],
        default='medicine_name'
    )
    category = serializers.CharField(max_length=100, required=False)
    low_stock_only = serializers.BooleanField(default=False)
    expiring_soon_only = serializers.BooleanField(default=False)

class BillSearchSerializer(serializers.Serializer):
    """Bill search parameters"""
    search_term = serializers.CharField(max_length=100, required=False)
    search_by = serializers.ChoiceField(
        choices=['bill_number', 'patient_name', 'patient_reg_number'],
        default='patient_name'
    )
    payment_status = serializers.ChoiceField(
        choices=[('', 'All')] + Bill.PAYMENT_STATUS_CHOICES,
        required=False
    )
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)
