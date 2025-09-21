from django.test import TestCase
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import date, timedelta
from decimal import Decimal
from .models import MedicineCategory, Medicine, Bill, BillMedicine, PharmacySales
from .serializers import (
    MedicineCategorySerializer, MedicineSerializer, BillSerializer,
    BillMedicineSerializer, PharmacySalesSerializer
)

class MedicineCategoryModelTest(TestCase):
    """Test MedicineCategory model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
    
    def test_s_no_auto_generation(self):
        """Test S.no auto-generates correctly"""
        category1 = MedicineCategory.objects.create(
            category_name='Pain Relief',
            created_by=self.user
        )
        self.assertEqual(category1.s_no, 1)
        
        category2 = MedicineCategory.objects.create(
            category_name='Antibiotics',
            created_by=self.user
        )
        self.assertEqual(category2.s_no, 2)
    
    def test_category_name_validation(self):
        """Test category name must be at least 3 characters"""
        category = MedicineCategory(
            category_name='AB',  # Too short
            created_by=self.user
        )
        with self.assertRaises(ValidationError):
            category.clean()
    
    def test_string_representation(self):
        """Test __str__ method"""
        category = MedicineCategory.objects.create(
            category_name='Pain Relief',
            created_by=self.user
        )
        expected = f"CAT{category.s_no:03d} - Pain Relief"
        self.assertEqual(str(category), expected)

class MedicineModelTest(TestCase):
    """Test Medicine model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.category = MedicineCategory.objects.create(
            category_name='Pain Relief',
            created_by=self.user
        )
    
    def test_s_no_auto_generation(self):
        """Test Medicine S.no auto-generates correctly"""
        medicine1 = Medicine.objects.create(
            category=self.category,
            medicine_code='MED001',
            medicine_name='Paracetamol',
            generic_name='Acetaminophen',
            company_name='Generic Pharma',
            price=Decimal('50.00'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today() - timedelta(days=30),
            batch_number='BATCH001',
            created_by=self.user
        )
        self.assertEqual(medicine1.s_no, 1)
        
        medicine2 = Medicine.objects.create(
            category=self.category,
            medicine_code='MED002',
            medicine_name='Aspirin',
            generic_name='Acetylsalicylic Acid',
            company_name='Generic Pharma',
            price=Decimal('30.00'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today() - timedelta(days=30),
            batch_number='BATCH002',
            created_by=self.user
        )
        self.assertEqual(medicine2.s_no, 2)
    
    def test_expiry_date_validation(self):
        """Test expiry date must be in future"""
        medicine = Medicine(
            category=self.category,
            medicine_code='MED001',
            medicine_name='Expired Medicine',
            generic_name='Generic Name',
            company_name='Test Company',
            price=Decimal('50.00'),
            expiry_date=date.today() - timedelta(days=1),  # Past date
            manufacturing_date=date.today() - timedelta(days=30),
            batch_number='BATCH001',
            created_by=self.user
        )
        with self.assertRaises(ValidationError):
            medicine.clean()
    
    def test_manufacturing_vs_expiry_date(self):
        """Test manufacturing date must be before expiry date"""
        medicine = Medicine(
            category=self.category,
            medicine_code='MED001',
            medicine_name='Test Medicine',
            generic_name='Generic Name',
            company_name='Test Company',
            price=Decimal('50.00'),
            manufacturing_date=date.today(),
            expiry_date=date.today() - timedelta(days=1),  # Before manufacturing
            batch_number='BATCH001',
            created_by=self.user
        )
        with self.assertRaises(ValidationError):
            medicine.clean()
    
    def test_price_validation(self):
        """Test price cannot exceed limit"""
        medicine = Medicine(
            category=self.category,
            medicine_code='MED001',
            medicine_name='Expensive Medicine',
            generic_name='Generic Name',
            company_name='Test Company',
            price=Decimal('60000.00'),  # Exceeds ₹50,000 limit
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today() - timedelta(days=30),
            batch_number='BATCH001',
            created_by=self.user
        )
        with self.assertRaises(ValidationError):
            medicine.clean()
    
    def test_is_low_stock_property(self):
        """Test is_low_stock property"""
        medicine = Medicine.objects.create(
            category=self.category,
            medicine_code='MED001',
            medicine_name='Low Stock Medicine',
            generic_name='Generic Name',
            company_name='Test Company',
            price=Decimal('50.00'),
            quantity=5,
            low_stock_threshold=10,
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today() - timedelta(days=30),
            batch_number='BATCH001',
            created_by=self.user
        )
        self.assertTrue(medicine.is_low_stock)
    
    def test_is_expiring_soon_property(self):
        """Test is_expiring_soon property"""
        medicine = Medicine.objects.create(
            category=self.category,
            medicine_code='MED001',
            medicine_name='Expiring Soon Medicine',
            generic_name='Generic Name',
            company_name='Test Company',
            price=Decimal('50.00'),
            expiry_date=date.today() + timedelta(days=15),  # Expires in 15 days
            manufacturing_date=date.today() - timedelta(days=30),
            batch_number='BATCH001',
            created_by=self.user
        )
        self.assertTrue(medicine.is_expiring_soon)

class BillModelTest(TestCase):
    """Test Bill model functionality"""
    
    def setUp(self):
        self.pharmacist = User.objects.create_user(username='pharmacist', password='testpass')
        self.doctor = User.objects.create_user(username='doctor', password='testpass')
    
    def test_bill_number_auto_generation(self):
        """Test bill number auto-generates correctly"""
        bill1 = Bill.objects.create(
            patient_reg_number='P001',
            patient_name='John Doe',
            patient_phone='9876543210',
            patient_dob=date(1990, 1, 1),
            prescribing_doctor=self.doctor,
            pharmacist=self.pharmacist
        )
        self.assertEqual(bill1.bill_number, 'BILL000001')
        
        bill2 = Bill.objects.create(
            patient_reg_number='P002',
            patient_name='Jane Doe',
            patient_phone='9876543211',
            patient_dob=date(1992, 1, 1),
            prescribing_doctor=self.doctor,
            pharmacist=self.pharmacist
        )
        self.assertEqual(bill2.bill_number, 'BILL000002')
    
    def test_patient_name_validation(self):
        """Test patient name must be at least 3 characters"""
        bill = Bill(
            patient_reg_number='P001',
            patient_name='Jo',  # Too short
            patient_phone='9876543210',
            patient_dob=date(1990, 1, 1),
            prescribing_doctor=self.doctor,
            pharmacist=self.pharmacist
        )
        with self.assertRaises(ValidationError):
            bill.clean()
    
    def test_payment_amount_validation(self):
        """Test paid amount cannot exceed total amount"""
        bill = Bill(
            patient_reg_number='P001',
            patient_name='John Doe',
            patient_phone='9876543210',
            patient_dob=date(1990, 1, 1),
            prescribing_doctor=self.doctor,
            pharmacist=self.pharmacist,
            total_amount=Decimal('100.00'),
            paid_amount=Decimal('150.00')  # Exceeds total
        )
        with self.assertRaises(ValidationError):
            bill.clean()

class MedicineSerializerTest(TestCase):
    """Test MedicineSerializer validation"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.category = MedicineCategory.objects.create(
            category_name='Pain Relief',
            created_by=self.user
        )
    
    def test_medicine_name_validation(self):
        """Test medicine name validation"""
        data = {
            'category': self.category.category_id,
            'medicine_code': 'MED001',
            'medicine_name': 'Pa',  # Too short
            'generic_name': 'Acetaminophen',
            'company_name': 'Generic Pharma',
            'price': '50.00',
            'expiry_date': date.today() + timedelta(days=365),
            'manufacturing_date': date.today() - timedelta(days=30),
            'batch_number': 'BATCH001'
        }
        serializer = MedicineSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('medicine_name', serializer.errors)
    
    def test_phone_number_validation(self):
        """Test patient phone number validation"""
        data = {
            'category': self.category.category_id,
            'medicine_code': 'MED001',
            'medicine_name': 'Paracetamol',
            'generic_name': 'Acetaminophen',
            'company_name': 'Generic Pharma',
            'price': '50.00',
            'patient_phone': '123456',  # Invalid format
            'expiry_date': date.today() + timedelta(days=365),
            'manufacturing_date': date.today() - timedelta(days=30),
            'batch_number': 'BATCH001'
        }
        serializer = MedicineSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('patient_phone', serializer.errors)
    
    def test_price_validation(self):
        """Test price validation"""
        data = {
            'category': self.category.category_id,
            'medicine_code': 'MED001',
            'medicine_name': 'Expensive Medicine',
            'generic_name': 'Generic Name',
            'company_name': 'Test Company',
            'price': '60000.00',  # Exceeds limit
            'expiry_date': date.today() + timedelta(days=365),
            'manufacturing_date': date.today() - timedelta(days=30),
            'batch_number': 'BATCH001'
        }
        serializer = MedicineSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('price', serializer.errors)

class BillMedicineSerializerTest(TestCase):
    """Test BillMedicineSerializer validation"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.category = MedicineCategory.objects.create(
            category_name='Pain Relief',
            created_by=self.user
        )
        self.medicine = Medicine.objects.create(
            category=self.category,
            medicine_code='MED001',
            medicine_name='Paracetamol',
            generic_name='Acetaminophen',
            company_name='Generic Pharma',
            price=Decimal('50.00'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today() - timedelta(days=30),
            batch_number='BATCH001',
            created_by=self.user
        )
        self.bill = Bill.objects.create(
            patient_reg_number='P001',
            patient_name='John Doe',
            patient_phone='9876543210',
            patient_dob=date(1990, 1, 1),
            prescribing_doctor=self.user,
            pharmacist=self.user
        )
    
    def test_dispensed_quantity_exceeds_prescribed(self):
        """Test dispensed quantity cannot exceed prescribed quantity"""
        data = {
            'medicine': self.medicine.medicine_id,
            'prescribed_quantity': 10,
            'dispensed_quantity': 15,  # Exceeds prescribed
            'dosage_instructions': 'Take 1 tablet after meals',
            'frequency': '3 times a day',
            'duration': '5 days',
            'unit_price': '50.00'
        }
        serializer = BillMedicineSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('dispensed_quantity', serializer.errors)
    
    def test_discount_percent_validation(self):
        """Test discount percent must be between 0-100"""
        data = {
            'medicine': self.medicine.medicine_id,
            'prescribed_quantity': 10,
            'dispensed_quantity': 10,
            'dosage_instructions': 'Take 1 tablet after meals',
            'frequency': '3 times a day',
            'duration': '5 days',
            'unit_price': '50.00',
            'discount_percent': '150.00'  # Invalid percentage
        }
        serializer = BillMedicineSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('discount_percent', serializer.errors)

class MedicineAPITest(APITestCase):
    """Test Medicine API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username='pharmacist', password='testpass')
        pharmacist_group, created = Group.objects.get_or_create(name='Pharmacist')
        self.user.groups.add(pharmacist_group)
        self.client.force_authenticate(user=self.user)
        
        self.category = MedicineCategory.objects.create(
            category_name='Pain Relief',
            created_by=self.user
        )
        self.medicine = Medicine.objects.create(
            category=self.category,
            medicine_code='MED001',
            medicine_name='Paracetamol',
            generic_name='Acetaminophen',
            company_name='Generic Pharma',
            price=Decimal('50.00'),
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today() - timedelta(days=30),
            batch_number='BATCH001',
            created_by=self.user
        )
    
    def test_search_by_sno_success(self):
        """Test successful S.no search"""
        response = self.client.get(f'/pharmacist/api/medicines/search_by_sno/?s_no={self.medicine.s_no}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['s_no'], self.medicine.s_no)
    
    def test_search_by_sno_not_found(self):
        """Test S.no search with non-existent S.no"""
        response = self.client.get('/pharmacist/api/medicines/search_by_sno/?s_no=999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertFalse(response.data['success'])
    
    def test_search_by_sno_invalid_format(self):
        """Test S.no search with invalid format"""
        response = self.client.get('/pharmacist/api/medicines/search_by_sno/?s_no=abc')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
    
    def test_low_stock_medicines(self):
        """Test low stock medicines endpoint"""
        # Create a low stock medicine
        Medicine.objects.create(
            category=self.category,
            medicine_code='MED002',
            medicine_name='Low Stock Medicine',
            generic_name='Generic Name',
            company_name='Test Company',
            price=Decimal('30.00'),
            quantity=5,
            low_stock_threshold=10,
            expiry_date=date.today() + timedelta(days=365),
            manufacturing_date=date.today() - timedelta(days=30),
            batch_number='BATCH002',
            created_by=self.user
        )
        
        response = self.client.get('/pharmacist/api/medicines/low_stock/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertGreater(response.data['count'], 0)
    
    def test_authentication_required(self):
        """Test API requires authentication"""
        self.client.force_authenticate(user=None)
        response = self.client.get('/pharmacist/api/medicines/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

class BillAPITest(APITestCase):
    """Test Bill API endpoints"""
    
    def setUp(self):
        self.client = APIClient()
        self.pharmacist = User.objects.create_user(username='pharmacist', password='testpass')
        self.doctor = User.objects.create_user(username='doctor', password='testpass')
        
        pharmacist_group, created = Group.objects.get_or_create(name='Pharmacist')
        self.pharmacist.groups.add(pharmacist_group)
        
        self.client.force_authenticate(user=self.pharmacist)
        
        self.bill = Bill.objects.create(
            patient_reg_number='P001',
            patient_name='John Doe',
            patient_phone='9876543210',
            patient_dob=date(1990, 1, 1),
            prescribing_doctor=self.doctor,
            pharmacist=self.pharmacist
        )
    
    def test_search_by_bill_number_success(self):
        """Test successful bill number search"""
        response = self.client.get(f'/pharmacist/api/bills/search_by_bill_number/?bill_number={self.bill.bill_number}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['bill_number'], self.bill.bill_number)
    
    def test_doctor_verification_success(self):
        """Test doctor verification process"""
        response = self.client.patch(f'/pharmacist/api/bills/{self.bill.bill_id}/doctor_verification/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify bill status changed
        self.bill.refresh_from_db()
        self.assertTrue(self.bill.doctor_verification_status)
        self.assertEqual(self.bill.payment_status, 'PAYMENT_PENDING')
    
    def test_daily_sales_summary(self):
        """Test daily sales summary"""
        response = self.client.get('/pharmacist/api/bills/daily_sales/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('total_bills', response.data['data'])

class PharmacySalesModelTest(TestCase):
    """Test PharmacySales model functionality"""
    
    def setUp(self):
        self.pharmacist = User.objects.create_user(username='pharmacist', password='testpass')
        self.doctor = User.objects.create_user(username='doctor', password='testpass')
        
        self.bill = Bill.objects.create(
            patient_reg_number='P001',
            patient_name='John Doe',
            patient_phone='9876543210',
            patient_dob=date(1990, 1, 1),
            prescribing_doctor=self.doctor,
            pharmacist=self.pharmacist,
            total_amount=Decimal('100.00'),
            payment_method='CASH',
            payment_status='PAID'
        )
    
    def test_sales_record_creation(self):
        """Test PharmacySales record creation from bill"""
        sales = PharmacySales.create_from_bill(self.bill)
        
        self.assertEqual(sales.patient_name, self.bill.patient_name)
        self.assertEqual(sales.total_amount, self.bill.total_amount)
        self.assertEqual(sales.payment_method, self.bill.payment_method)
        self.assertEqual(sales.s_no, 1)
    
    def test_s_no_generation(self):
        """Test S.no generation for sales records"""
        sales1 = PharmacySales.create_from_bill(self.bill)
        self.assertEqual(sales1.s_no, 1)
        
        # Create another bill and sales record
        bill2 = Bill.objects.create(
            patient_reg_number='P002',
            patient_name='Jane Doe',
            patient_phone='9876543211',
            patient_dob=date(1992, 1, 1),
            prescribing_doctor=self.doctor,
            pharmacist=self.pharmacist,
            total_amount=Decimal('150.00'),
            payment_method='CARD',
            payment_status='PAID'
        )
        sales2 = PharmacySales.create_from_bill(bill2)
        self.assertEqual(sales2.s_no, 2)
