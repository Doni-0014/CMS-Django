# Pharmacist/views.py - COMPLETE VERSION WITH AUTOMATION
from rest_framework import viewsets, status, filters, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Sum, Count, F
from django.db import transaction
from django.utils import timezone
from datetime import date, timedelta
from django.contrib.auth.models import User
from rest_framework.permissions import AllowAny

from .models import MedicineCategory, Medicine, Bill, BillMedicine, PharmacySales
from .serializers import (
    MedicineCategorySerializer, MedicineSerializer, MedicineListSerializer,
    BillSerializer, BillListSerializer, BillMedicineSerializer,
    PharmacySalesSerializer, PharmacySalesListSerializer, DoctorListSerializer
)
from .services import PharmacyAutomationService  # NEW - Automation service
from Doctor.models import MedicinePrescription  # NEW - For prescription integration


class MedicineCategoryViewSet(viewsets.ModelViewSet):
    """Medicine Category CRUD with JWT authentication"""
    queryset = MedicineCategory.objects.filter(is_active=True)
    serializer_class = MedicineCategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active', 'category_name']
    search_fields = ['category_name', 'description']
    ordering = ['s_no']
    
    @action(detail=False, methods=['get'])
    def active_categories(self, request):
        """Get active categories for dropdown"""
        categories = self.queryset.filter(is_active=True)
        serializer = self.get_serializer(categories, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=True, methods=['patch'])
    def toggle_status(self, request, pk=None):
        """Toggle category active/inactive status"""
        category = self.get_object()
        category.is_active = not category.is_active
        category.save()
        
        status_text = "activated" if category.is_active else "deactivated"
        return Response({
            'success': True,
            'message': f'Category {category.category_name} has been {status_text}',
            'is_active': category.is_active
        })
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete category"""
        category = self.get_object()
        
        if category.medicines.filter(is_active=True).exists():
            return Response({
                'success': False,
                'message': 'Cannot delete category with active medicines'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        category.is_active = False
        category.save()
        
        return Response({
            'success': True,
            'message': f'Category {category.category_name} has been deactivated'
        })


class MedicineViewSet(viewsets.ModelViewSet):
    """Medicine CRUD with S.no search functionality + AUTOMATION"""
    queryset = Medicine.objects.filter(is_active=True)
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'company_name', 'is_active']
    search_fields = ['medicine_name', 'medicine_code', 'generic_name', 'patient_reg_number']
    ordering = ['s_no']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return MedicineListSerializer
        return MedicineSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # S.no search support
        s_no = self.request.query_params.get('s_no')
        if s_no:
            try:
                return queryset.filter(s_no=int(s_no))
            except (ValueError, TypeError):
                pass
        
        # REMOVED: Patient registration number search
        # (Patient info no longer in Medicine model)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def search_by_sno(self, request):
        """Quick search by S.no"""
        s_no = request.query_params.get('s_no')
        if not s_no:
            return Response({
                'success': False,
                'message': 'S.no parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            medicine = Medicine.objects.get(s_no=int(s_no), is_active=True)
            serializer = MedicineSerializer(medicine)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Medicine.DoesNotExist:
            return Response({
                'success': False,
                'message': f'Medicine with S.no {s_no} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({
                'success': False,
                'message': 'Invalid S.no format'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # NEW - AUTOMATION: Fuzzy search for prescription matching
    @action(detail=False, methods=['get'])
    def search_fuzzy(self, request):
        """
        Fuzzy search for medicines by name (for prescription matching)
        GET /api/pharmacist/medicines/search_fuzzy/?q=Paracetamol
        """
        query = request.query_params.get('q', '')
        if not query:
            return Response({
                'success': False,
                'error': 'Query parameter "q" is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        results = PharmacyAutomationService.fuzzy_search_medicine(query)
        return Response({
            'success': True,
            'query': query,
            'matches': results,
            'count': len(results)
        })
    
    @action(detail=True, methods=['patch'])
    def update_stock(self, request, pk=None):
        """Update medicine stock and price"""
        medicine = self.get_object()
        new_quantity = request.data.get('quantity')
        new_price = request.data.get('price')
        
        if new_quantity is not None:
            try:
                new_quantity = int(new_quantity)
                if new_quantity < 0:
                    return Response({
                        'success': False,
                        'message': 'Quantity cannot be negative'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                medicine.quantity = new_quantity
                medicine.updated_by = request.user
                medicine.save()
                
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'message': 'Invalid quantity format'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        if new_price is not None:
            try:
                new_price = float(new_price)
                if new_price <= 0:
                    return Response({
                        'success': False,
                        'message': 'Price must be positive'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                medicine.price = new_price
                medicine.updated_by = request.user
                medicine.save()
                
            except (ValueError, TypeError):
                return Response({
                    'success': False,
                    'message': 'Invalid price format'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = MedicineSerializer(medicine)
        return Response({
            'success': True,
            'message': 'Medicine updated successfully',
            'data': serializer.data
        })
    
    # ENHANCED - Uses automation service now
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get medicines with low stock - ENHANCED with automation"""
        low_stock_medicines = PharmacyAutomationService.get_low_stock_medicines()
        serializer = MedicineListSerializer(low_stock_medicines, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': low_stock_medicines.count()
        })
    
    # NEW - AUTOMATION: Low stock alert endpoint
    @action(detail=False, methods=['get'])
    def low_stock_alert(self, request):
        """
        Get medicines with low stock alert (for dashboard)
        GET /api/pharmacist/medicines/low_stock_alert/
        """
        medicines = PharmacyAutomationService.get_low_stock_medicines()
        serializer = self.get_serializer(medicines, many=True)
        return Response({
            'success': True,
            'count': medicines.count(),
            'medicines': serializer.data,
            'alert': '🚨 These medicines need reordering'
        })
    
    # ENHANCED - Uses automation service now
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get medicines expiring within specified days - ENHANCED"""
        days = int(request.query_params.get('days', 30))
        expiring_medicines = PharmacyAutomationService.get_expiring_medicines(days)
        serializer = MedicineListSerializer(expiring_medicines, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': expiring_medicines.count(),
            'days': days,
            'warning': f'⚠️ These medicines expire within {days} days'
        })
    
    # NEW - AUTOMATION: Expired medicines alert
    @action(detail=False, methods=['get'])
    def expired(self, request):
        """
        Get expired medicines (DO NOT DISPENSE)
        GET /api/pharmacist/medicines/expired/
        """
        medicines = PharmacyAutomationService.get_expired_medicines()
        serializer = self.get_serializer(medicines, many=True)
        return Response({
            'success': True,
            'count': medicines.count(),
            'medicines': serializer.data,
            'critical_warning': '❌ These medicines are EXPIRED - DO NOT DISPENSE'
        })
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)


class BillViewSet(viewsets.ModelViewSet):
    """Bill CRUD with workflow integration"""
    queryset = Bill.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['payment_status', 'payment_method', 'doctor_verification_status']
    search_fields = ['bill_number', 'patient_name', 'patient_reg_number']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return BillListSerializer
        return BillSerializer
    
    @action(detail=False, methods=['get'])
    def search_by_bill_number(self, request):
        """Quick search by bill number"""
        bill_number = request.query_params.get('bill_number')
        if not bill_number:
            return Response({
                'success': False,
                'message': 'bill_number parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            bill = Bill.objects.get(bill_number=bill_number.upper())
            serializer = BillSerializer(bill)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except Bill.DoesNotExist:
            return Response({
                'success': False,
                'message': f'Bill {bill_number} not found'
            }, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['patch'])
    def doctor_verification(self, request, pk=None):
        """Doctor verification workflow step"""
        bill = self.get_object()
        
        if bill.doctor_verification_status:
            return Response({
                'success': False,
                'message': 'Bill is already verified by doctor'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update doctor verification
        bill.doctor_verification_status = True
        bill.doctor_verified_at = timezone.now()
        bill.payment_status = 'PAYMENT_PENDING'
        bill.save()
        
        return Response({
            'success': True,
            'message': 'Bill verified successfully. Patient can now make payment.'
        })
    
    @action(detail=True, methods=['patch'])
    def update_payment_status(self, request, pk=None):
        """Update payment status"""
        bill = self.get_object()
        new_status = request.data.get('payment_status')
        payment_method = request.data.get('payment_method')
        paid_amount = request.data.get('paid_amount')
        
        # Validate workflow sequence
        if new_status == 'PAID' and not bill.doctor_verification_status:
            return Response({
                'success': False,
                'message': 'Bill must be verified by doctor before payment'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        old_status = bill.payment_status
        bill.payment_status = new_status
        
        if new_status == 'PAID':
            bill.payment_method = payment_method or 'CASH'
            bill.paid_amount = float(paid_amount) if paid_amount else bill.total_amount
            bill.paid_at = timezone.now()
            bill.is_reported_to_admin = True
        
        bill.save()
        
        return Response({
            'success': True,
            'message': f'Payment status updated from {old_status} to {new_status}'
        })
    
    @action(detail=False, methods=['get'])
    def daily_sales(self, request):
        """Today's sales summary"""
        today = timezone.now().date()
        today_bills = self.queryset.filter(created_at__date=today)
        
        total_bills = today_bills.count()
        paid_bills = today_bills.filter(payment_status='PAID')
        total_revenue = paid_bills.aggregate(total=Sum('total_amount'))['total'] or 0
        
        return Response({
            'success': True,
            'data': {
                'date': today,
                'total_bills': total_bills,
                'paid_bills': paid_bills.count(),
                'total_revenue': total_revenue
            }
        })
    
    @action(detail=False, methods=['get'])
    def patient_bills(self, request):
        """Get all bills for a specific patient"""
        patient_reg_number = request.query_params.get('patient_reg_number')
        if not patient_reg_number:
            return Response({
                'success': False,
                'message': 'patient_reg_number parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        bills = self.queryset.filter(patient_reg_number=patient_reg_number)
        serializer = BillListSerializer(bills, many=True)
        
        return Response({
            'success': True,
            'data': serializer.data,
            'count': bills.count()
        })
    
    def perform_create(self, serializer):
        serializer.save(pharmacist=self.request.user)


class BillMedicineViewSet(viewsets.ModelViewSet):
    """Bill Medicine items CRUD"""
    queryset = BillMedicine.objects.all()
    serializer_class = BillMedicineSerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        bill_id = self.request.query_params.get('bill_id')
        if bill_id:
            queryset = queryset.filter(bill_id=bill_id)
        return queryset
    
    @action(detail=True, methods=['patch'])
    def doctor_approve(self, request, pk=None):
        """Doctor approval for specific medicine in bill"""
        bill_medicine = self.get_object()
        
        bill_medicine.doctor_approved = request.data.get('approved', True)
        bill_medicine.doctor_notes = request.data.get('notes', '')
        bill_medicine.save()
        
        return Response({
            'success': True,
            'message': 'Medicine approval updated',
            'approved': bill_medicine.doctor_approved
        })


class PharmacySalesViewSet(viewsets.ReadOnlyModelViewSet):
    """Pharmacy sales analytics (read-only)"""
    queryset = PharmacySales.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['payment_method', 'sale_date', 'pharmacist']
    search_fields = ['patient_name', 'patient_reg_number']
    ordering = ['-sale_date']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PharmacySalesListSerializer
        return PharmacySalesSerializer
    
    @action(detail=False, methods=['get'])
    def search_by_sno(self, request):
        """Quick search by S.no"""
        s_no = request.query_params.get('s_no')
        if not s_no:
            return Response({
                'success': False,
                'message': 'S.no parameter is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            sale = PharmacySales.objects.get(s_no=int(s_no))
            serializer = PharmacySalesSerializer(sale)
            return Response({
                'success': True,
                'data': serializer.data
            })
        except PharmacySales.DoesNotExist:
            return Response({
                'success': False,
                'message': f'Sales record with S.no {s_no} not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except ValueError:
            return Response({
                'success': False,
                'message': 'Invalid S.no format'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def daily_summary(self, request):
        """Daily sales summary"""
        target_date = request.query_params.get('date', timezone.now().date())
        
        if isinstance(target_date, str):
            try:
                target_date = timezone.datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                target_date = timezone.now().date()
        
        daily_sales = self.queryset.filter(sale_date=target_date)
        
        total_sales = daily_sales.count()
        total_revenue = daily_sales.aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Payment method breakdown
        payment_breakdown = daily_sales.values('payment_method').annotate(
            count=Count('sales_id'),
            amount=Sum('total_amount')
        )
        
        return Response({
            'success': True,
            'data': {
                'date': target_date,
                'total_sales': total_sales,
                'total_revenue': total_revenue,
                'payment_breakdown': payment_breakdown
            }
        })


# NEW - AUTOMATION: Prescription Management ViewSet
class PrescriptionManagementViewSet(viewsets.ViewSet):
    """
    Pharmacy-side prescription management with automation
    """
    permission_classes = [AllowAny]
    
    def list(self, request):
        """
        Get pending prescriptions with fuzzy-matched medicines
        GET /api/pharmacist/prescriptions/pending/
        """
        prescriptions = PharmacyAutomationService.get_pending_prescriptions()
        data = []
        
        for prescription in prescriptions:
            # Auto-suggest matching medicines from inventory
            matches = PharmacyAutomationService.fuzzy_search_medicine(
                prescription.medicine_name
            )
            
            data.append({
                'prescription_id': prescription.prescription_id,
                'consultation_id': prescription.consultation.consultation_id,
                'patient_name': prescription.consultation.patient.full_name,
                'patient_reg': prescription.consultation.patient.patient_reg_number,
                'doctor_name': prescription.consultation.doctor.doctor_name,
                'medicine_prescribed': prescription.medicine_name,
                'dosage': prescription.dosage,
                'frequency': prescription.frequency,
                'duration_days': prescription.duration_days,
                'status': prescription.fulfillment_status,
                'suggested_matches': matches,  # Auto-suggested from inventory
                'match_count': len(matches)
            })
        
        return Response({
            'success': True,
            'count': len(data),
            'prescriptions': data
        })
    
    @action(detail=False, methods=['post'])
    def create_bill_from_prescription(self, request):
        """
        Generate bill from prescription with stock validation & expiry checking
        POST /api/pharmacist/prescriptions/create_bill/
        {
            "prescription_id": "RX202510220001",
            "medicine_id": "uuid",
            "quantity_to_dispense": 10
        }
        """
        prescription_id = request.data.get('prescription_id')
        medicine_id = request.data.get('medicine_id')
        quantity = int(request.data.get('quantity_to_dispense', 0))
        
        if not all([prescription_id, medicine_id, quantity]):
            return Response({
                'success': False,
                'error': 'prescription_id, medicine_id, and quantity_to_dispense are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            prescription = MedicinePrescription.objects.get(prescription_id=prescription_id)
            medicine = Medicine.objects.get(medicine_id=medicine_id)
            
            # AUTOMATION: Check stock availability
            has_stock, stock_status, available = PharmacyAutomationService.check_stock_availability(
                medicine_id, quantity
            )
            
            if stock_status == 'out_of_stock':
                return Response({
                    'success': False,
                    'error': 'Medicine out of stock',
                    'available': 0,
                    'requested': quantity
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # AUTOMATION: Check expiry
            is_valid, expiry_status, days = PharmacyAutomationService.check_medicine_expiry(medicine_id)
            if expiry_status == 'expired':
                return Response({
                    'success': False,
                    'error': '❌ CRITICAL: Medicine is EXPIRED - DO NOT DISPENSE',
                    'expiry_date': str(medicine.expiry_date),
                    'days_expired': abs(days)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Determine actual quantity (partial fulfillment if needed)
            actual_quantity = min(quantity, available) if stock_status == 'partial' else quantity
            
            # Create Bill
            bill = Bill.objects.create(
                patient=prescription.consultation.patient,
                prescribing_doctor=prescription.consultation.doctor,
                prescription=prescription,
                patient_name=prescription.consultation.patient.full_name,
                patient_reg_number=prescription.consultation.patient.patient_reg_number,
                patient_phone=prescription.consultation.patient.contact_number,
                patient_dob=prescription.consultation.patient.date_of_birth,
                pharmacist=request.user if request.user.is_authenticated else None,
                subtotal=medicine.price * actual_quantity,
                total_amount=medicine.price * actual_quantity,
                payment_status='PAYMENT_PENDING'
            )
            
            # Create BillMedicine
            bill_medicine = BillMedicine.objects.create(
                bill=bill,
                medicine=medicine,
                prescribed_quantity=quantity,
                dispensed_quantity=actual_quantity,
                dosage_instructions=prescription.dosage,
                frequency=prescription.frequency,
                duration=f"{prescription.duration_days} days",
                unit_price=medicine.price
            )
            
            # Update prescription fulfillment status
            if actual_quantity < quantity:
                prescription.fulfillment_status = 'partial'
                fulfillment_message = f'Partially fulfilled: {actual_quantity}/{quantity}'
            else:
                prescription.fulfillment_status = 'fulfilled'
                fulfillment_message = 'Fully fulfilled'
            
            prescription.dispensed_quantity = actual_quantity
            prescription.save()
            
            # Prepare response
            response_data = {
                'success': True,
                'bill_number': bill.bill_number,
                'bill_id': str(bill.bill_id),
                'dispensed_quantity': actual_quantity,
                'prescribed_quantity': quantity,
                'fulfillment_status': fulfillment_message,
                'total_amount': float(bill.total_amount),
                'payment_status': bill.payment_status
            }
            
            # Add warnings if applicable
            if stock_status == 'partial':
                response_data['warning'] = f'⚠️ Only {available} tablets available - dispensed partially'
            
            if expiry_status == 'expiring_soon':
                response_data['expiry_warning'] = f'⚠️ Medicine expires in {days} days'
            
            return Response(response_data)
            
        except MedicinePrescription.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Prescription not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Medicine.DoesNotExist:
            return Response({
                'success': False,
                'error': 'Medicine not found in inventory'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'error': f'Error creating bill: {str(e)}'
            }, status=status.HTTP_400_BAD_REQUEST)


class PharmacyDashboardViewSet(viewsets.ViewSet):
    """Pharmacy dashboard analytics"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def dashboard_summary(self, request):
        """Complete dashboard summary"""
        today = timezone.now().date()
        
        # Medicine statistics
        total_medicines = Medicine.objects.filter(is_active=True).count()
        low_stock_count = Medicine.objects.filter(
            is_active=True,
            quantity__lte=F('low_stock_threshold')
        ).count()
        
        expiring_soon_count = Medicine.objects.filter(
            is_active=True,
            expiry_date__lte=today + timedelta(days=30)
        ).count()
        
        # Bill statistics
        today_bills = Bill.objects.filter(created_at__date=today)
        pending_verification = today_bills.filter(payment_status='PENDING_VERIFICATION').count()
        pending_payment = today_bills.filter(payment_status='PAYMENT_PENDING').count()
        completed_today = today_bills.filter(payment_status='PAID').count()
        
        # Revenue statistics
        today_revenue = today_bills.filter(payment_status='PAID').aggregate(
            total=Sum('total_amount')
        )['total'] or 0
        
        return Response({
            'success': True,
            'data': {
                'medicine_stats': {
                    'total_medicines': total_medicines,
                    'low_stock_count': low_stock_count,
                    'expiring_soon_count': expiring_soon_count
                },
                'bill_stats': {
                    'pending_verification': pending_verification,
                    'pending_payment': pending_payment,
                    'completed_today': completed_today,
                    'today_revenue': today_revenue
                },
                'date': today
            }
        })
    
    @action(detail=False, methods=['get'])
    def alerts(self, request):
        """Get important alerts"""
        alerts = []
        
        # Low stock alerts
        low_stock_medicines = Medicine.objects.filter(
            is_active=True,
            quantity__lte=F('low_stock_threshold')
        )[:5]
        
        for medicine in low_stock_medicines:
            alerts.append({
                'type': 'LOW_STOCK',
                'priority': 'HIGH',
                'message': f'{medicine.medicine_name} is low on stock (S.no: MED{medicine.s_no:06d})',
                'data': {
                    'medicine_id': medicine.medicine_id,
                    's_no': medicine.s_no,
                    'current_stock': medicine.quantity
                }
            })
        
        # Expiry alerts
        expiry_date = date.today() + timedelta(days=30)
        expiring_medicines = Medicine.objects.filter(
            is_active=True,
            expiry_date__lte=expiry_date
        )[:5]
        
        for medicine in expiring_medicines:
            days_left = (medicine.expiry_date - date.today()).days
            alerts.append({
                'type': 'EXPIRY_ALERT',
                'priority': 'MEDIUM' if days_left > 7 else 'HIGH',
                'message': f'{medicine.medicine_name} expires in {days_left} days',
                'data': {
                    'medicine_id': medicine.medicine_id,
                    's_no': medicine.s_no,
                    'days_left': days_left
                }
            })
        
        return Response({
            'success': True,
            'data': alerts,
            'count': len(alerts)
        })


class UtilityViewSet(viewsets.ViewSet):
    """Utility endpoints for dropdowns"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [AllowAny]
    
    @action(detail=False, methods=['get'])
    def doctors_list(self, request):
        """Get list of doctors"""
        doctors = User.objects.filter(
            groups__name='Doctor',
            is_active=True
        )
        serializer = DoctorListSerializer(doctors, many=True)
        return Response({
            'success': True,
            'data': serializer.data
        })
    
    @action(detail=False, methods=['get'])
    def categories_dropdown(self, request):
        """Get medicine categories for dropdown"""
        categories = MedicineCategory.objects.filter(is_active=True)
        return Response({
            'success': True,
            'data': [
                {
                    'category_id': cat.category_id,
                    's_no': cat.s_no,
                    'category_name': cat.category_name
                }
                for cat in categories
            ]
        })
    
    @action(detail=False, methods=['get'])
    def system_stats(self, request):
        """System-wide statistics"""
        stats = {
            'total_medicines': Medicine.objects.filter(is_active=True).count(),
            'total_categories': MedicineCategory.objects.filter(is_active=True).count(),
            'total_bills': Bill.objects.count(),
            'paid_bills': Bill.objects.filter(payment_status='PAID').count(),
            'total_revenue': Bill.objects.filter(payment_status='PAID').aggregate(
                total=Sum('total_amount')
            )['total'] or 0
        }
        
        return Response({
            'success': True,
            'data': stats
        })
