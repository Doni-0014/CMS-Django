# Receptionist/admin.py
from django.contrib import admin
from .models import Patient, Registration, Appointment, Bill, BillItem
from Authentication.models import Doctor  # Import from Authentication


# Patient Admin
@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ['patient_reg_number', 'full_name', 'date_of_birth', 'blood_group', 'phone_number', 'is_active']
    list_filter = ['blood_group', 'gender', 'is_active', 'created_at']
    search_fields = ['patient_reg_number', 'full_name', 'phone_number']
    readonly_fields = ['patient_reg_number', 'created_at', 'updated_at']
    ordering = ['-created_at']


# Registration Admin
@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ['patient', 'registration_type', 'registration_date', 'expiry_date', 'fee_amount', 'is_active']
    list_filter = ['registration_type', 'is_active', 'registration_date']
    search_fields = ['patient__patient_reg_number', 'patient__full_name']
    readonly_fields = ['registration_date']


# Appointment Admin
@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ['appointment_id', 'patient', 'get_doctor_name', 'appointment_date', 'token_number', 'status', 'is_active']
    list_filter = ['status', 'appointment_date', 'is_active']
    search_fields = ['appointment_id', 'patient__full_name', 'patient__patient_reg_number', 'doctor__staff__staff_name']
    readonly_fields = ['appointment_id', 'created_at', 'updated_at']
    ordering = ['appointment_date', 'token_number']
    
    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.doctor_name}" if obj.doctor else "N/A"
    get_doctor_name.short_description = 'Doctor'


# Bill Admin
@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = ['bill_number', 'bill_type', 'total_amount', 'discount_amount', 'final_amount', 'payment_status', 'created_at']
    list_filter = ['bill_type', 'payment_status', 'payment_mode', 'created_at']
    search_fields = ['bill_number']
    readonly_fields = ['bill_number', 'created_at', 'paid_at']
    ordering = ['-created_at']


# BillItem Admin
@admin.register(BillItem)
class BillItemAdmin(admin.ModelAdmin):
    list_display = ['bill', 'item_type', 'description', 'amount', 'created_at']
    list_filter = ['item_type', 'created_at']
    search_fields = ['bill__bill_number', 'description']
    readonly_fields = ['created_at']


# NOTE: Don't register Doctor here - it's managed in Authentication app
# Doctor admin is in Authentication/admin.py
