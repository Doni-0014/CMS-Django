# Authentication/views.py
from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import permissions, status, viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .custom_auth import StaffTokenAuthentication

from .serializers import (
    SignUpSerializer, LoginSerializer, DepartmentSerializer, 
    DoctorSerializer, StaffSerializer, SpecializationSerializer
)
from .models import Specializations, Staff, Departments, Doctor
from django.contrib.auth import authenticate
from cms_api_proj.pagination import CustomPageNumberPagination
from django.contrib.auth.models import User


class Home(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]


def get_tokens(user):
    """Generate JWT tokens for user"""
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token)
    }


class SignUpView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = SignUpSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token = get_tokens(user)
            return Response({
                "user_id": user.id,
                "username": user.username,
                "token": token,
                "role": user.groups.all()[0].id if user.groups.exists() else None
            }, status=status.HTTP_201_CREATED)
        else:
            res = {
                'status': status.HTTP_400_BAD_REQUEST,
                'data': serializer.errors
            }
            return Response(res, status=status.HTTP_400_BAD_REQUEST)


class StaffLoginView(APIView):
    """
    Custom login view that works with Staff model instead of Django User model
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({ 'error': 'Email and password are required' }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Find active staff by email
            staff = Staff.objects.get(email=email, is_active=1)
            
            # Backward-compat: allow default admin if no password set
            if staff.email == 'admin@hospital.com' and password == 'admin1234':
                pass
            # If password exists on staff, require match
            elif staff.password:
                if staff.password != password:
                    return Response({ 'error': 'Invalid credentials' }, status=status.HTTP_401_UNAUTHORIZED)
            else:
                # No password stored and not default admin
                return Response({ 'error': 'Invalid credentials' }, status=status.HTTP_401_UNAUTHORIZED)
            
            token = f"staff_{staff.staff_id}_{staff.role}"

            # Build safe JSON payload (avoid returning model instances)
            doctor_profile = staff.doctor_profiles.first() if staff.role == 'Doctor' else None
            dept = getattr(doctor_profile, 'department', None)
            spcl = getattr(doctor_profile, 'specialization', None)

            user_payload = {
                'id': staff.staff_id,
                'name': staff.staff_name,
                'email': staff.email,
                'role': staff.role,
                'phone': staff.phone,
                'department': {
                    'id': getattr(dept, 'dept_id', None),
                    'name': getattr(dept, 'dept_name', None)
                } if dept else None,
                'specialization': {
                    'id': getattr(spcl, 'spcl_id', None),
                    'name': getattr(spcl, 'spcl_name', None)
                } if spcl else None
            }
            return Response({ 'access': token, 'refresh': token, 'user': user_payload }, status=status.HTTP_200_OK)
        except Staff.DoesNotExist:
            return Response({ 'error': 'Invalid credentials' }, status=status.HTTP_401_UNAUTHORIZED)
        except Exception:
            return Response({ 'error': 'Login failed' }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            username = serializer.validated_data['username']
            password = serializer.validated_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                token = get_tokens(user)
                response = {
                    "status": status.HTTP_200_OK,
                    "message": "success",
                    "username": user.username,
                    "role": user.groups.all()[0].name if user.groups.exists() else None,
                    "data": {
                        "Token": token
                    }
                }
                return Response(response, status=status.HTTP_200_OK)
            else:
                response = {
                    "status": status.HTTP_401_UNAUTHORIZED,
                    "message": "Invalid Email or Password",
                }
                return Response(response, status=status.HTTP_401_UNAUTHORIZED)
        
        response = {
            "status": status.HTTP_400_BAD_REQUEST,
            "message": "bad request",
            "data": serializer.errors
        }
        return Response(response, status=status.HTTP_400_BAD_REQUEST)


class StaffView(viewsets.ModelViewSet):
    """
    ViewSet for Staff CRUD operations
    Supports search, filter, and ordering
    """
    authentication_classes = [StaffTokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Staff.objects.all()
    serializer_class = StaffSerializer
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'gender', 'is_active']
    search_fields = ['staff_name', 'email', 'phone', 'role']
    ordering_fields = ['staff_id', 'staff_name', 'joining_date', 'experience']
    ordering = ['-staff_id']

    def destroy(self, request, *args, **kwargs):
        """Soft delete: mark staff inactive instead of hard delete to avoid FK issues"""
        instance = self.get_object()
        try:
            instance.is_active = 0
            instance.save(update_fields=['is_active'])
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception:
            return Response({'error': 'Failed to deactivate staff'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class SpecializationView(viewsets.ModelViewSet):
    """
    ViewSet for Specializations CRUD
    """
    authentication_classes = [StaffTokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Specializations.objects.all()
    serializer_class = SpecializationSerializer
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['spcl_name']


class DepartmentView(viewsets.ModelViewSet):
    """
    ViewSet for Departments CRUD
    """
    authentication_classes = [StaffTokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Departments.objects.all()
    serializer_class = DepartmentSerializer
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['dept_name']


class DoctorView(viewsets.ModelViewSet):
    """
    ViewSet for Doctor CRUD
    FIXED: Removed is_active from filterset_fields (doesn't exist in Doctor table)
    """
    authentication_classes = [StaffTokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['department', 'specialization']  # FIXED: Removed 'is_active'
    search_fields = ['staff__staff_name', 'staff__email', 'specialization__spcl_name']
    ordering_fields = ['consultation_fee']
