from django.shortcuts import render
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
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
    # Search and filter
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['consultation']
    search_fields = ['prescription_id']
