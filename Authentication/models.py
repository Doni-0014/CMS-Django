from django.db import models
from datetime import date

class Staff(models.Model):
    class Genders(models.TextChoices):
        MALE='Male'
        FEMALE='Female'
        OTHERS='Others'
    
    class Roles(models.TextChoices):
        ADMIN='Admin'
        DOCTOR='Doctor'
        PHARMACIST='Pharmacist'
        RECEPTIONIST='Receptionist'

    StaffId=models.AutoField(primary_key=True)
    StaffName=models.CharField(max_length=20,blank=False)
    DOB=models.DateField(blank=False)
    Email=models.EmailField(unique=True,blank=False)
    Phone=models.CharField(max_length=10,unique=True,blank=False)
    Gender=models.CharField(max_length=6,choices=Genders.choices)
    Address=models.TextField(max_length=100,blank=False)
    Experience=models.PositiveIntegerField(default=0)
    Joining_Date=models.DateField(default=date.today)
    Role=models.CharField(max_length=15,choices=Roles.choices)
    IsActive=models.BooleanField(default=True)

    def __str__(self):
        return f"Staff Id : {self.StaffId}, Staff Name : {self.StaffName}"

class Departments(models.Model):
    DeptId=models.AutoField(primary_key=True)
    DeptName=models.CharField(max_length=25,blank=False)

    def __str__(self):
        return self.DeptName

class Specializations(models.Model):
    SpclId=models.AutoField(primary_key=True)
    SpclName=models.CharField (max_length=20,blank=False)  

class Doctor(models.Model):
    DocId=models.AutoField(primary_key=True)
    StaffId=models.ForeignKey(Staff,on_delete=models.CASCADE,blank=False)
    DeptId=models.ForeignKey(Departments,on_delete=models.CASCADE,blank=False)
    SpecializationId=models.ForeignKey(Specializations,on_delete=models.CASCADE,blank=False)
    Fee=models.DecimalField(max_digits=5,decimal_places=3)