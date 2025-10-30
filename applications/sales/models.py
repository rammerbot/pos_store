from django.db import models, transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from django.conf import settings

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


class DailyReport(BaseModel):
    """Modelo para registrar informes diarios generados"""
    report_date = models.DateField('Fecha del Reporte', unique=True)
    generated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    total_sales = models.DecimalField('Total Ventas', max_digits=10, decimal_places=2, default=0)
    total_customers = models.PositiveIntegerField('Total Clientes', default=0)
    total_products_sold = models.PositiveIntegerField('Total Productos Vendidos', default=0)
    opening_balance = models.DecimalField('Saldo Inicial', max_digits=10, decimal_places=2, default=0)
    closing_balance = models.DecimalField('Saldo Final', max_digits=10, decimal_places=2, default=0)
    cash_difference = models.DecimalField('Diferencia en Caja', max_digits=10, decimal_places=2, default=0)
    observations = models.TextField('Observaciones', blank=True, null=True)

    class Meta:
        verbose_name = 'Informe Diario'
        verbose_name_plural = 'Informes Diarios'
        ordering = ['-report_date']

    def __str__(self):
        return f'Informe {self.report_date}'

class CashRegister(BaseModel):
    """Modelo para control de caja"""
    CASH_IN = 'in'
    CASH_OUT = 'out'
    CASH_OPEN = 'open'
    CASH_CLOSE = 'close'
    
    OPERATION_TYPES = [
        (CASH_OPEN, 'Apertura de Caja'),
        (CASH_CLOSE, 'Cierre de Caja'),
        (CASH_IN, 'Ingreso de Efectivo'),
        (CASH_OUT, 'Retiro de Efectivo'),
    ]

    operation_type = models.CharField('Tipo de Operación', max_length=10, choices=OPERATION_TYPES)
    amount = models.DecimalField('Monto', max_digits=10, decimal_places=2)
    date = models.DateTimeField('Fecha y Hora', auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cash_register_movements')
    description = models.TextField('Descripción', blank=True, null=True)
    current_balance = models.DecimalField('Saldo Actual', max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Movimiento de Caja'
        verbose_name_plural = 'Movimientos de Caja'
        ordering = ['-date']

    def __str__(self):
        return f'{self.get_operation_type_display()} - ${self.amount} - {self.date.strftime("%d/%m/%Y %H:%M")}'

    def save(self, *args, **kwargs):
        # Asignar el usuario actual si no hay created_by
        if not self.created_by_id and hasattr(self, '_current_user'):
            self.created_by = self._current_user
        
        # Calcular saldo actual basado en movimientos anteriores
        if not self.pk:  # Solo para nuevos registros
            last_balance = CashRegister.objects.filter(
                status=True
            ).order_by('-date').values_list('current_balance', flat=True).first()
            
            if last_balance is None:
                last_balance = 0
            
            if self.operation_type == self.CASH_OPEN or self.operation_type == self.CASH_IN:
                self.current_balance = last_balance + self.amount
            elif self.operation_type == self.CASH_OUT:
                self.current_balance = last_balance - self.amount
            elif self.operation_type == self.CASH_CLOSE:
                self.current_balance = 0  # Al cerrar caja, el saldo vuelve a 0
        
        super().save(*args, **kwargs)
    """Modelo para control de caja"""
    CASH_IN = 'in'
    CASH_OUT = 'out'
    CASH_OPEN = 'open'
    CASH_CLOSE = 'close'
    
    OPERATION_TYPES = [
        (CASH_OPEN, 'Apertura de Caja'),
        (CASH_CLOSE, 'Cierre de Caja'),
        (CASH_IN, 'Ingreso de Efectivo'),
        (CASH_OUT, 'Retiro de Efectivo'),
    ]

    operation_type = models.CharField('Tipo de Operación', max_length=10, choices=OPERATION_TYPES)
    amount = models.DecimalField('Monto', max_digits=10, decimal_places=2)
    date = models.DateTimeField('Fecha y Hora', auto_now_add=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    description = models.TextField('Descripción', blank=True, null=True)
    current_balance = models.DecimalField('Saldo Actual', max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Movimiento de Caja'
        verbose_name_plural = 'Movimientos de Caja'
        ordering = ['-date']

    def __str__(self):
        return f'{self.get_operation_type_display()} - ${self.amount} - {self.date.strftime("%d/%m/%Y %H:%M")}'

    def save(self, *args, **kwargs):
        # Calcular saldo actual basado en movimientos anteriores
        if not self.pk:  # Solo para nuevos registros
            last_balance = CashRegister.objects.filter(
                status=True
            ).order_by('-date').values_list('current_balance', flat=True).first()
            
            if last_balance is None:
                last_balance = 0
            
            if self.operation_type == self.CASH_OPEN or self.operation_type == self.CASH_IN:
                self.current_balance = last_balance + self.amount
            elif self.operation_type == self.CASH_OUT:
                self.current_balance = last_balance - self.amount
            elif self.operation_type == self.CASH_CLOSE:
                self.current_balance = 0  # Al cerrar caja, el saldo vuelve a 0
        
        super().save(*args, **kwargs)