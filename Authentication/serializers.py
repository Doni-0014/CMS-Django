from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User,Group
from .models import Specializations,Staff,Departments,Doctor
from datetime import date
from serializers import DoctorSerializer
import re

pattern_name=r'^[A-Za-z]+(?: [A-Za-z]+)*$'
pattern_email=r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'

class SignUpSerializer(serializers.ModelSerializer):
    group_name=serializers.CharField(write_only=True,required=False)
    def create(self, validated_data):
        group_name=validated_data.pop("group_name",None)
        validated_data['password']=make_password(validated_data.get('password'))
        user=super(SignUpSerializer,self).create(validated_data)
        if group_name:
            group,_=Group.objects.get_or_create(name=group_name)
            user.groups.add(group)
        return user
    class Meta:
        model=User
        fields=['username','password','group_name']

class LoginSerializer(serializers.ModelSerializer):
    username = serializers.CharField()
    class Meta:
        model = User
        fields = ['username', 'password']

class StaffSerializer(serializers.ModelSerializer):
    doc=DoctorSerializer()
    class Meta:
        model= Staff
        fields='__all__'

    def create(self, validated_data):
        if self.role=='Doctor':
            doc_data=validated_data.pop("Doc")
            doc,_=Doctor.objects.get_or_create(**doc_data)
            staff=Staff.objects.create(Doctor=doc,**validated_data)
            return staff


    def validate_StaffName(self,value):
        if not re.match(pattern_name,value):
            raise serializers.ValidationError("Name must contains letters, . , ' ' ")
        elif len(value)<3:
            raise serializers.ValidationError("Name must be atleast 3 characters")
        return value
    def validate_DOB(self,value):
        dob=value
        td = date.today()
        age= 0
        if dob:
            age=td.year-dob.year-((td.month, td.day) < (dob.month, dob.day))
            if self.Role!='Doctor':
                if age<18:
                    raise serializers.ValidationError("Age must be grater than 18")
            elif age<23:
                raise serializers.ValidationError("Age must be grater than 23")
            elif age>60:
                raise serializers.ValidationError("Age cant be greater than 60")    
            
            return value
    def validate_Email(self,value):
        if not re.match(pattern_email,value):
             raise serializers.ValidationError("Invalide email")
        return value
    def validate_Phone(self,value):
        if len(value)!=10:
            raise serializers.ValidationError("Phone number must be 10 digits")
        elif not value.isdigit():
            raise serializers.ValidationError("Phone number must not contain letters")
    def validate_Experience(self,value):
        if self.Role=='Doctor':
            if value>value-23:
                raise serializers.ValidationError("Invalid experience")
        elif value>value-13:
            raise serializers.ValidationError("Invalid experience")
 
class SpecializationSerializer(serializers.ModelSerializer):
    class Meta:
        model=Specializations
        fields='__all__'
    def validate_SpclName(self,value):
        if not re.match(pattern_name,value):
            raise serializers.ValidationError("Specialization name must contains letters, . , ' ' ")
        elif len(value)<5:
            raise serializers.ValidationError("Specialization Name must be atleast 5 characters")
        return value
    
class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model=Departments
        fields='__all__'
    def validate_DeptName(self,value):
        if not re.match(pattern_name,value):
            raise serializers.ValidationError("Department name must contains letters, . , ' ' ")
        elif len(value)<5:
            raise serializers.ValidationError("Department Name must be atleast 5 characters")
        return value
    
class DoctorSerializer(serializers.ModelSerializer):
    staff=StaffSerializer()
    dept=DepartmentSerializer()
    spcl=SpecializationSerializer()
    class Meta:
        model=Doctor
        fields=["DocId","staff","dept","spcl","fee"]
    def validate_fee(self,value):
        if not value<0:
            raise serializers.ValidationError("Fee should not be negative")
        