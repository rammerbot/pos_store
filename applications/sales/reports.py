import os
from datetime import datetime, date, timedelta

from django.shortcuts import render,redirect
from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.template.loader import get_template
from django.db.models import Sum, Q, Count, Avg
from django.utils import timezone
from django.db.models.functions import TruncMonth
from django.db import models

from xhtml2pdf import pisa

from .models import Sale, SaleDetail, Customer, CashRegister, DailyReport
from applications.inv.models import Product, Category


def link_callback(uri, rel):
    """
    Convert HTML URIs to absolute system paths so xhtml2pdf can access those
    resources
    """
    result = finders.find(uri)

    if result:
        if not isinstance(result, (list, tuple)):
            result = [result]
        result = list(os.path.realpath(path) for path in result)
        path = result[0]
    else:
        static_url = settings.STATIC_URL    # Usually /static/
        static_root = settings.STATIC_ROOT  # Usually /home/user/project_static/
        media_url = settings.MEDIA_URL      # Usually /media/
        media_root = settings.MEDIA_ROOT    # Usually /home/user/project_static/media/

        if uri.startswith(media_url):
            path = os.path.join(media_root, uri.replace(media_url, ""))
        elif uri.startswith(static_url):
            path = os.path.join(static_root, uri.replace(static_url, ""))
        else:
            return uri

    # make sure that file exists
    if not os.path.isfile(path):
        raise RuntimeError(
            f'media URI must start with {static_url} or {media_url}'
        )
    return path


def sales_report_to_pdf(request):
    template_path = 'sales/sales_report.html'
    today = timezone.now()
    
    # Obtener parámetros de fecha del request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    # Filtrar ventas por rango de fechas si se proporciona
    sales = Sale.objects.all()
    
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            sales = sales.filter(date__range=[start_date, end_date])
        except ValueError:
            # Si hay error en el formato, usar todas las ventas
            pass
    
    # Calcular total general
    total_general = sales.aggregate(
        total_sum=Sum('total_amount'),
        subtotal_sum=Sum('subtotal'),
        discount_sum=Sum('discount'),
        tax_sum=Sum('tax'),
        count_sales=Count('id')
    )
    
    # Productos más vendidos por categoría
    top_products_by_category = SaleDetail.objects.filter(
        sale__in=sales
    ).values(
        'product__subcategory__category__name',
        'product__name',
        'product__code'
    ).annotate(
        total_vendido=Sum('quantity'),
        total_ingresos=Sum('total_price'),
        cantidad_ventas=Count('sale', distinct=True)
    ).order_by('product__subcategory__category__name', '-total_vendido')
    
    # Productos más vendidos por proveedor
    top_products_by_supplier = SaleDetail.objects.filter(
        sale__in=sales
    ).values(
        'product__brand__name',  # Asumiendo que brand representa al proveedor
        'product__name',
        'product__code'
    ).annotate(
        total_vendido=Sum('quantity'),
        total_ingresos=Sum('total_price'),
        cantidad_ventas=Count('sale', distinct=True),
        precio_promedio=Avg('unit_price')
    ).order_by('product__brand__name', '-total_vendido')
    
    # Ventas por categoría
    sales_by_category = SaleDetail.objects.filter(
        sale__in=sales
    ).values(
        'product__subcategory__category__name'
    ).annotate(
        total_ventas=Sum('quantity'),
        total_ingresos=Sum('total_price'),
        porcentaje_ingresos=Sum('total_price') * 100 / total_general['total_sum'] if total_general['total_sum'] else 0
    ).order_by('-total_ingresos')
    
    # Ventas por proveedor (marca)
    sales_by_supplier = SaleDetail.objects.filter(
        sale__in=sales
    ).values(
        'product__brand__name'
    ).annotate(
        total_ventas=Sum('quantity'),
        total_ingresos=Sum('total_price'),
        cantidad_productos=Count('product', distinct=True),
        porcentaje_ingresos=Sum('total_price') * 100 / total_general['total_sum'] if total_general['total_sum'] else 0
    ).order_by('-total_ingresos')
    
    # Ventas por cliente
    sales_by_customer = sales.values(
        'customer__id',
        'customer__name',
        'customer__last_name'
    ).annotate(
        total_compras=Sum('total_amount'),
        subtotal_compras=Sum('subtotal'),
        discount_compras=Sum('discount'),
        tax_compras=Sum('tax'),
        cantidad_compras=Count('id')
    ).order_by('-total_compras')[:10]  # Top 10 clientes
    
    # Ventas mensuales (para tendencia)
    monthly_sales = sales.annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total_ventas=Sum('total_amount'),
        cantidad_ventas=Count('id')
    ).order_by('month')
    
    # Productos con mejor margen (basado en precio de venta vs último precio de compra)
    high_margin_products = SaleDetail.objects.filter(
        sale__in=sales
    ).values(
        'product__name',
        'product__code',
        'product__brand__name'
    ).annotate(
        precio_venta_promedio=Avg('unit_price'),
        cantidad_vendida=Sum('quantity'),
        total_ingresos=Sum('total_price')
    ).order_by('-cantidad_vendida')[:15]
    
    # Calcular métricas adicionales
    avg_sale_value = total_general['total_sum'] / total_general['count_sales'] if total_general['count_sales'] > 0 else 0
    discount_percentage = (total_general['discount_sum'] / total_general['subtotal_sum'] * 100) if total_general['subtotal_sum'] > 0 else 0

    context = {
        'sales': sales,
        'top_products_by_category': top_products_by_category,
        'top_products_by_supplier': top_products_by_supplier,
        'sales_by_category': sales_by_category,
        'sales_by_supplier': sales_by_supplier,
        'sales_by_customer': sales_by_customer,
        'monthly_sales': monthly_sales,
        'high_margin_products': high_margin_products,
        'today': today,
        'total_general': total_general['total_sum'] or 0,
        'subtotal_general': total_general['subtotal_sum'] or 0,
        'discount_general': total_general['discount_sum'] or 0,
        'tax_general': total_general['tax_sum'] or 0,
        'count_sales': total_general['count_sales'] or 0,
        'avg_sale_value': avg_sale_value,
        'discount_percentage': discount_percentage,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'request': request,
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_ventas_analitico.pdf"'
    template = get_template(template_path)
    html = template.render(context)
    
    # create a pdf
    pisa_status = pisa.CreatePDF(
       html,
       dest=response,
       link_callback=link_callback,
    )

    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')

    return response


def sales_report_filter(request):
    """Vista para mostrar el formulario de filtros del reporte de ventas"""
    return render(request, 'sales/report_filter.html')


def print_sale_invoice(request, sale_id):
    """Generar PDF de factura individual de venta"""
    template_path = 'sales/print_sale_invoice.html'
    today = timezone.now()
    
    # Obtener la venta específica
    try:
        sale = Sale.objects.get(id=sale_id)
    except Sale.DoesNotExist:
        return HttpResponse('Venta no encontrada')
    
    sale_items = SaleDetail.objects.filter(sale=sale)
    
    context = {
        'sale': sale,
        'items': sale_items,
        'today': today,
        'request': request,
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="factura_venta_{sale.invoice_number}.pdf"'
    template = get_template(template_path)
    html = template.render(context)
    
    # create a pdf
    pisa_status = pisa.CreatePDF(
       html,
       dest=response,
       link_callback=link_callback,
    )

    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')

    return response

def print_invoice(request, id):
    template_name = 'sales/print_invoice.html'

    header = Sale.objects.get(id=id)
    detail = SaleDetail.objects.filter(sale=header)

    context = {
        'request':request,
        'header':header,
        'detail':detail,
    }

    return render(request, template_name, context)

def generate_budget_pdf(request):
    """Generar PDF del presupuesto"""
    template_path = 'sales/budget_pdf.html'
    
    if request.method == 'POST':
        # Obtener datos del formulario
        customer_data = {
            'name': request.POST.get('customer_name', ''),
            'dni': request.POST.get('customer_dni', ''),
            'phone': request.POST.get('customer_phone', ''),
            'email': request.POST.get('customer_email', ''),
            'address': request.POST.get('customer_address', ''),
        }
        
        observation = request.POST.get('observation', '')
        validity_days = request.POST.get('validity_days', 30)
        subtotal = request.POST.get('subtotal', 0)
        discount = request.POST.get('discount', 0)
        tax = request.POST.get('tax', 0)
        total_amount = request.POST.get('total_amount', 0)
        
        # Obtener items del presupuesto
        budget_items = []
        item_count = int(request.POST.get('item_count', 0))
        
        for i in range(item_count):
            product_name = request.POST.get(f'items[{i}][product_name]')
            quantity = request.POST.get(f'items[{i}][quantity]')
            unit_price = request.POST.get(f'items[{i}][unit_price]')
            item_subtotal = request.POST.get(f'items[{i}][subtotal]')
            
            if product_name and quantity and unit_price:
                budget_items.append({
                    'product_name': product_name,
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'subtotal': item_subtotal,
                })
        
        # Usar datetime.now() para obtener fecha y hora completas
        today_date = datetime.now().date()
        now_datetime = datetime.now()
        valid_until = now_datetime + timedelta(days=int(validity_days))
        
        context = {
            'customer': customer_data,
            'observation': observation,
            'validity_days': validity_days,
            'budget_items': budget_items,
            'subtotal': subtotal,
            'discount': discount,
            'tax': tax,
            'total_amount': total_amount,
            'today': today_date,  # Solo fecha para el encabezado
            'now': now_datetime,  # Fecha y hora completa para el pie de página
            'valid_until': valid_until.date(),
            'budget_number': f"PRE-{datetime.now().strftime('%Y%m%d')}-{request.user.id}",
        }

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="presupuesto.pdf"'
        template = get_template(template_path)
        html = template.render(context)
        
        pisa_status = pisa.CreatePDF(
           html,
           dest=response,
           link_callback=link_callback,
        )

        if pisa_status.err:
            return HttpResponse('We had some errors <pre>' + html + '</pre>')

        return response
    
    return redirect('sales:create_budget')

def daily_sales_report_to_pdf(request):
    """Generar PDF del informe diario de ventas"""
    template_path = 'sales/daily_sales_report.html'
    
    # Obtener la fecha del request o usar hoy por defecto
    date_param = request.GET.get('date')
    if date_param:
        try:
            selected_date = datetime.strptime(date_param, '%Y-%m-%d').date()
        except ValueError:
            selected_date = datetime.now().date()
    else:
        selected_date = datetime.now().date()
    
    now = datetime.now()
    
    # Filtrar ventas de la fecha seleccionada
    sales_today = Sale.objects.filter(date=selected_date, status=True)
    
    # Obtener información de caja del día seleccionado
    start_of_day = datetime.combine(selected_date, datetime.min.time())
    end_of_day = datetime.combine(selected_date, datetime.max.time())
    
    cash_movements = CashRegister.objects.filter(
        date__range=(start_of_day, end_of_day), 
        status=True
    )
    opening_balance = cash_movements.filter(operation_type=CashRegister.CASH_OPEN).aggregate(Sum('amount'))['amount__sum'] or 0
    cash_ins = cash_movements.filter(operation_type=CashRegister.CASH_IN).aggregate(Sum('amount'))['amount__sum'] or 0
    cash_outs = cash_movements.filter(operation_type=CashRegister.CASH_OUT).aggregate(Sum('amount'))['amount__sum'] or 0
    
    # Obtener último saldo registrado
    last_movement = cash_movements.order_by('-date').first()
    current_balance = last_movement.current_balance if last_movement else 0
    
    # Calcular diferencia en caja
    expected_balance = opening_balance + (sales_today.aggregate(Sum('total_amount'))['total_amount__sum'] or 0) + cash_ins - cash_outs
    cash_difference = current_balance - expected_balance
    
    # Calcular totales del día
    daily_totals = sales_today.aggregate(
        total_sum=Sum('total_amount'),
        subtotal_sum=Sum('subtotal'),
        discount_sum=Sum('discount'),
        tax_sum=Sum('tax'),
        count_sales=Count('id')
    )
    
    # PRODUCTOS VENDIDOS CON DETALLE COMPLETO
    products_sold_today = SaleDetail.objects.filter(
        sale__in=sales_today,
        status=True
    ).values(
        'product__id',
        'product__name',
        'product__code',
        'product__brand__name',  # Proveedor
        'product__last_purchase_price',  # Costo de compra
        'unit_price'  # Precio de venta unitario
    ).annotate(
        total_quantity=Sum('quantity'),
        total_sales_amount=Sum('total_price'),
        total_cost=Sum('quantity') * models.F('product__last_purchase_price'),
        total_profit=Sum('total_price') - (Sum('quantity') * models.F('product__last_purchase_price'))
    ).order_by('-total_quantity')
    
    # Calcular totales generales de productos
    total_products_summary = products_sold_today.aggregate(
        total_quantity_all=Sum('total_quantity'),
        total_sales_all=Sum('total_sales_amount'),
        total_cost_all=Sum('total_cost'),
        total_profit_all=Sum('total_profit')
    )
    
    # RESUMEN POR PROVEEDOR
    supplier_summary = SaleDetail.objects.filter(
        sale__in=sales_today,
        status=True
    ).values(
        'product__brand__name'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_sales=Sum('total_price'),
        total_cost=Sum('quantity') * models.F('product__last_purchase_price'),
        total_profit=Sum('total_price') - (Sum('quantity') * models.F('product__last_purchase_price'))
    ).order_by('-total_sales')
    
    # Productos más vendidos (versión simplificada)
    top_products_today = products_sold_today[:10]
    
    # Clientes que más compraron hoy
    top_customers_today = sales_today.values(
        'customer__id',
        'customer__name',
        'customer__last_name'
    ).annotate(
        total_compras=Sum('total_amount'),
        cantidad_compras=Count('id')
    ).order_by('-total_compras')[:5]
    
    # Guardar registro del informe
    if sales_today.exists() or cash_movements.exists():
        total_products_sold = products_sold_today.aggregate(Sum('total_quantity'))['total_quantity__sum'] or 0
        
        try:
            daily_report, created = DailyReport.objects.get_or_create(
                report_date=selected_date,
                defaults={
                    'generated_by': request.user,
                    'total_sales': daily_totals['total_sum'] or 0,
                    'total_customers': sales_today.values('customer').distinct().count(),
                    'total_products_sold': total_products_sold,
                    'opening_balance': opening_balance,
                    'closing_balance': current_balance,
                    'cash_difference': cash_difference,
                    'created_by': request.user,
                }
            )
            
            if not created:
                daily_report.generated_by = request.user
                daily_report.total_sales = daily_totals['total_sum'] or 0
                daily_report.total_customers = sales_today.values('customer').distinct().count()
                daily_report.total_products_sold = total_products_sold
                daily_report.opening_balance = opening_balance
                daily_report.closing_balance = current_balance
                daily_report.cash_difference = cash_difference
                daily_report.modified_by = request.user.id
                daily_report.save()
                
        except Exception as e:
            print(f"Error al guardar DailyReport: {e}")
    
    context = {
        'sales_today': sales_today,
        'products_sold_today': products_sold_today,
        'top_products_today': top_products_today,
        'top_customers_today': top_customers_today,
        'supplier_summary': supplier_summary,
        'total_products_summary': total_products_summary,
        'today': selected_date,  # Usar la fecha seleccionada
        'selected_date': selected_date,  # Nueva variable para el template
        'now': now,
        'total_general': daily_totals['total_sum'] or 0,
        'subtotal_general': daily_totals['subtotal_sum'] or 0,
        'discount_general': daily_totals['discount_sum'] or 0,
        'tax_general': daily_totals['tax_sum'] or 0,
        'count_sales': daily_totals['count_sales'] or 0,
        'avg_sale_value': daily_totals['total_sum'] / daily_totals['count_sales'] if daily_totals['count_sales'] > 0 else 0,
        'opening_balance': opening_balance,
        'cash_ins': cash_ins,
        'cash_outs': cash_outs,
        'current_balance': current_balance,
        'cash_difference': cash_difference,
        'cash_movements': cash_movements,
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="reporte_ventas_diario_{selected_date}.pdf"'
    template = get_template(template_path)
    html = template.render(context)
    
    pisa_status = pisa.CreatePDF(
       html,
       dest=response,
       link_callback=link_callback,
    )

    if pisa_status.err:
       return HttpResponse('We had some errors <pre>' + html + '</pre>')

    return response