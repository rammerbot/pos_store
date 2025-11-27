# applications/sales/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from .models import Sale, CashRegister


@receiver(post_save, sender=Sale)
def handle_sale_cash_movement(sender, instance, created, **kwargs):
    """
    ÚNICO signal responsable del control de caja.
    - Crea CASH_IN al hacer una venta
    - Crea CASH_OUT al reducir o anular una venta
    - Ajusta automáticamente si se agrega/quita productos
    """
    # =============================================
    # 1. VENTA ANULADA → RESTAR TODO
    # =============================================
    if not instance.status:
        if instance.cash_movement and instance.cash_movement.operation_type == CashRegister.CASH_IN:
            amount = instance.cash_movement.amount
            _create_reverse_movement(
                sale=instance,
                amount=amount,
                reason=f"Anulación completa de venta {instance.invoice_number}"
            )
            # Romper vínculo
            Sale.objects.filter(pk=instance.pk).update(cash_movement=None)
        return

    # =============================================
    # 2. VERIFICAR QUE HAYA CAJA ABIERTA
    # =============================================
    today = timezone.now().date()
    if not CashRegister.objects.filter(
        operation_type=CashRegister.CASH_OPEN,
        date__date=today,
        status=True
    ).exists():
        return

    # =============================================
    # 3. YA EXISTE UN MOVIMIENTO ASOCIADO (venta ya estaba registrada)
    # =============================================
    if instance.cash_movement:
        movement = instance.cash_movement
        old_amount = movement.amount
        new_amount = Decimal(str(instance.total_amount))  # Seguro contra float

        # Solo actuar si el monto cambió
        if old_amount != new_amount:
            if new_amount > old_amount:
                # Se agregó producto → ingreso adicional
                diff = new_amount - old_amount
                CashRegister.objects.create(
                    operation_type=CashRegister.CASH_IN,
                    amount=diff,
                    user=instance.modified_by or instance.created_by,
                    description=f"Ajuste por aumento en venta {instance.invoice_number}",
                    created_by=instance.modified_by or instance.created_by,
                    date=timezone.now()
                )
            else:
                # Se quitó producto o se anuló parcialmente → devolución
                diff = old_amount - new_amount
                _create_reverse_movement(
                    sale=instance,
                    amount=diff,
                    reason=f"Devolución parcial - Factura {instance.invoice_number}"
                )

            # Actualizar el movimiento original de la venta
            movement.amount = new_amount
            movement.description = f"Venta {instance.invoice_number} - {instance.customer.full_name()}"
            movement.save()

    # =============================================
    # 4. VENTA NUEVA → CREAR CASH_IN
    # =============================================
    else:
        CashRegister.objects.create(
            operation_type=CashRegister.CASH_IN,
            amount=instance.total_amount,
            user=instance.created_by,
            description=f"Venta {instance.invoice_number} - {instance.customer.full_name()}",
            created_by=instance.created_by,
            date=timezone.now()
        )

        # Vincular el movimiento recién creado
        movement = CashRegister.objects.filter(
            operation_type=CashRegister.CASH_IN,
            amount=instance.total_amount,
            description__contains=instance.invoice_number
        ).order_by('-id').first()

        if movement:
            Sale.objects.filter(pk=instance.pk).update(cash_movement=movement)


# =============================================
# FUNCIÓN AUXILIAR: Crea CASH_OUT sin duplicados
# =============================================
def _create_reverse_movement(sale, amount, reason):
    """Crea un retiro de efectivo por devolución o anulación"""
    if amount <= 0:
        return

    today = timezone.now().date()

    # Evitar duplicados exactos (misma descripción + monto + día)
    exists = CashRegister.objects.filter(
        operation_type=CashRegister.CASH_OUT,
        amount=amount,
        description=reason,
        date__date=today
    ).exists()

    if not exists:
        CashRegister.objects.create(
            operation_type=CashRegister.CASH_OUT,
            amount=amount,
            user=sale.modified_by or sale.created_by,
            description=reason,
            created_by=sale.modified_by or sale.created_by,
            date=timezone.now()
        )