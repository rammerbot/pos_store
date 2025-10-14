import os
from datetime import datetime, date

from django.shortcuts import render
from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.template.loader import get_template
from django.db.models import Sum, Q, Count, Avg
from django.utils import timezone
from django.db.models.functions import TruncMonth

from xhtml2pdf import pisa

from .models import Sale, SaleDetail, Customer
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