from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.authtoken.models import Token
from rest_framework import permissions,status, viewsets
from .serializers import SignUpSerializer,LoginSerializer,DepartmentSerializer,DoctorSerializer,StaffSerializer,SpecializationSerializer
from .models import Specializations,Staff,Departments,Doctor
from django.contrib.auth import authenticate

class Home(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

def get_tokens(user):
    refresh=RefreshToken.for_user(user)
    return{
        'refresh':str(refresh),
        'access':str(refresh.access_token)
    }

class SignUpView(APIView):
    permission_classes=[permissions.AllowAny]
    def post(self,request):
        serializer=SignUpSerializer(data=request.data)
        if serializer.is_valid():
            user=serializer.save()
            token=get_tokens(user)
            return Response({
                "user_id": user.id,
                "username":user.username,
                "token":token,
                "role":user.groups.all()[0].id if user.groups.exists() else None
            },status = status.HTTP_201_CREATED)
        else:
            res = {'status': status.HTTP_400_BAD_REQUEST,'data':serializer.errors}
            return Response (res,status=status.HTTP_400_BAD_REQUEST)
        
class LoginView(APIView):
    permission_classes=[permissions.AllowAny]
    def post(self,request):
        serializer=LoginSerializer(data=request.data)
        if serializer.is_valid():
            username=serializer.validated_data['username']
            password=serializer.validated_data['password']
            user=authenticate(request,username=username,password=password)
            if user is not None:
                """We are reterving the token for authenticated user."""
                token = get_tokens(user)
                response = {
                    "status": status.HTTP_200_OK,
                    "message": "success",
                    "username": user.username,
                    "role": user.groups.all()[0].id if user.groups.exists() else None,
                    "data": {
                            "Token" : token
                            }
                    }
                return Response(response, status = status.HTTP_200_OK)
            else :
                response = {
                "status": status.HTTP_401_UNAUTHORIZED,
                "message": "Invalid Email or Password",
                }
                return Response(response, status = status.HTTP_401_UNAUTHORIZED)
        response = {
            "status": status.HTTP_400_BAD_REQUEST,
            "message": "bad request",
            "data":serializer.errors
            }
        return Response(response, status = status.HTTP_400_BAD_REQUEST)
    
class StaffView(viewsets.ModelViewSet):
    permission_classes=[permissions.AllowAny]
    queryset=Staff.objects.all()
    serializer_class=StaffSerializer

class SpecializationView(viewsets.ModelViewSet):
    queryset=Staff.objects.all()
    serializer_class=SpecializationSerializer

class DepartmentView(viewsets.ModelViewSet):
    queryset=Departments.objects.all()
    serializer_class=DepartmentSerializer

class DoctorView(viewsets.ModelViewSet):
    permission_classes=[permissions.AllowAny]
    queryset=Doctor.objects.all()
    serializer_class=DoctorSerializer
