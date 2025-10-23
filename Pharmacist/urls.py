# Pharmacist/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
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

urlpatterns = [
    # JWT Authentication endpoints
    path('auth/', include([
        path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
        path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    ])),
    
    # API endpoints - include all router URLs
    path('', include(router.urls)),
    
    # # Additional custom endpoints (if needed)
    # path('api/test/', views.UtilityViewSet.as_view({'get': 'system_stats'}), name='test-endpoint'),
]
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include('Pharmacist.urls')),
# ]
