from django.db import models
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum

from applications.home.models import BaseModel
from applications.inv.models import Product


# Create your models here.

class Supplier(BaseModel):
    name = models.CharField(max_length=255, verbose_name='Proveedor')
    contact_person = models.CharField(max_length=255, verbose_name='Contacto', blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name='Telefono', blank=True, null=True, unique=True)
    email = models.EmailField(verbose_name='Email Address', blank=True, null=True, unique=True)
    address = models.TextField(verbose_name='Direccion', blank=True, null=True)

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return self.name

    def save(self):
        self.name = self.name.upper()
        return super(Supplier, self).save()

    def toggle_status(self):
        self.status = not self.status
        self.save()
        return self.status
    
class PurchaseOrder(BaseModel):
        order_date = models.DateField(verbose_name='Fecha de Orden')
        observations = models.TextField(verbose_name='Observaciones', blank=True, null=True)
        order_number = models.CharField(max_length=100, verbose_name='Numero de Orden', unique=True)
        buy_date = models.DateField(verbose_name='Fecha de Compra')
        subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Subtotal', default=0.00)
        discount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Descuento', default=0.00)
        tax = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Impuesto', default=0.00)
        supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, verbose_name='Proveedor')
        
        total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Monto Total')

        class Meta:
            verbose_name = 'Orden de Compra'
            verbose_name_plural = 'Ordenes de Compra'

        def __str__(self):
            return self.order_number

        def save(self):
            self.order_number = self.order_number.upper()
            self.total_amount = self.subtotal - self.discount + self.tax
            return super(PurchaseOrder, self).save()

        def toggle_status(self):
            self.status = not self.status
            self.save()
            return self.status
        
class PurchaseItem(BaseModel):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, verbose_name='Orden de Compra', related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Producto')
    quantity = models.PositiveIntegerField(verbose_name='Cantidad', default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio Unitario')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Subtotal', default=0.00)
    tax = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Impuesto', default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Descuento', default=0.00)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio Total')
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Costo', default=0.00)

    class Meta:
        verbose_name = 'Item de Compra'
        verbose_name_plural = 'Items de Compra'

    def __str__(self):
        return f"{self.product} - {self.purchase_order.order_number}"

    def save(self):
        self.subtotal = float(self.quantity) * float(self.unit_price)
        self.total_price = self.subtotal - float(self.discount) + float(self.tax)
        return super(PurchaseItem, self).save()
    
@receiver(post_delete, sender=PurchaseItem)
def update_purchase_oder_delete(sender, instance, **kwargs):
    id_product = instance.product.id
    id_purchase = instance.purchase_order.id

    header = PurchaseItem.objects.filter(pk=id_purchase).first()
    if header:
            sub_total = PurchaseItem.objects.filter(purchase_order=id_purchase).aggregate(Sum('subtotal'))
            discount = PurchaseItem.objects.filter(purchase_order=id_purchase).aggregate(Sum('discount'))
            tax = PurchaseItem.objects.filter(purchase_order=id_purchase).aggregate(Sum('tax'))
            header.subtotal = sub_total["subtotal__sum"]
            header.discount = discount["discount__sum"]
            header.tax = tax["tax__sum"]
            header.save()
    
    product = Product.objects.filter(pk=id_product).first()
    if product:
        quantity = int(product.stock) - int(instance.quantity)
        product.stock = quantity
        product.save()

@receiver(post_save, sender=PurchaseItem)
def update_purchase_oder_save(sender, instance, created, **kwargs):
    id_product = instance.product.id
    buy_date = instance.purchase_order.buy_date
    
    product = Product.objects.filter(pk=id_product).first()
    if product:
        quantity = int(product.stock) + int(instance.quantity)
        product.stock = quantity
        product.last_buy_date = buy_date
        product.save()