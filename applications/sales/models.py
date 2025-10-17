from django.db import models, transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum

from applications.home.models import BaseModel
from applications.inv.models import Product



# Create your models here.

class ControlSequence(models.Model):
    name = models.CharField(max_length=100, unique=True)
    sequence_number = models.IntegerField(default=0)

    @classmethod
    def get_next_sequence_number(cls, sequence_name):
        with transaction.atomic():
            # Bloquea la fila de la secuencia hasta que termine la transacción
            control_seq = cls.objects.select_for_update().get(name=sequence_name)
            next_number = control_seq.sequence_number + 1
            control_seq.sequence_number = next_number
            control_seq.save()
            return next_number

class Customer(BaseModel):
    NAT = 'Natural'
    JUR = 'Juridica'
    TYPE_CUSTOMER_ = [
        (NAT, 'Persona Natural'),
        (JUR, 'Persona Juridica'),
    ]

    MALE = 'Masculino'
    FEMALE = 'Femenino'
    OTHER = 'Otro'
    GENDER_ = [
        (MALE, 'Masculino'),
        (FEMALE, 'Femenino'),
        (OTHER, 'Otro'),
    ]

    name = models.CharField('Nombre',max_length=100)
    last_name = models.CharField('Apellido',max_length=100)
    dni = models.CharField('DNI',max_length=10, unique=True)
    email = models.EmailField('Correo',unique=True, blank=True, null=True)
    phone = models.CharField('Telefono',max_length=15, blank=True, null=True)
    address = models.TextField('Direccion',blank=True, null=True)
    type_customer = models.CharField('Tipo de Cliente', max_length=10, choices=TYPE_CUSTOMER_, default=NAT)
    gender = models.CharField('Genero', max_length=10, choices=GENDER_)

    def __str__(self):
        return f"{self.dni} - {self.name}"
    
    def full_name(self):
        return f'{self.name} {self.last_name}'
    
    def save(self):
        self.name = self.name.title()
        self.last_name = self.last_name.title()
        self.status = True
        super(Customer, self).save()
    
    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['name']

    def toggle_status(self):
        self.status = not self.status
        self.save()
        return self.status
    

class Sale(BaseModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    invoice_number = models.CharField('Numero de Factura', max_length=100, unique=True, editable=False) 
    date = models.DateField('Fecha de Venta', auto_now_add=True)
    observation = models.TextField('Observacion', blank=True, null=True)
    subtotal = models.DecimalField('Subtotal', max_digits=10, decimal_places=2, default=0.00)
    tax = models.DecimalField('Impuesto', max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    discount = models.DecimalField('Descuento', max_digits=10, decimal_places=2, default=0.00, null=True, blank=True)
    total_amount = models.DecimalField('Monto Total', max_digits=10, decimal_places=2, default=0.00)

    def __str__(self):
        return f'Venta {self.invoice_number} - {self.customer.full_name()} - {self.total_amount}'
    
    def save(self):
        # Generar número de factura solo para una nueva venta
        if not self.invoice_number:
            # Obtener el próximo número de forma segura
            next_number = ControlSequence.get_next_sequence_number('sale_invoice')
            # Formatear el número con ceros a la izquierda, e.g., 00001
            self.invoice_number = f"INV-{next_number:05d}"
        self.invoice_number = self.invoice_number.upper()
        self.total_amount = float(self.subtotal) - float(self.discount) + float(self.tax)
        return super(Sale, self).save()
    
    class Meta:
        verbose_name = 'Venta'
        verbose_name_plural = 'Ventas'
        ordering = ['-date']
        permissions = [
            ('supervisor_cashier_envoice',' Permiso para agregar o quitar elementos de una factura (devoluciones)')
            ]

    def toggle_status(self):
        self.status = not self.status
        self.save()
        return self.status

class SaleDetail(BaseModel):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='details')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField('Cantidad', default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Precio Unitario')
    tax = models.DecimalField('Impuesto', max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    discount = models.DecimalField('Descuento', max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    subtotal = models.DecimalField('SubTotal', max_digits=10, decimal_places=2)
    total_price = models.DecimalField('Precio Total', max_digits=10, decimal_places=2)

    def __str__(self):
        return f'{self.product.name} - {self.quantity} x {self.unit_price} = {self.total_price}'
    
    def save(self):
        self.subtotal = float(self.quantity) * float(self.unit_price)
        self.total_price = float(self.subtotal) + float(self.tax) - float(self.discount)
        return super(SaleDetail, self).save()
    
    class Meta:
        verbose_name = 'Detalle de Venta'
        verbose_name_plural = 'Detalles de Ventas'
        ordering = ['-sale__date']

        permissions = [
            ('supervisor_cashier_envoice_detail',' Permiso para agregar o quitar elementos de una factura (devoluciones)')
        ]


@receiver(post_delete, sender=SaleDetail)
def update_sale_delete(sender, instance, **kwargs):
    id_product = instance.product.id
    id_sale = instance.sale.id

    header = SaleDetail.objects.filter(pk=id_sale).first()
    if header:
            sub_total = SaleDetail.objects.filter(purchase_order=id_sale).aggregate(Sum('subtotal'))
            discount = SaleDetail.objects.filter(purchase_order=id_sale).aggregate(Sum('discount'))
            tax = SaleDetail.objects.filter(purchase_order=id_sale).aggregate(Sum('tax'))
            header.subtotal = sub_total["subtotal__sum"]
            header.discount = discount["discount__sum"]
            header.tax = tax["tax__sum"]
            header.save()
    
    product = Product.objects.filter(pk=id_product).first()
    if product:
        quantity = int(product.stock) + int(instance.quantity)
        product.stock = quantity
        product.save()

@receiver(post_save, sender=SaleDetail)
def update_sale_save(sender, instance, created, **kwargs):
    id_product = instance.product.id
    
    product = Product.objects.filter(pk=id_product).first()
    if product:
        quantity = float(product.stock) - float(instance.quantity)
        product.stock = quantity
        product.save()