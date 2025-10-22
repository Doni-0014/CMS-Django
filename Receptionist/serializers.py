# Receptionist/serializers.py

from rest_framework import serializers
from django.core.exceptions import ValidationError
from datetime import date, datetime, timedelta
from .models import Patient, Registration, Appointment, Bill, BillItem
from Authentication.models import Doctor
from Authentication.serializers import DoctorSerializer  # If you need nested serialization
class PatientSerializer(serializers.ModelSerializer):
    """Patient serializer with dd-mm-yyyy date format and validations"""
    
    date_of_birth = serializers.CharField(write_only=True)  # Accept dd-mm-yyyy format
    date_of_birth_formatted = serializers.SerializerMethodField(read_only=True)
    age = serializers.ReadOnlyField()
    is_senior_citizen = serializers.ReadOnlyField()
    registration_status = serializers.ReadOnlyField()
    
    class Meta:
        model = Patient
        fields = [
            'id', 'patient_reg_number', 'full_name', 'date_of_birth', 
            'date_of_birth_formatted', 'blood_group', 'phone_number', 
            'address', 'gender', 'is_active', 'age', 'is_senior_citizen',
            'registration_status', 'created_at', 'updated_at'
        ]
        read_only_fields = ['patient_reg_number', 'created_at', 'updated_at']
    
    def get_date_of_birth_formatted(self, obj):
        """Return date in dd-mm-yyyy format for frontend"""
        return obj.date_of_birth.strftime('%d-%m-%Y')
    
    def validate_full_name(self, value):
        """Name should have at least three characters"""
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Name should have at least three characters")
        return value.strip()
    
    def validate_phone_number(self, value):
        """Phone number should have 10 digits"""
        if not value.isdigit() or len(value) != 10:
            raise serializers.ValidationError("Phone number should have 10 digits")
        return value
    
    def validate_date_of_birth(self, value):
        """Validate and convert dd-mm-yyyy format to date object"""
        try:
            # Parse dd-mm-yyyy format
            date_obj = datetime.strptime(value, '%d-%m-%Y').date()
            
            # Check if date is in future
            if date_obj > date.today():
                raise serializers.ValidationError("Date of birth cannot be in the future")
            
            return date_obj
        except ValueError:
            raise serializers.ValidationError("Give the date in the correct format dd-mm-yyyy")
    
    def update(self, instance, validated_data):
        """Custom update validation - prevent name editing if active appointments"""
        if 'full_name' in validated_data and not instance.can_edit_name:
            raise serializers.ValidationError({
                'full_name': 'Cannot edit name when patient has active or future appointments'
            })
        return super().update(instance, validated_data)

class PatientSearchSerializer(serializers.Serializer):
    """Serializer for patient search functionality"""
    
    query = serializers.CharField(max_length=100, required=True)
    search_type = serializers.ChoiceField(
        choices=['registration_number', 'phone', 'name', 'dob'],
        default='registration_number'
    )
    
    def validate_query(self):
        search_type = self.initial_data.get('search_type', 'registration_number')
        query = self.initial_data.get('query', '')
        
        if search_type == 'phone' and (not query.isdigit() or len(query) != 10):
            raise serializers.ValidationError("Invalid phone number format")
        
        if search_type == 'dob':
            try:
                datetime.strptime(query, '%d-%m-%Y')
            except ValueError:
                raise serializers.ValidationError("Date should be in dd-mm-yyyy format")
        
        return query

class DoctorSerializer(serializers.ModelSerializer):
    available_tokens_today = serializers.SerializerMethodField()
    
    def get_available_tokens_today(self, obj):
        """Calculate available tokens for today"""
        from datetime import date
        today = date.today()
        booked_today = obj.doctor_appointments.filter(
            appointment_date=today
        ).count()
        return max(0, obj.daily_patient_limit - booked_today)
    
    class Meta:
        model = Doctor
        fields = [
            'id', 'doctor_id', 'full_name', 'specialization',
            'consultation_fee', 'daily_patient_limit', 
            'available_tokens_today', 'is_available'
        ]


# Receptionist/serializers.py

class AppointmentSerializer(serializers.ModelSerializer):
    """Receptionist appointment creation with auto token assignment"""
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    doctor_name = serializers.CharField(source='doctor.full_name', read_only=True)
    appointment_date = serializers.CharField(write_only=True)  # Accept dd-mm-yyyy
    appointment_date_formatted = serializers.SerializerMethodField(read_only=True)
    appointment_time_slot = serializers.ReadOnlyField()
    is_revisit = serializers.ReadOnlyField()
    
    class Meta:
        model = Appointment
        fields = [
            'id', 'appointment_id', 'patient', 'patient_name', 'doctor', 'doctor_name',
            'appointment_date', 'appointment_date_formatted',
            'token_number', 'reason', 'status', 'appointment_time_slot',
            'is_revisit', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['appointment_id', 'token_number']

    def get_appointment_date_formatted(self, obj):
        """Return appointment date in dd-mm-yyyy format"""
        if obj.appointment_date:
            return obj.appointment_date.strftime('%d-%m-%Y')
        return None
    
    def create(self, validated_data):
        """Receptionist creates appointment → Token auto-assigned"""
        # Convert date format
        date_str = validated_data.pop('appointment_date')
        try:
            appointment_date = datetime.strptime(date_str, '%d-%m-%Y').date()
        except ValueError:
            raise serializers.ValidationError({'appointment_date': 'Invalid date format. Use dd-mm-yyyy'})
        
        validated_data['appointment_date'] = appointment_date
        
        # Create appointment - token will be auto-assigned in save()
        appointment = Appointment(**validated_data)
        appointment.save()  # This triggers token assignment
        return appointment

class AppointmentStatusUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating appointment status"""
    
    class Meta:
        model = Appointment
        fields = ['status']
    
    def validate_status(self, value):
        """Validate status transitions"""
        current_status = self.instance.status if self.instance else None
        
        # Define allowed transitions
        allowed_transitions = {
            'phone_booked': ['confirmed', 'no_show', 'cancelled'],
            'confirmed': ['completed', 'no_show', 'cancelled'],
            'completed': [],  # Cannot change from completed
            'no_show': [],    # Cannot change from no_show
            'cancelled': []   # Cannot change from cancelled
        }
        
        if current_status and value not in allowed_transitions.get(current_status, []):
            raise serializers.ValidationError(
                f"Cannot change status from {current_status} to {value}"
            )
        
        return value

class RegistrationSerializer(serializers.ModelSerializer):
    """Registration serializer"""
    
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    registration_number = serializers.SerializerMethodField()
    status = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    registration_date_formatted = serializers.SerializerMethodField()
    expiry_date_formatted = serializers.SerializerMethodField()

    def get_registration_number(self, obj):
        return f"REG{obj.id:05d}"  # e.g., REG00001, REG00002
    
    class Meta:
        model = Registration
        fields = [
            'id', 'registration_number', 'patient','patient_name', 'registration_date', 'registration_date_formatted',
            'expiry_date', 'expiry_date_formatted', 'registration_type', 
            'fee_amount', 'status', 'days_until_expiry', 'is_active'
        ]
        read_only_fields = ['registration_date', 'expiry_date']
    
    def get_registration_date_formatted(self, obj):
        return obj.registration_date.strftime('%d-%m-%Y')
    
    def get_expiry_date_formatted(self, obj):
        return obj.expiry_date.strftime('%d-%m-%Y')

class BillItemSerializer(serializers.ModelSerializer):
    """Bill item serializer"""
    
    class Meta:
        model = BillItem
        fields = ['item_type', 'description', 'amount']

class BillSerializer(serializers.ModelSerializer):
    """Bill serializer with line items"""
    
    bill_items = BillItemSerializer(many=True, read_only=True)
    appointment_details = AppointmentSerializer(source='appointment', read_only=True)
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)

    def get_patient_name(self, obj):
        # Get patient name through appointment
        if obj.appointment and obj.appointment.patient:
            return obj.appointment.patient.full_name
        return None
    
    def get_appointment_details(self, obj):
        if obj.appointment:
            return {
                'appointment_id': obj.appointment.appointment_id,
                'doctor_name': obj.appointment.doctor.full_name if obj.appointment.doctor else None,
                'appointment_date': obj.appointment.appointment_date.strftime('%d-%m-%Y') if obj.appointment.appointment_date else None,
                'token_number': obj.appointment.token_number
            }
        return None
    
    class Meta:
        model = Bill
        fields = [
            'id', 'bill_number', 'patient_name', 'appointment', 'appointment_details',
            'total_amount', 'discount_amount', 'final_amount', 
            'payment_status', 'payment_mode', 'bill_items',
            'created_at', 'paid_at'
        ]
        read_only_fields = ['bill_number', 'total_amount', 'discount_amount', 'final_amount']
    
    def update(self, instance, validated_data):
        """Handle payment status updates"""
        if 'payment_status' in validated_data and validated_data['payment_status'] == 'paid':
            instance.paid_at = datetime.now()
        
        return super().update(instance, validated_data)

class DailyCollectionSerializer(serializers.Serializer):
    """Serializer for daily collection reports"""
    
    date = serializers.DateField()
    total_bills = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    registration_fees = serializers.DecimalField(max_digits=10, decimal_places=2)
    consultation_fees = serializers.DecimalField(max_digits=10, decimal_places=2)
    op_fees = serializers.DecimalField(max_digits=10, decimal_places=2)
    discounts = serializers.DecimalField(max_digits=10, decimal_places=2)

# Custom Response Serializers for API responses
class SuccessResponseSerializer(serializers.Serializer):
    """Standard success response format"""
    status = serializers.CharField(default='success')
    message = serializers.CharField()
    data = serializers.JSONField(required=False)

class ErrorResponseSerializer(serializers.Serializer):
    """Standard error response format"""
    status = serializers.CharField(default='error')
    message = serializers.CharField()
    field = serializers.CharField(required=False)
    data = serializers.JSONField(required=False, default=None)
