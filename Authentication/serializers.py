# Authentication/serializers.py
from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User, Group
from .models import Specializations, Staff, Departments, Doctor
from datetime import date
import re


# Validation patterns
pattern_name = r'^[A-Za-z]+(?: [A-Za-z]+)*$'
pattern_email = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'


def calculate_age(date_of_birth):
    """Helper function to calculate age from date of birth"""
    today = date.today()
    return today.year - date_of_birth.year - (
        (today.month, today.day) < (date_of_birth.month, date_of_birth.day)
    )


class SignUpSerializer(serializers.ModelSerializer):
    group_name = serializers.CharField(write_only=True, required=False)
    
    def create(self, validated_data):
        group_name = validated_data.pop("group_name", None)
        validated_data['password'] = make_password(validated_data.get('password'))
        user = super(SignUpSerializer, self).create(validated_data)
        if group_name:
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
        return user
    
    class Meta:
        model = User
        fields = ['username', 'password', 'group_name']


class LoginSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    
    class Meta:
        model = User
        fields = ['username', 'password']


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Departments
        fields = '__all__'
    
    def validate_dept_name(self, value):
        if not re.match(pattern_name, value):
            raise serializers.ValidationError("Department name must contain letters, '.', ' '")
        if len(value) < 3:
            raise serializers.ValidationError("Department name must be at least 3 characters")
        return value


class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Specializations
        fields = '__all__'
    
    def validate_spcl_name(self, value):
        if not re.match(pattern_name, value):
            raise serializers.ValidationError("Specialization name must contain letters, '.', ' '")
        if len(value) < 3:
            raise serializers.ValidationError("Specialization name must be at least 3 characters")
        return value


class StaffSerializer(serializers.ModelSerializer):
    age = serializers.ReadOnlyField()
    
    class Meta:
        model = Staff
        fields = '__all__'
    
    def validate_staff_name(self, value):
        if not re.match(pattern_name, value):
            raise serializers.ValidationError("Name must contain letters, '.', ' '")
        if len(value) < 3:
            raise serializers.ValidationError("Name must be at least 3 characters")
        return value
    
    def validate_date_of_birth(self, value):
        """Validate date of birth based on role"""
        if value > date.today():
            raise serializers.ValidationError("Date of birth cannot be in the future")
        
        age = calculate_age(value)
        
        # Get role from initial_data or instance
        role = None
        if hasattr(self, 'initial_data'):
            role = self.initial_data.get('role')
        elif self.instance:
            role = self.instance.role
        
        # Validate age based on role
        if role == 'Doctor':
            if age < 23:
                raise serializers.ValidationError("Doctors must be at least 23 years old (MBBS completion age)")
            if age > 65:
                raise serializers.ValidationError("Age cannot exceed 65 years")
        else:
            if age < 18:
                raise serializers.ValidationError("Staff must be at least 18 years old")
            if age > 65:
                raise serializers.ValidationError("Age cannot exceed 65 years")
        
        return value
    
    def validate_email(self, value):
        if not re.match(pattern_email, value):
            raise serializers.ValidationError("Invalid email format")
        return value
    
    def validate_phone(self, value):
        if len(value) != 10:
            raise serializers.ValidationError("Phone number must be exactly 10 digits")
        if not value.isdigit():
            raise serializers.ValidationError("Phone number must contain only digits")
        if value[0] not in '6789':
            raise serializers.ValidationError("Phone number must start with 6, 7, 8, or 9")
        return value
    
    def validate_experience(self, value):
        """Validate experience based on age and role"""
        if value < 0:
            raise serializers.ValidationError("Experience cannot be negative")
        
        # Get date_of_birth and role
        dob = None
        role = None
        
        if hasattr(self, 'initial_data'):
            dob = self.initial_data.get('date_of_birth')
            role = self.initial_data.get('role')
        elif self.instance:
            dob = self.instance.date_of_birth
            role = self.instance.role
        
        if dob:
            # Convert string to date if needed
            if isinstance(dob, str):
                from datetime import datetime
                dob = datetime.strptime(dob, '%Y-%m-%d').date()
            
            age = calculate_age(dob)
            
            # Calculate maximum possible experience
            if role == 'Doctor':
                # Doctors can work from age 23 (after MBBS)
                max_experience = age - 23
                if value > max_experience:
                    raise serializers.ValidationError(
                        f"Experience cannot exceed {max_experience} years based on age and doctor qualifications"
                    )
            else:
                # Other staff can work from age 18
                max_experience = age - 18
                if value > max_experience:
                    raise serializers.ValidationError(
                        f"Experience cannot exceed {max_experience} years based on age"
                    )
        
        return value


class DoctorSerializer(serializers.ModelSerializer):
    # Nested serializers for read operations
    staff_details = StaffSerializer(source='staff', read_only=True)
    department_details = DepartmentSerializer(source='department', read_only=True)
    specialization_details = SpecializationSerializer(source='specialization', read_only=True)
    
    # For displaying names
    doctor_name = serializers.ReadOnlyField()
    doctor_email = serializers.ReadOnlyField()
    
    class Meta:
        model = Doctor
        fields = [
            'doc_id',  # Primary key for Doctor model
            'staff', 'staff_details', 'doctor_name', 'doctor_email',
            'department', 'department_details', 
            'specialization', 'specialization_details',
            'consultation_fee'
            # REMOVED 'is_active' - field doesn't exist in Doctor table
        ]
        read_only_fields = ['doc_id', 'doctor_name', 'doctor_email']
    
    def validate_consultation_fee(self, value):
        if value < 0:
            raise serializers.ValidationError("Consultation fee cannot be negative")
        if value > 10000:
            raise serializers.ValidationError("Consultation fee cannot exceed ₹10,000")
        return value
    
    def validate(self, attrs):
        """Validate that staff has Doctor role"""
        staff = attrs.get('staff')
        
        if staff and staff.role != 'Doctor':
            raise serializers.ValidationError({
                'staff': 'Selected staff member must have Doctor role'
            })
        
        return attrs
