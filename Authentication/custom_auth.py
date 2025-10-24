# Custom authentication for CMS
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from .models import Staff


class StaffTokenAuthentication(BaseAuthentication):
    """
    Custom authentication that works with the custom token format
    Token format: "staff_{staff_id}_{role}"
    """
    
    def authenticate(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if not auth_header:
            return None
            
        try:
            # Extract token from "Bearer <token>" format
            token = auth_header.split(' ')[1]
            
            # Parse custom token format: "staff_{staff_id}_{role}"
            if not token.startswith('staff_'):
                return None
                
            parts = token.split('_')
            if len(parts) != 3:
                return None
                
            staff_id = int(parts[1])
            role = parts[2]
            
            # Find staff member
            try:
                staff = Staff.objects.get(staff_id=staff_id, is_active=1)
                
                # Verify role matches
                if staff.role != role:
                    return None
                    
                # Create a simple user object for the staff member
                class StaffUser:
                    def __init__(self, staff):
                        self.staff = staff
                        self.id = staff.staff_id
                        self.email = staff.email
                        self.name = staff.staff_name
                        self.role = staff.role
                        self.is_authenticated = True
                        self.is_anonymous = False
                        
                    def __str__(self):
                        return f"StaffUser({self.name})"
                        
                return (StaffUser(staff), token)
                
            except Staff.DoesNotExist:
                return None
                
        except (ValueError, IndexError):
            return None
            
    def authenticate_header(self, request):
        return 'Bearer'

