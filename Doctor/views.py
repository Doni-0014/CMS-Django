from django.shortcuts import render
from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from .models import Consultation, MedicinePrescription
from .serializers import ConsultationSerializer, MedicinePrescriptionSerializer
from Authentication.custom_auth import StaffTokenAuthentication

class ConsultationViewSet(viewsets.ModelViewSet):
    authentication_classes = [StaffTokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Consultation.objects.all()
    serializer_class = ConsultationSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['consultation_id']

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, 'user', None)
        # If authenticated staff doctor, limit to own consultations
        try:
            staff = getattr(user, 'staff', None)
            if staff and staff.role == 'Doctor':
                from Authentication.models import Doctor as AuthDoctor
                doc = AuthDoctor.objects.filter(staff=staff).first()
                if doc:
                    return qs.filter(doctor=doc)
        except Exception:
            pass
        return qs

    def perform_create(self, serializer):
        """Attach current doctor from token; require patient and details"""
        user = getattr(self.request, 'user', None)
        staff = getattr(user, 'staff', None)
        if not staff or staff.role != 'Doctor':
            raise PermissionError('Only doctors can create consultations')
        from Authentication.models import Doctor as AuthDoctor
        doctor = AuthDoctor.objects.filter(staff=staff).first()
        serializer.save(doctor=doctor)

class MedicinePrescriptionViewSet(viewsets.ModelViewSet):
    authentication_classes = [StaffTokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = MedicinePrescription.objects.all()
    serializer_class = MedicinePrescriptionSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['consultation']
    search_fields = ['prescription_id']
