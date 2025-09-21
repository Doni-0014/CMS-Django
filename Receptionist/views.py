from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from .models import ReceptionistProfile
from .serializers import ReceptionistProfileSerializer

class ReceptionistProfileViewSet(viewsets.ModelViewSet):
    queryset = ReceptionistProfile.objects.all()
    serializer_class = ReceptionistProfileSerializer
    permission_classes = [IsAuthenticated]
