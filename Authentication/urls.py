from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'staff', views.StaffView, basename='staff')
router.register(r'doctor', views.DoctorView, basename='doctor')
router.register(r'department', views.DepartmentView, basename='department')
router.register(r'specialization', views.SpecializationView, basename='specialization')
urlpatterns = router.urls