# Pharmacist/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView,
)
from .views import (
    MedicineViewSet,
    MedicineCategoryViewSet,
    BillViewSet,
    BillMedicineViewSet,
    PharmacySalesViewSet,
    PrescriptionManagementViewSet
)

router = DefaultRouter()
router.register(r'medicines', MedicineViewSet, basename='medicine')
router.register(r'categories', MedicineCategoryViewSet, basename='category')
router.register(r'bills', BillViewSet, basename='bill')
router.register(r'bill-medicines', BillMedicineViewSet, basename='bill-medicine')
router.register(r'sales', PharmacySalesViewSet, basename='sales')
router.register(r'prescriptions', PrescriptionManagementViewSet, basename='prescription-mgmt')

# ✅ FIXED - Removed duplicate JWT auth endpoints
# JWT authentication is centralized in main urls.py at /api/auth/
urlpatterns = [
    path('', include(router.urls)),
]
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include('Pharmacist.urls')),
# ]
