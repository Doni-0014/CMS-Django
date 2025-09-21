# Receptionist/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PatientViewSet, DoctorViewSet, RegistrationViewSet,
    AppointmentViewSet, BillViewSet, AdminReportsViewSet
)

# Create router and register viewsets
router = DefaultRouter()
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'registrations', RegistrationViewSet, basename='registration')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'bills', BillViewSet, basename='bill')
router.register(r'admin', AdminReportsViewSet, basename='admin-reports')

# URL patterns
urlpatterns = [
    path('api/', include(router.urls)),
]
