from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'consultations', views.ConsultationViewSet)
router.register(r'presctiptions/medicine', views.MedicinePrescriptionViewSet)

urlpatterns = router.urls