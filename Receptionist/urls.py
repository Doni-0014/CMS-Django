# Receptionist/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    PatientViewSet, DoctorViewSet, RegistrationViewSet,
    AppointmentViewSet, BillViewSet, AdminReportsViewSet
)
from .views import dashboard_stats, dashboard_notifications

# Create router and register viewsets
router = DefaultRouter()
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'doctors', DoctorViewSet, basename='doctor')
router.register(r'registrations', RegistrationViewSet, basename='registration')
router.register(r'appointments', AppointmentViewSet, basename='appointment')
router.register(r'bills', BillViewSet, basename='bill')
router.register(r'admin-reports', AdminReportsViewSet, basename='admin-reports')

# URL patterns - REMOVE the 'api/' prefix since main urls.py already has it
urlpatterns = [
    path('dashboard/stats/', dashboard_stats, name='dashboard-stats'),
    path('dashboard/notifications/', dashboard_notifications, name='dashboard-notifications'),
    path('', include(router.urls)),  # Changed from path('api/', ...) to path('', ...)
]
