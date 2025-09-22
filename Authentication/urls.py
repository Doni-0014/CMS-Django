from django.urls import path
from . import views


urlpatterns = [
    path('signup/',views.SignUpView.as_view()),
    path('login/',views.LoginView.as_view()),
    path('staff/',views.StaffView.as_view()),
    path('doctor/',views.DoctorView.as_view()),
    path('specializations/',views.SpecializationView.as_view()),
    path('departments/',views.DepartmentView.as_view())
    ]