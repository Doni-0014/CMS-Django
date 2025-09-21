<<<<<<< HEAD
#duplicated file

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import Doctor
from .serializers import DoctorSerializer

class DoctorViewSet(viewsets.ModelViewSet):
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    permission_classes = [IsAuthenticated]
=======
from django.shortcuts import render
from rest_framework import viewsets, filters
from .models import Consultation, MedicinePrescription
from .serializers import ConsultationSerializer, MedicinePrescriptionSerializer
# Create your views here.

class ConsultationViewSet(viewsets.ModelViewSet):
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    #permission_classes = [IsDoctor]
    #Search 
    filter_backends = [filters.SearchFilter]
    search_fields = ['consultation_id']

class MedicinePrescriptionViewSet(viewsets.ModelViewSet):
    queryset = MedicinePrescription.objects.all()
    serializer_class = MedicinePrescriptionSerializer
    # permission_classes = [IsDoctor]
    #Search 
    filter_backends = [filters.SearchFilter]
    search_fields = ['prescription_id']
>>>>>>> c7f23ddb54f0b42c7ea05877b0e8c8fbfbfa92b5
