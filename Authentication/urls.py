# Authentication/urls.py
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from . import views

# Router for ViewSets
router = DefaultRouter()
router.register(r'staff', views.StaffView, basename='staff')
router.register(r'doctors', views.DoctorView, basename='doctor')
router.register(r'departments', views.DepartmentView, basename='department')
router.register(r'specializations', views.SpecializationView, basename='specialization')

# Combine router URLs with auth endpoints
urlpatterns = [
    # Authentication endpoints
    path('signup/', views.SignUpView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('staff-login/', views.StaffLoginView.as_view(), name='staff-login'),
    
    # Include all router URLs
    path('', include(router.urls)),
]
