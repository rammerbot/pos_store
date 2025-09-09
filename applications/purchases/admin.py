from django.contrib import admin

# Register your models here.
from .models import Supplier, PurchaseOrder

# Register your models here.

admin.site.register(Supplier)
admin.site.register(PurchaseOrder)
