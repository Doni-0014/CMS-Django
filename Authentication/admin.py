# Authentication/admin.py
from django.contrib import admin
from .models import Staff, Specializations, Doctor, Departments


@admin.register(Staff)
class StaffAdmin(admin.ModelAdmin):
    list_display = ['staff_id', 'staff_name', 'role', 'email', 'phone', 'is_active', 'joining_date']
    list_filter = ['role', 'gender', 'is_active', 'joining_date']
    search_fields = ['staff_name', 'email', 'phone']
    ordering = ['-staff_id']
    readonly_fields = ['age']
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('staff_name', 'date_of_birth', 'age', 'gender', 'email', 'phone', 'address')
        }),
        ('Professional Information', {
            'fields': ('role', 'experience', 'joining_date', 'is_active')
        }),
    )


@admin.register(Departments)
class DepartmentsAdmin(admin.ModelAdmin):
    list_display = ['dept_id', 'dept_name']  # Removed 'is_active' - doesn't exist in DB
    search_fields = ['dept_name']
    ordering = ['dept_name']


@admin.register(Specializations)
class SpecializationsAdmin(admin.ModelAdmin):
    list_display = ['spcl_id', 'spcl_name']  # Removed 'is_active' - doesn't exist in DB
    search_fields = ['spcl_name']
    ordering = ['spcl_name']


@admin.register(Doctor)
class DoctorAdmin(admin.ModelAdmin):
    list_display = ['doc_id', 'get_doctor_name', 'department', 'specialization', 'consultation_fee']  # Removed 'is_active'
    list_filter = ['department', 'specialization']  # Removed 'is_active'
    search_fields = ['staff__staff_name', 'staff__email', 'department__dept_name', 'specialization__spcl_name']
    ordering = ['doc_id']
    
    fieldsets = (
        ('Doctor Information', {
            'fields': ('staff', 'department', 'specialization')
        }),
        ('Consultation', {
            'fields': ('consultation_fee',)
        }),
    )
    
    def get_doctor_name(self, obj):
        return obj.doctor_name
    get_doctor_name.short_description = 'Doctor Name'
