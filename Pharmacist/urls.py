from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
    TokenBlacklistView
)
from . import views
from django.contrib import admin

# Create router for ViewSets
router = DefaultRouter()
router.register(r'categories', views.MedicineCategoryViewSet, basename='medicinecategory')
router.register(r'medicines', views.MedicineViewSet, basename='medicine')
router.register(r'bills', views.BillViewSet, basename='bill')
router.register(r'bill-medicines', views.BillMedicineViewSet, basename='billmedicine')
router.register(r'dashboard', views.PharmacyDashboardViewSet, basename='dashboard')
router.register(r'utilities', views.UtilityViewSet, basename='utilities')

app_name = 'pharmacist'

urlpatterns = [
    # JWT Authentication endpoints
    path('auth/', include([
        path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
        path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
        path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
        path('token/blacklist/', TokenBlacklistView.as_view(), name='token_blacklist'),
    ])),
    
    # API endpoints - include all router URLs
    path('api/', include(router.urls)),
    
    # # Additional custom endpoints (if needed)
    # path('api/test/', views.UtilityViewSet.as_view({'get': 'system_stats'}), name='test-endpoint'),
]
# urlpatterns = [
#     path('admin/', admin.site.urls),
#     path('', include('Pharmacist.urls')),
# ]
