from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    # Admin panel
    path('admin/', admin.site.urls),
    
    # JWT Authentication endpoints (centralized)
    path('api/auth/', include([
        path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    ])),
    
    # App-specific API endpoints
    path('api/authentication/', include('Authentication.urls')),  # NEW - Staff, Doctor management
    path('api/receptionist/', include('Receptionist.urls')),      # Patient, Appointment, Registration
    path('api/doctor/', include('Doctor.urls')),                  # NEW - Consultation, Prescriptions
    path('api/pharmacist/', include('Pharmacist.urls')),          # Medicine, Bills, Sales
]

# Why:

# Centralized JWT auth at /api/auth/

# All apps under /api/ prefix for clean API structure

# Each app has its own namespace for organization