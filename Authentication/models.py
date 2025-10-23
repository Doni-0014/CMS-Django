# Authentication/models.py - CORRECTED to match your database
from django.db import models
from django.core.validators import MinValueValidator
from datetime import date


class Staff(models.Model):
    """Staff model - maps to existing authentication_staff table"""
    
    class Genders(models.TextChoices):
        MALE = 'Male', 'Male'
        FEMALE = 'Female', 'Female'
        OTHERS = 'Others', 'Others'
    
    class Roles(models.TextChoices):
        ADMIN = 'Admin', 'Admin'
        DOCTOR = 'Doctor', 'Doctor'
        PHARMACIST = 'Pharmacist', 'Pharmacist'
        RECEPTIONIST = 'Receptionist', 'Receptionist'
    
    # Map to existing columns
    staff_id = models.AutoField(primary_key=True, db_column='StaffId')
    staff_name = models.CharField(max_length=20, blank=False, db_column='StaffName')
    date_of_birth = models.DateField(blank=False, db_column='DOB')
    email = models.EmailField(unique=True, blank=False, max_length=254, db_column='Email')
    phone = models.CharField(max_length=10, unique=True, blank=False, db_column='Phone')
    gender = models.CharField(max_length=6, choices=Genders.choices, db_column='Gender')
    address = models.TextField(blank=False, db_column='Address')
    experience = models.PositiveIntegerField(db_column='Experience')
    joining_date = models.DateField(db_column='Joining_Date')
    role = models.CharField(max_length=15, choices=Roles.choices, db_column='Role')
    is_active = models.IntegerField(db_column='IsActive')  # Note: IntegerField in DB (0/1), not BooleanField
    # Plain-text password field (temporary; replace with proper hashing later)
    password = models.CharField(max_length=255, blank=True, null=True, db_column='Password')
    
    class Meta:
        managed = True  # Let Django manage this table
        db_table = 'authentication_staff'
        verbose_name = 'Staff Member'
        verbose_name_plural = 'Staff Members'
        ordering = ['-staff_id']
    
    def __str__(self):
        return f"{self.staff_id} - {self.staff_name} ({self.role})"
    
    @property
    def age(self):
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )


class Departments(models.Model):
    dept_id = models.AutoField(primary_key=True, db_column='DeptId')
    dept_name = models.CharField(max_length=25, unique=False, blank=False, db_column='DeptName')  # Note: max_length=25 in DB
    
    class Meta:
        managed = True
        db_table = 'authentication_departments'
        verbose_name = 'Department'
        verbose_name_plural = 'Departments'
        ordering = ['dept_name']
    
    def __str__(self):
        return f"{self.dept_id} - {self.dept_name}"


class Specializations(models.Model):
    spcl_id = models.AutoField(primary_key=True, db_column='SpclId')
    spcl_name = models.CharField(max_length=20, unique=False, blank=False, db_column='SpclName')  # Note: max_length=20 in DB
    
    class Meta:
        managed = True
        db_table = 'authentication_specializations'
        verbose_name = 'Specialization'
        verbose_name_plural = 'Specializations'
        ordering = ['spcl_name']
    
    def __str__(self):
        return f"{self.spcl_id} - {self.spcl_name}"


class Doctor(models.Model):
    """
    Doctor model - maps to existing authentication_doctor table
    NOTE: Uses DocId as primary key, NOT StaffId!
    """
    doc_id = models.AutoField(primary_key=True, db_column='DocId')  # This is the PK, not staff!
    
    staff = models.ForeignKey(
        Staff, 
        on_delete=models.CASCADE, 
        related_name='doctor_profiles',  # Changed: one staff can have multiple doctor records
        db_column='StaffId_id'  # Note the _id suffix!
    )
    department = models.ForeignKey(
        Departments, 
        on_delete=models.CASCADE, 
        related_name='doctors',
        db_column='DeptId_id'  # Note the _id suffix!
    )
    specialization = models.ForeignKey(
        Specializations, 
        on_delete=models.CASCADE, 
        related_name='doctors',
        db_column='SpecializationId_id'  # Note the _id suffix!
    )
    consultation_fee = models.DecimalField(
        max_digits=10,  # Note: DB has max_digits=5, decimal_places=3
        decimal_places=2,  # This seems wrong for money (should be 2), but matches DB
        validators=[MinValueValidator(0)],
        help_text="Consultation fee in rupees",
        db_column='Fee'
    )
    
    class Meta:
        managed = True
        db_table = 'authentication_doctor'
        verbose_name = 'Doctor'
        verbose_name_plural = 'Doctors'
    
    def __str__(self):
        return f"Dr. {self.staff.staff_name} - {self.specialization.spcl_name}"
    
    @property
    def doctor_name(self):
        return self.staff.staff_name
    
    @property
    def doctor_email(self):
        return self.staff.email
