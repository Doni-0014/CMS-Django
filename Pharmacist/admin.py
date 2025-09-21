from django.contrib import admin
from .models import MedicineCategory, Medicine, Bill, BillMedicine

# Register your models here.
admin.site.register(MedicineCategory)
admin.site.register(Medicine)
admin.site.register(Bill)
admin.site.register(BillMedicine)

# Don't register JWT token models - they're already registered by rest_framework_simplejwt
