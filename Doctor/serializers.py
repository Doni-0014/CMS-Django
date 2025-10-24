# Doctor/serializers.py
from rest_framework import serializers
from .models import Consultation, MedicinePrescription
from Authentication.models import Doctor
from Authentication.serializers import DoctorSerializer
from Receptionist.models import Patient, Appointment
from Receptionist.serializers import PatientSerializer, AppointmentSerializer


class ConsultationSerializer(serializers.ModelSerializer):
    # Nested serializers for read operations
    doctor_details = DoctorSerializer(source='doctor', read_only=True)
    patient_details = PatientSerializer(source='patient', read_only=True)
    appointment_details = AppointmentSerializer(source='appointment', read_only=True)
    
    class Meta:
        model = Consultation
        fields = [
            'consultation_id',
            'doctor', 'doctor_details',
            'patient', 'patient_details',
            'appointment', 'appointment_details',
            'symptoms',
            'diagnosis',
            'notes',
            'created_at',
            'is_active'
        ]
        read_only_fields = ['consultation_id', 'doctor', 'created_at']
    
    def validate_symptoms(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Symptoms must be at least 10 characters")
        return value
    
    def validate_diagnosis(self, value):
        if len(value) < 10:
            raise serializers.ValidationError("Diagnosis must be at least 10 characters")
        return value


class MedicinePrescriptionSerializer(serializers.ModelSerializer):
    # Nested consultation details
    consultation_details = ConsultationSerializer(source='consultation', read_only=True)
    
    class Meta:
        model = MedicinePrescription
        fields = [
            'prescription_id',
            'consultation', 'consultation_details',
            'medicine_name',  # FIXED: This is the correct field name!
            'dosage',
            'frequency',
            'duration_days',
            'created_at'
        ]
        read_only_fields = ['prescription_id', 'created_at']
    
    def validate_medicine_name(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Medicine name must be at least 3 characters")
        return value
    
    def validate_dosage(self, value):
        if len(value) < 2:
            raise serializers.ValidationError("Dosage must be at least 2 characters")
        return value
    
    def validate_frequency(self, value):
        if len(value) < 3:
            raise serializers.ValidationError("Frequency must be at least 3 characters")
        return value
    
    def validate_duration_days(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Duration must be positive")
        if value is not None and value > 365:
            raise serializers.ValidationError("Duration cannot exceed 365 days")
        return value
