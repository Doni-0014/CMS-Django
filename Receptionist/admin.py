# Receptionist/admin.py

from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from .models import Patient, Registration, Doctor, Appointment, Bill, BillItem

class RegistrationInline(admin.StackedInline):
    """Inline form to create registration when creating patient"""
    model = Registration
    extra = 1  # Show 1 registration form
    max_num = 1  # Only allow 1 registration per patient
    can_delete = False  # Don't allow deletion of registration
    
    fields = ('registration_type', 'fee_amount', 'registration_date', 'expiry_date')
    readonly_fields = ('registration_date', 'expiry_date')
    
    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly for existing registrations"""
        if obj:  # Editing existing patient
            return self.readonly_fields + ('registration_type', 'fee_amount')
        return self.readonly_fields

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    """Patient admin with inline registration form"""
    
    list_display = ['patient_reg_number', 'full_name', 'age', 'phone_number', 'is_senior_citizen', 'registration_status', 'is_active']
    list_filter = ['is_active', 'blood_group', 'gender', 'created_at']
    search_fields = ['patient_reg_number', 'full_name', 'phone_number']
    readonly_fields = ['patient_reg_number', 'age', 'is_senior_citizen', 'registration_status', 'created_at', 'updated_at']
    
    # Add registration inline
    inlines = [RegistrationInline]
    
    fieldsets = (
        ('Patient Information', {
            'fields': ('patient_reg_number', 'full_name', 'date_of_birth', 'age', 'gender')
        }),
        ('Contact Details', {
            'fields': ('phone_number', 'address')
        }),
        ('Medical Information', {
            'fields': ('blood_group', 'is_senior_citizen')
        }),
        ('Status', {
            'fields': ('is_active', 'registration_status', 'created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Ensure registration is created when patient is saved"""
        super().save_model(request, obj, form, change)
        
        # If this is a new patient and no registration exists, create one
        if not change and not hasattr(obj, 'registration'):
            Registration.objects.create(patient=obj)

@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    """Minimal registration admin for viewing only"""
    list_display = ['patient', 'registration_type', 'fee_amount', 'registration_date', 'expiry_date', 'status', 'days_until_expiry']
    list_filter = ['registration_type', 'fee_amount', 'registration_date', 'is_active']
    search_fields = ['patient__full_name', 'patient__patient_reg_number']
    readonly_fields = ['registration_date', 'expiry_date', 'status', 'days_until_expiry']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient')
    
    # Make it mostly read-only
    def has_add_permission(self, request):
        return False  # Don't allow adding registrations separately
    
    def has_delete_permission(self, request, obj=None):
        return False  # Don't allow deletion

@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    """Doctor admin (temporary model)"""
    list_display = ['doctor_id', 'full_name', 'specialization', 'consultation_fee', 'daily_patient_limit', 'is_available']
    list_filter = ['is_available', 'specialization']
    search_fields = ['doctor_id', 'full_name', 'specialization']
    readonly_fields = ['doctor_id', 'created_at']
    
    fieldsets = (
        ('Doctor Information', {
            'fields': ('doctor_id', 'full_name', 'specialization')
        }),
        ('Consultation Details', {
            'fields': ('consultation_fee', 'daily_patient_limit', 'is_available')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    """Receptionist appointment management in admin"""
    
    list_display = ['appointment_id', 'patient', 'doctor', 'appointment_date', 'token_number', 'status', 'appointment_time_slot']
    list_filter = ['status', 'appointment_date', 'doctor', 'is_active']
    search_fields = ['appointment_id', 'patient__full_name', 'doctor__full_name']
    readonly_fields = ['appointment_id', 'token_number', 'appointment_time_slot', 'is_revisit', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Appointment Booking (Receptionist)', {
            'fields': ('patient', 'doctor', 'appointment_date', 'reason')
        }),
        ('System Generated', {
            'fields': ('appointment_id', 'token_number', 'appointment_time_slot'),
            'classes': ('collapse',)
        }),
        ('Status Management', {
            'fields': ('status', 'is_revisit', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Handle receptionist appointment booking in admin"""
        if not change:  # New appointment
            try:
                super().save_model(request, obj, form, change)
                self.message_user(request, f"Appointment {obj.appointment_id} created successfully with token #{obj.token_number}")
            except ValidationError as e:
                from django.contrib import messages
                messages.error(request, f"Error creating appointment: {e}")
        else:
            super().save_model(request, obj, form, change)

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    """Bill admin - READ ONLY (auto-generated)"""
    list_display = ['bill_number', 'get_patient_name', 'bill_type', 'total_amount', 'final_amount', 'payment_status', 'created_at']
    list_filter = ['bill_type', 'payment_status', 'payment_mode', 'created_at']
    search_fields = ['bill_number', 'registration__patient__full_name', 'appointment__patient__full_name']
    readonly_fields = ['bill_number', 'registration', 'appointment', 'bill_type', 'total_amount', 'discount_amount', 'final_amount', 'created_at']
    
    fieldsets = (
        ('Bill Information', {
            'fields': ('bill_number', 'bill_type', 'registration', 'appointment')
        }),
        ('Amount Details', {
            'fields': ('total_amount', 'discount_amount', 'final_amount')
        }),
        ('Payment Information', {
            'fields': ('payment_status', 'payment_mode', 'paid_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',)
        }),
    )
    
    def get_patient_name(self, obj):
        patient = obj.get_patient()
        return patient.full_name if patient else 'Unknown'
    get_patient_name.short_description = 'Patient'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'registration__patient', 'appointment__patient', 'appointment__doctor'
        )
    
    # DISABLE MANUAL CREATION
    def has_add_permission(self, request):
        return False  # Bills are auto-generated
    
    def has_delete_permission(self, request, obj=None):
        # Only allow deletion of unpaid bills
        if obj and obj.payment_status == 'pending':
            return True
        return False

@admin.register(BillItem)
class BillItemAdmin(admin.ModelAdmin):
    """BillItem admin - READ ONLY (auto-generated)"""
    list_display = ['bill', 'item_type', 'description', 'amount', 'created_at']
    list_filter = ['item_type', 'created_at']
    search_fields = ['bill__bill_number', 'description']
    readonly_fields = ['bill', 'item_type', 'description', 'amount', 'created_at']
    
    # DISABLE MANUAL CREATION  
    def has_add_permission(self, request):
        return False  # Bill items are auto-generated
    
    def has_delete_permission(self, request, obj=None):
        return False  # Bill items should not be manually deleted