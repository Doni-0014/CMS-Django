from . import views
from django.urls import path
from rest_framework.routers import DefaultRouter

router = DefaultRouter()

urlpatterns = [
    path('login/', views.LoginView.as_view()),
    path('signup/', views.SignUpView.as_view())
]
urlpatterns = router.urls