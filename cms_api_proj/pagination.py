# cms_api_proj/pagination.py
"""
Custom pagination classes for different use cases
Allows client to control page size via ?page_size=X query parameter
"""
from rest_framework.pagination import PageNumberPagination


class CustomPageNumberPagination(PageNumberPagination):
    """
    Base pagination with configurable page size
    Client can override using ?page_size=X (up to max_page_size)
    """
    page_size = 20  # Default
    page_size_query_param = 'page_size'  # Allow client to override
    max_page_size = 100  # Maximum allowed


class ReceptionistPagination(PageNumberPagination):
    """
    For Receptionist app - Patients, Appointments, Registrations
    Smaller pages for detailed review
    """
    page_size = 15  # Default for receptionist
    page_size_query_param = 'page_size'
    max_page_size = 50


class DoctorPagination(PageNumberPagination):
    """
    For Doctor app - Consultations, Prescriptions, Patient records
    """
    page_size = 15  # Default for doctor
    page_size_query_param = 'page_size'
    max_page_size = 50


class PharmacistPagination(PageNumberPagination):
    """
    For Pharmacist app - Medicine inventory, Bills, Sales
    Larger pages for bulk scanning
    """
    page_size = 30  # Default for pharmacist (inventory browsing)
    page_size_query_param = 'page_size'
    max_page_size = 100


class AdminPagination(PageNumberPagination):
    """
    For Admin dashboards and reports
    Very flexible pagination
    """
    page_size = 20  # Default
    page_size_query_param = 'page_size'
    max_page_size = 200  # Allow large exports
