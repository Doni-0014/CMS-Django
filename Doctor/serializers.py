from rest_framework import serializers
from .models import Consultation, MedicinePrescription

class MedicinePrescriptionSerializer(serializers.ModelSerializer):
    model = MedicinePrescription
    fields = ['prescription_id', 'consultation', 'medicine', 'dosage', 'frequency', 'duration_days', 'created_at', 'is_active']
    read_only_fields = ['prescription_id', 'created_at'] 

class ConsultationSerializer(serializers.ModelSerializer):
    medicine_prescriptions = MedicinePrescriptionSerializer(many=True, read_only=True)

    class Meta:
        model = Consultation
        fields = ['consultation_id', 'appointment', 'patient', 'doctor', 'symptoms', 'diagnosis', 'notes', 'created_at', 'is_active', 'medicine_prescriptions'],
        read_only_fields = ['consultation_id', 'created_at', 'medicine_prescriptions']