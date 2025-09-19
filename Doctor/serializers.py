from rest_framework import serializers
from .models import Consultation, MedicinePrescription

class MedicinePrescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicinePrescription
        fields = ['prescription_id', 'consultation', 'medicine', 'dosage', 'frequency', 'duration_days', 'created_at', 'is_active']
        read_only_fields = ['prescription_id', 'created_at'] 

    def validate_dosage(self, value):
        if not value:
            raise serializers.ValidationError("Dosage cannot be empty!")
        if len(value.strip())<5:
            raise serializers.ValidationError("Dosage must be atleast 5 characters long!")
        return value

    def validate_frequency(self, value):
        if not value:
            raise serializers.ValidationError("Frequency cannot be empty!")
        if len(value.strip())<5:
            raise serializers.ValidationError("Frequency must be atleast 5 characters long!")
        return value
    
    def validate_duration_days(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Duration must be a positive number.")
        return value


class ConsultationSerializer(serializers.ModelSerializer):
    medicine_prescriptions = MedicinePrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = Consultation
        fields = ['consultation_id', 'appointment', 'patient', 'doctor', 'symptoms', 'diagnosis', 'notes', 'created_at', 'medicine_prescriptions']
        read_only_fields = ['consultation_id', 'created_at', 'medicine_prescriptions']

    def validate_symptoms(self, value):
        if value and len(value.strip())<5:
            raise serializers.ValidationError("Symptoms must be atleast 5 characters long!")
        return value
    
    def validate_diagnosis(self, value):
        if value and len(value.strip())<5:
            raise serializers.ValidationError("Diagnosis must be atleast 5 characters long!")
        return value
    
    def validate_notes(self, value):
        if value and len(value.strip())<5:
            raise serializers.ValidationError("Notes must be atleast 5 characters long!")
        return value