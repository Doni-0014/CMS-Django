# Pharmacist/services.py
"""
Business logic for pharmacy automation
"""
from django.db.models import Q
from .models import Medicine
from Doctor.models import MedicinePrescription

class PharmacyAutomationService:
    """Service class for pharmacy automation logic"""
    
    @staticmethod
    def fuzzy_search_medicine(medicine_name, threshold=0.6):
        """
        Fuzzy search for medicines in inventory
        Returns list of matching medicines with similarity scores
        """
        if not medicine_name:
            return []
        
        # Simple case-insensitive contains search
        # For production: use django-fuzzywuzzy or postgresql similarity
        medicines = Medicine.objects.filter(
            Q(medicine_name__icontains=medicine_name) |
            Q(generic_name__icontains=medicine_name),
            is_active=1
        ).values('medicine_id', 'medicine_name', 'price', 'quantity', 'expiry_date')
        
        return list(medicines)
    
    @staticmethod
    def check_stock_availability(medicine_id, required_quantity):
        """
        Check if sufficient stock is available
        Returns: (available, stock_status, available_quantity)
        """
        try:
            medicine = Medicine.objects.get(medicine_id=medicine_id)
            
            if medicine.quantity >= required_quantity:
                return True, 'sufficient', medicine.quantity
            elif medicine.quantity > 0:
                return False, 'partial', medicine.quantity
            else:
                return False, 'out_of_stock', 0
        except Medicine.DoesNotExist:
            return False, 'not_found', 0
    
    @staticmethod
    def check_medicine_expiry(medicine_id):
        """
        Check if medicine is expired or expiring soon
        Returns: (is_valid, status, days_to_expiry)
        """
        from datetime import date
        try:
            medicine = Medicine.objects.get(medicine_id=medicine_id)
            today = date.today()
            days_to_expiry = (medicine.expiry_date - today).days
            
            if days_to_expiry < 0:
                return False, 'expired', days_to_expiry
            elif days_to_expiry <= 30:
                return True, 'expiring_soon', days_to_expiry
            else:
                return True, 'valid', days_to_expiry
        except Medicine.DoesNotExist:
            return False, 'not_found', None
    
    @staticmethod
    def get_pending_prescriptions():
        """
        Get all prescriptions pending at pharmacy
        """
        return MedicinePrescription.objects.filter(
            fulfillment_status='pending'
        ).exclude(
            medicine_name=''
        ).select_related(
            'consultation__patient',
            'consultation__doctor'
        )
    
    @staticmethod
    def get_low_stock_medicines():
        """
        Get medicines below reorder threshold
        """
        from django.db.models import F
        return Medicine.objects.filter(
            quantity__lte=F('low_stock_threshold'),
            is_active=1
        ).order_by('quantity')
    
    @staticmethod
    def get_expiring_medicines(days=30):
        """
        Get medicines expiring within specified days
        """
        from datetime import date, timedelta
        threshold_date = date.today() + timedelta(days=days)
        
        return Medicine.objects.filter(
            expiry_date__lte=threshold_date,
            expiry_date__gte=date.today(),
            is_active=1
        ).order_by('expiry_date')
    
    @staticmethod
    def get_expired_medicines():
        """
        Get expired medicines that should not be dispensed
        """
        from datetime import date
        return Medicine.objects.filter(
            expiry_date__lt=date.today(),
            is_active=1
        )
