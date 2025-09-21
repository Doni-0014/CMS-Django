#duplicated file

from rest_framework import serializers
from .models import ReceptionistProfile

class ReceptionistProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReceptionistProfile
        fields = ['id', 'user', 'phone']
