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

from .models import MedicineCategory, Medicine, Bill, BillMedicine, PharmacySales
from .serializers import (
    MedicineCategorySerializer, MedicineSerializer, MedicineListSerializer,
    BillSerializer, BillListSerializer, BillMedicineSerializer,
    PharmacySalesSerializer, PharmacySalesListSerializer,  DoctorListSerializer
)

class MedicineCategoryViewSet(viewsets.ModelViewSet):
    """Medicine Category CRUD with JWT authentication"""
    queryset = MedicineCategory.objects.filter(is_active=True)
    serializer_class = MedicineCategorySerializer
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
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
    """Medicine CRUD with S.no search functionality"""
    queryset = Medicine.objects.filter(is_active=True)
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
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
        
        # Patient registration number search
        patient_reg = self.request.query_params.get('patient_reg_number')
        if patient_reg:
            queryset = queryset.filter(patient_reg_number__icontains=patient_reg)
        
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
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get medicines with low stock"""
        low_stock_medicines = self.queryset.filter(quantity__lte=F('low_stock_threshold'))
        serializer = MedicineListSerializer(low_stock_medicines, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': low_stock_medicines.count()
        })
    
    @action(detail=False, methods=['get'])
    def expiring_soon(self, request):
        """Get medicines expiring within 30 days"""
        expiry_date = date.today() + timedelta(days=30)
        expiring_medicines = self.queryset.filter(expiry_date__lte=expiry_date)
        serializer = MedicineListSerializer(expiring_medicines, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': expiring_medicines.count()
        })
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)
    
    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

class BillViewSet(viewsets.ModelViewSet):
    """Bill CRUD with workflow integration"""
    queryset = Bill.objects.all()
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
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
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
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

class PharmacyDashboardViewSet(viewsets.ViewSet):
    """Pharmacy dashboard analytics"""
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    
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
    permission_classes = [permissions.IsAuthenticated]
    
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
