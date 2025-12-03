# applications/sales/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal
from .models import Sale, CashRegister


@receiver(post_save, sender=Sale)
def handle_sale_cash_movement(sender, instance, created, **kwargs):
    """
    Signal ÚNICO y DEFINITIVO para el control de caja.
    - Registra ventas nuevas
    - Ajusta montos al modificar
    - Crea devoluciones/anulaciones
    - Siempre con status=True → visible en historial
    """
    
    # =============================================
    # 1. VENTA NUEVA + ACTIVA → Crear CASH_IN (el que SÍ funcionaba)
    # =============================================
    if created and instance.status and instance.total_amount > 0:
        open_register = CashRegister.objects.filter(
            operation_type=CashRegister.CASH_OPEN,
            status=True
        ).first()

        if open_register:
            new_movement = CashRegister.objects.create(
                operation_type=CashRegister.CASH_IN,
                amount=instance.total_amount,
                user=instance.created_by,
                description=f"Venta {instance.invoice_number} - {instance.customer.full_name()}",
                created_by=instance.created_by,
                date=timezone.now(),
                status=True  # ← Crucial: aparece en la tabla
            )
            # Vincular inmediatamente
            instance.cash_movement = new_movement
            instance.save(update_fields=['cash_movement'])
        return  # ← Salir aquí si es venta nueva

    # =============================================
    # 2. VENTA ANULADA → Crear CASH_OUT y desvincular
    # =============================================
    if not instance.status:
        if hasattr(instance, 'cash_movement') and instance.cash_movement:
            movement = instance.cash_movement
            if movement.operation_type == CashRegister.CASH_IN:
                _create_reverse_movement(
                    sale=instance,
                    amount=movement.amount,
                    reason=f"Anulación completa - Factura {instance.invoice_number}"
                )
            # Desvincular
            Sale.objects.filter(pk=instance.pk).update(cash_movement=None)
        return

    # =============================================
    # 3. VERIFICAR QUE HAYA CAJA ABIERTA (para modificaciones)
    # =============================================
    if not CashRegister.objects.filter(operation_type=CashRegister.CASH_OPEN, status=True).exists():
        return

    # =============================================
    # 4. VENTA MODIFICADA → Ajustar movimientos
    # =============================================
    if hasattr(instance, 'cash_movement') and instance.cash_movement:
        movement = instance.cash_movement
        old_amount = movement.amount
        new_amount = Decimal(str(instance.total_amount))

        if old_amount != new_amount:
            diff = new_amount - old_amount

            if diff > 0:
                # Se agregó producto → ingreso adicional
                CashRegister.objects.create(
                    operation_type=CashRegister.CASH_IN,
                    amount=diff,
                    user=instance.modified_by or instance.created_by,
                    description=f"Ajuste +${diff:,.2f} - Venta {instance.invoice_number}",
                    created_by=instance.modified_by or instance.created_by,
                    date=timezone.now(),
                    status=True
                )
            elif diff < 0:
                # Se quitó producto → devolución parcial
                _create_reverse_movement(
                    sale=instance,
                    amount=-diff,
                    reason=f"Devolución parcial - Factura {instance.invoice_number}"
                )

            # Actualizar el movimiento principal
            movement.amount = new_amount
            movement.description = f"Venta {instance.invoice_number} - {instance.customer.full_name()}"
            movement.status = True
            movement.save()

    # =============================================
    # 5. VENTA NUEVA SIN MOVIMIENTO (por si falla el primer if)
    # =============================================
    elif not hasattr(instance, 'cash_movement') or not instance.cash_movement:
        if instance.total_amount > 0:
            new_movement = CashRegister.objects.create(
                operation_type=CashRegister.CASH_IN,
                amount=instance.total_amount,
                user=instance.created_by,
                description=f"Venta {instance.invoice_number} - {instance.customer.full_name()}",
                created_by=instance.created_by,
                date=timezone.now(),
                status=True
            )
            Sale.objects.filter(pk=instance.pk).update(cash_movement=new_movement)


# =============================================
# FUNCIÓN AUXILIAR: Crea CASH_OUT sin duplicados
# =============================================
def _create_reverse_movement(sale, amount, reason):
    """Crea un retiro seguro y visible"""
    if amount <= 0:
        return

    today = timezone.now().date()

    # Evitar duplicados exactos
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
            date=timezone.now(),
            status=True  # ← Siempre visible en el historial
        )