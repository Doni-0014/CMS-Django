# Receptionist/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from datetime import date, datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from datetime import date, timedelta
from rest_framework.decorators import api_view
from django.db.models import Sum

from .models import Patient, Registration, Appointment, Bill, BillItem
from Authentication.models import Doctor  # Import real Doctor
from .serializers import (
    PatientSerializer, DoctorSerializer, RegistrationSerializer,
    AppointmentSerializer, BillSerializer, PatientSearchSerializer,
    AppointmentStatusUpdateSerializer, DailyCollectionSerializer,
    SuccessResponseSerializer, ErrorResponseSerializer
)

class PatientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Patient management with search functionality
    """
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    
    def get_queryset(self):
        """Filter active patients by default"""
        return Patient.objects.active_patients()
    
    @action(detail=False, methods=['post'])
    def search(self, request):
        """
        Search patients by registration number, phone, name, or DOB
        POST /api/patients/search/
        Body: {"query": "PAT001", "search_type": "registration_number"}
        """
        serializer = PatientSearchSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'status': 'error',
                'message': 'Invalid search parameters',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        query = serializer.validated_data['query']
        search_type = serializer.validated_data['search_type']
        
        # Perform search based on type
        if search_type == 'registration_number':
            patients = Patient.objects.filter(patient_reg_number__icontains=query)
        elif search_type == 'phone':
            patients = Patient.objects.filter(phone_number__icontains=query)
        elif search_type == 'name':
            patients = Patient.objects.filter(full_name__icontains=query)
        elif search_type == 'dob':
            try:
                search_date = datetime.strptime(query, '%d-%m-%Y').date()
                patients = Patient.objects.filter(date_of_birth=search_date)
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid date format. Use dd-mm-yyyy'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            patients = Patient.objects.none()
        
        if not patients.exists():
            return Response({
                'status': 'error',
                'message': 'Patient does not exist'
            }, status=status.HTTP_404_NOT_FOUND)
        
        serializer = PatientSerializer(patients, many=True)
        return Response({
            'status': 'success',
            'message': f'Found {patients.count()} patient(s)',
            'data': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """
        Disable a patient
        POST /api/patients/{id}/disable/
        """
        patient = self.get_object()
        patient.is_active = False
        patient.save()
        
        return Response({
            'status': 'success',
            'message': f'Patient {patient.patient_reg_number} disabled successfully'
        })
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """
        Enable a patient
        POST /api/patients/{id}/enable/
        """
        patient = self.get_object()
        patient.is_active = True
        patient.save()
        
        return Response({
            'status': 'success',
            'message': f'Patient {patient.patient_reg_number} enabled successfully'
        })

class DoctorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Doctor management (temporary model)
    """
    queryset = Doctor.objects.all()
    serializer_class = DoctorSerializer
    
    @action(detail=True, methods=['get'])
    def availability(self, request, pk=None):
        """
        Get doctor's token availability for a specific date
        GET /api/doctors/{id}/availability/?date=2025-09-19
        """
        doctor = self.get_object()
        date_str = request.query_params.get('date')
        
        if not date_str:
            appointment_date = date.today() + timedelta(days=1)
        else:
            try:
                appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if it's Sunday
        if appointment_date.weekday() == 6:
            return Response({
                'status': 'success',
                'message': 'No appointments on Sundays',
                'data': {
                    'date': appointment_date.strftime('%d-%m-%Y'),
                    'available_tokens': 0,
                    'is_sunday': True
                }
            })
        
        available_tokens = doctor.get_available_tokens_for_date(appointment_date)
        
        return Response({
            'status': 'success',
            'message': f'Token availability for Dr. {doctor.full_name}',
            'data': {
                'date': appointment_date.strftime('%d-%m-%Y'),
                'available_tokens': available_tokens,
                'total_limit': doctor.daily_patient_limit,
                'is_sunday': False
            }
        })

class RegistrationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Patient Registration management
    """
    queryset = Registration.objects.all()
    serializer_class = RegistrationSerializer
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """
        Get registrations expiring in next 7 days
        GET /api/registrations/expiring_soon/
        """
        expiring_registrations = Registration.objects.due_for_renewal()
        serializer = RegistrationSerializer(expiring_registrations, many=True)
        
        return Response({
            'status': 'success',
            'message': f'Found {expiring_registrations.count()} registrations expiring soon',
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def expiring(self, request):
        """Get registrations expiring soon (within 30 days)"""
        from datetime import date, timedelta
        expiry_date = date.today() + timedelta(days=30)
        
        expiring_registrations = self.queryset.filter(
            expiry_date__lte=expiry_date,  # Changed from registration_expiry_date
            expiry_date__gte=date.today()  # Changed from registration_expiry_date
        )
        
        serializer = self.get_serializer(expiring_registrations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def in_grace_period(self, request):
        """
        Get registrations currently in grace period
        GET /api/registrations/in_grace_period/
        """
        grace_registrations = Registration.objects.in_grace_period()
        serializer = RegistrationSerializer(grace_registrations, many=True)
        
        return Response({
            'status': 'success',
            'message': f'Found {grace_registrations.count()} registrations in grace period',
            'data': serializer.data
        })

class AppointmentViewSet(viewsets.ModelViewSet):
    """Receptionist appointment management with auto token assignment"""
    
    queryset = Appointment.objects.all()
    serializer_class = AppointmentSerializer
    
    @action(detail=False, methods=['get'])
    def doctor_availability(self, request):
        """
        Check doctor token availability - used by receptionist
        GET /api/appointments/doctor_availability/?doctor_id=1&date=2025-09-19
        """
        doctor_id = request.query_params.get('doctor_id')
        date_str = request.query_params.get('date')
        
        if not doctor_id:
            return Response({
                'status': 'error',
                'message': 'doctor_id parameter required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            doctor = Doctor.objects.get(id=doctor_id)
        except Doctor.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Doctor not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        if date_str:
            try:
                appointment_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            appointment_date = date.today() + timedelta(days=1)
        
        # Check if it's Sunday
        if appointment_date.weekday() == 6:
            return Response({
                'status': 'success',
                'message': 'No appointments on Sundays',
                'data': {
                    'date': appointment_date.strftime('%d-%m-%Y'),
                    'available_tokens': 0,
                    'booked_tokens': [],
                    'next_token': None,
                    'is_sunday': True
                }
            })
        
        try:
            available_tokens = Appointment.objects.get_available_tokens_for_date(doctor, appointment_date)
            booked_tokens = Appointment.objects.get_booked_tokens_for_date(doctor, appointment_date)
            next_token = Appointment.objects.get_next_token(doctor, appointment_date) if available_tokens > 0 else None
            
            return Response({
                'status': 'success',
                'message': f'Token availability for Dr. {doctor.full_name}',
                'data': {
                    'doctor_name': doctor.full_name,
                    'date': appointment_date.strftime('%d-%m-%Y'),
                    'total_limit': doctor.daily_patient_limit,
                    'available_tokens': available_tokens,
                    'booked_tokens': booked_tokens,
                    'next_token': next_token,
                    'is_sunday': False
                }
            })
        except ValueError as e:
            return Response({
                'status': 'error',
                'message': str(e),
                'data': {
                    'doctor_name': doctor.full_name,
                    'date': appointment_date.strftime('%d-%m-%Y'),
                    'available_tokens': 0,
                    'booked_tokens': Appointment.objects.get_booked_tokens_for_date(doctor, appointment_date),
                    'next_token': None,
                    'is_sunday': False
                }
            })

class BillViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Bill management with generation and payment processing
    """
    queryset = Bill.objects.all()
    serializer_class = BillSerializer
    
    @action(detail=True, methods=['post'])
    def generate_items(self, request, pk=None):
        """
        Generate bill items for an appointment
        POST /api/bills/{id}/generate_items/
        """
        bill = self.get_object()
        
        try:
            bill.generate_bill_items()
            serializer = BillSerializer(bill)
            
            return Response({
                'status': 'success',
                'message': f'Bill items generated for {bill.bill_number}',
                'data': serializer.data
            })
        except Exception as e:
            return Response({
                'status': 'error',
                'message': f'Error generating bill items: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def process_payment(self, request, pk=None):
        """
        Process bill payment
        POST /api/bills/{id}/process_payment/
        Body: {"payment_mode": "cash"}
        """
        bill = self.get_object()
        payment_mode = request.data.get('payment_mode')
        
        if payment_mode not in ['cash', 'card', 'upi', 'online']:
            return Response({
                'status': 'error',
                'message': 'Invalid payment mode'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        bill.payment_status = 'paid'
        bill.payment_mode = payment_mode
        bill.paid_at = datetime.now()
        bill.save()
        
        return Response({
            'status': 'success',
            'message': f'Payment processed for {bill.bill_number}',
            'data': {
                'bill_number': bill.bill_number,
                'final_amount': bill.final_amount,
                'payment_mode': payment_mode,
                'paid_at': bill.paid_at.strftime('%d-%m-%Y %H:%M:%S')
            }
        })
    
    @action(detail=False, methods=['post'])
    def create_from_appointment(self, request):
        """
        Create bill from appointment ID
        POST /api/bills/create_from_appointment/
        Body: {"appointment_id": 1}
        """
        appointment_id = request.data.get('appointment_id')
        
        if not appointment_id:
            return Response({
                'status': 'error',
                'message': 'appointment_id required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except Appointment.DoesNotExist:
            return Response({
                'status': 'error',
                'message': 'Appointment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check if bill already exists
        if hasattr(appointment, 'bill'):
            return Response({
                'status': 'error',
                'message': f'Bill already exists: {appointment.bill.bill_number}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create and generate bill
        bill = Bill.objects.create(appointment=appointment)
        bill.generate_bill_items()
        
        serializer = BillSerializer(bill)
        return Response({
            'status': 'success',
            'message': f'Bill {bill.bill_number} created successfully',
            'data': serializer.data
        })

class AdminReportsViewSet(viewsets.ViewSet):
    """
    ViewSet for admin reports and analytics
    """
    
    @action(detail=False, methods=['get'])
    def daily_collection(self, request):
        """
        Get daily collection report
        GET /api/admin/daily_collection/?date=2025-09-18
        """
        date_str = request.query_params.get('date')
        
        if date_str:
            try:
                report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({
                    'status': 'error',
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }, status=status.HTTP_400_BAD_REQUEST)
        else:
            report_date = date.today()
        
        collection_data = Bill.objects.daily_collection(report_date)
        
        return Response({
            'status': 'success',
            'message': f'Daily collection report for {report_date.strftime("%d-%m-%Y")}',
            'data': collection_data
        })
    
    @action(detail=False, methods=['get'])
    def monthly_collection(self, request):
        """
        Get monthly collection report
        GET /api/admin/monthly_collection/?year=2025&month=9
        """
        year = request.query_params.get('year', date.today().year)
        month = request.query_params.get('month', date.today().month)
        
        try:
            year = int(year)
            month = int(month)
        except ValueError:
            return Response({
                'status': 'error',
                'message': 'Invalid year or month'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        monthly_bills = Bill.objects.monthly_collection(year, month)
        total_amount = sum(bill.final_amount for bill in monthly_bills)
        
        return Response({
            'status': 'success',
            'message': f'Monthly collection report for {month}/{year}',
            'data': {
                'year': year,
                'month': month,
                'total_bills': monthly_bills.count(),
                'total_amount': total_amount,
                'bills': BillSerializer(monthly_bills, many=True).data
            }
        })
    
    @action(detail=False, methods=['get'])
    def dashboard_stats(self, request):
        """
        Get dashboard statistics
        GET /api/admin/dashboard_stats/
        """
        today = date.today()
        
        stats = {
            'patients': {
                'total': Patient.objects.count(),
                'active': Patient.objects.active_patients().count(),
                'senior_citizens': Patient.objects.senior_citizens().count(),
            },
            'registrations': {
                'expiring_soon': Registration.objects.due_for_renewal().count(),
                'in_grace_period': Registration.objects.in_grace_period().count(),
                'expired': Registration.objects.expired_registrations().count(),
            },
            'appointments': {
                'today': Appointment.objects.today_appointments().count(),
                'completed_today': Appointment.objects.completed_today().count(),
                'pending': Appointment.objects.active_appointments().count(),
            },
            'collections': {
                'today': Bill.objects.daily_collection(today),
            }
        }
        
        return Response({
            'status': 'success',
            'message': 'Dashboard statistics',
            'data': stats
        })

@api_view(['GET'])
def dashboard_stats(request):
    from Authentication.models import Staff
    today = date.today()
    
    # Patient counts
    patientstoday = Patient.objects.count()
    
    # Appointment counts
    appointmentstoday = Appointment.objects.filter(status__in=['confirmed', 'phonebooked']).count()
    pendingappointments = Appointment.objects.filter(status='pending').count()
    
    # Revenue
    revenuetoday = Bill.objects.filter(payment_status='paid').aggregate(total=Sum('final_amount'))['total'] or 0
    
    # Expiring registrations count
    nextweek = today + timedelta(days=7)
    expiringregistrations = Registration.objects.filter(
        expiry_date__lte=nextweek,
        expiry_date__gte=today,
        is_active=True
    ).count()
    
    # Available doctors count
    availabledoctors = Staff.objects.filter(role='Doctor', is_active=True).count()
    
    # Recent registrations with patient details (last 10)
    recent_registrations = Registration.objects.select_related('patient').order_by('-registration_date')[:10]
    registrations_data = []
    for reg in recent_registrations:
        registrations_data.append({
            'id': reg.id,
            'patient_reg_number': reg.patient.patient_reg_number,  # Changed: access through patient
            'full_name': reg.patient.full_name,  # Changed: access through patient
            'registration_date': reg.registration_date.strftime('%d-%m-%Y'),
            'registration_date_formatted': reg.registration_date.strftime('%d-%m-%Y'),
            'expiry_date': reg.expiry_date.strftime('%d-%m-%Y'),
            'expiry_date_formatted': reg.expiry_date.strftime('%d-%m-%Y'),
            'registration_status': reg.registration_status,
        })
    
    # Recent appointments (last 10)
    recent_appointments = Appointment.objects.select_related('patient', 'doctor').order_by('-created_at')[:10]
    appointments_data = []
    for apt in recent_appointments:
        appointments_data.append({
            'id': apt.id,
            'patient_name': apt.patient.full_name,
            'doctor_name': f"Dr. {apt.doctor.StaffName}" if apt.doctor else 'No doctor assigned',
            'appointment_date': apt.appointment_date.strftime('%d-%m-%Y'),
            'appointment_date_formatted': apt.appointment_date.strftime('%d-%m-%Y'),
            'token_number': apt.token_number,
            'status': apt.status,
            'reason': apt.reason or '',
        })
    
    # Recent bills (last 10)
    recent_bills = Bill.objects.select_related('appointment__patient').order_by('-created_at')[:10]
    bills_data = []
    for bill in recent_bills:
        bills_data.append({
            'id': bill.id,
            'bill_number': bill.bill_number,
            'patient_name': bill.appointment.patient.full_name if bill.appointment else 'N/A',
            'amount': float(bill.final_amount),
            'payment_status': bill.payment_status,
            'created_at': bill.created_at.strftime('%d-%m-%Y'),
        })
    
    return Response({
        'patientstoday': patientstoday,
        'appointmentstoday': appointmentstoday,
        'pendingappointments': pendingappointments,
        'revenuetoday': float(revenuetoday),
        'expiringregistrations': expiringregistrations,
        'availabledoctors': availabledoctors,
        'registrations': registrations_data,
        'appointments': appointments_data,
        'bills': bills_data,
    })


@api_view(['GET'])
def doctor_list(request):
    """Get list of all active doctors"""
    from Authentication.models import Staff
    
    doctors = Staff.objects.filter(
        Role='Doctor',
        IsActive=True
    ).values('StaffId', 'StaffName', 'Experience', 'Email', 'Phone')
    
    return Response({
        'status': 'success',
        'data': list(doctors)
    })

# Receptionist/views.py

@api_view(['GET'])
def dashboard_notifications(request):
    """
    Get dashboard notifications for receptionist
    Returns: new registrations, expiring registrations, low doctor availability, 
             pending bills, cancelled appointments
    """
    from django.utils import timezone
    from datetime import timedelta
    
    today = timezone.now().date()
    week_from_now = today + timedelta(days=7)
    
    # New registrations today
    new_registrations = Registration.objects.filter(
        registration_date=today
    ).select_related('patient')[:5]
    
    # Registrations expiring within 7 days
    expiring_registrations = Registration.objects.filter(
        expiry_date__lte=week_from_now,
        expiry_date__gte=today
    ).select_related('patient')[:5]
    
    # Cancelled appointments today
    cancelled_appointments = Appointment.objects.filter(
        appointment_date=today,
        status='Cancelled'
    ).select_related('patient', 'doctor')[:5]
    
    # Pending bills (unpaid)
    pending_bills = Bill.objects.filter(
        payment_status='Unpaid'
    ).select_related('appointment__patient')[:5]
    
    # Serialize data
    new_reg_data = [{
        'patient_name': reg.patient.full_name,
        'patient_reg_number': reg.patient.patient_reg_number,
        'registration_date': reg.registration_date.strftime('%d-%m-%Y'),
    } for reg in new_registrations]
    
    expiring_reg_data = [{
        'patient_name': reg.patient.full_name,
        'patient_reg_number': reg.patient.patient_reg_number,
        'expiry_date': reg.expiry_date.strftime('%d-%m-%Y'),
        'days_left': (reg.expiry_date - today).days,
    } for reg in expiring_registrations]
    
    cancelled_apt_data = [{
        'patient_name': apt.patient.full_name,
        'doctor_name': apt.doctor.doctor_name,
        'appointment_date': apt.appointment_date.strftime('%d-%m-%Y'),
        'token_number': apt.token_number,
    } for apt in cancelled_appointments]
    
    pending_bills_data = [{
        'bill_number': bill.bill_number,
        'patient_name': bill.appointment.patient.full_name if bill.appointment else 'N/A',
        'total_amount': float(bill.total_amount),
        'created_at': bill.created_at.strftime('%d-%m-%Y %H:%M'),
    } for bill in pending_bills]
    
    return Response({
        'success': True,
        'data': {
            'newRegistrations': new_reg_data,
            'expiringRegistrations': expiring_reg_data,
            'cancelledAppointments': cancelled_apt_data,
            'pendingBills': pending_bills_data,
            'lowDoctorAvailability': [],  # Can add logic later if needed
        }
    })
