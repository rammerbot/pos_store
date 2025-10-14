import os
from datetime import datetime

from django.shortcuts import render
from django.conf import settings
from django.contrib.staticfiles import finders
from django.http import HttpResponse
from django.template.loader import get_template
from django.utils import timezone
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth

from xhtml2pdf import pisa

from .models import PurchaseOrder, PurchaseItem, Supplier


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



def purshase_repotr_to_pdf(request):
    template_path = 'purchases/purchase_report.html'
    today = timezone.now()
    
    # Obtener parámetros de fecha del request
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    
    # Filtrar compras por rango de fechas si se proporciona
    purchases = PurchaseOrder.objects.all()
    
    if start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            purchases = purchases.filter(buy_date__range=[start_date, end_date])
        except ValueError:
            # Si hay error en el formato, usar todas las compras
            pass
    
    # Calcular total general
    total_general = purchases.aggregate(
        total_sum=Sum('total_amount'),
        subtotal_sum=Sum('subtotal'),
        discount_sum=Sum('discount'),
        tax_sum=Sum('tax'),
        count_purchases=Count('id')
    )
    
    # Agrupar compras por proveedor
    suppliers_totals = purchases.values(
        'supplier__id',
        'supplier__name'
    ).annotate(
        total_compras=Sum('total_amount'),
        subtotal_compras=Sum('subtotal'),
        discount_compras=Sum('discount'),
        tax_compras=Sum('tax'),
        cantidad_compras=Count('id')
    ).order_by('-total_compras')

    # Calcular porcentaje para cada proveedor
    for supplier in suppliers_totals:
        if total_general['total_sum'] and total_general['total_sum'] > 0:
            supplier['porcentaje_total'] = (supplier['total_compras'] / total_general['total_sum']) * 100
        else:
            supplier['porcentaje_total'] = 0

    # Productos más comprados por proveedor
    top_products_by_supplier = PurchaseItem.objects.filter(
        purchase_order__in=purchases
    ).values(
        'product__brand__name',
        'product__name',
        'product__code'
    ).annotate(
        total_comprado=Sum('quantity'),
        total_costo=Sum('total_price'),
        precio_promedio=Avg('unit_price'),
        cantidad_compras=Count('purchase_order', distinct=True)
    ).order_by('product__brand__name', '-total_comprado')

    # Productos más comprados por categoría
    top_products_by_category = PurchaseItem.objects.filter(
        purchase_order__in=purchases
    ).values(
        'product__subcategory__category__name',
        'product__name',
        'product__brand__name'
    ).annotate(
        total_comprado=Sum('quantity'),
        total_costo=Sum('total_price'),
        precio_promedio=Avg('unit_price')
    ).order_by('product__subcategory__category__name', '-total_comprado')

    # Tendencias mensuales
    monthly_purchases = purchases.annotate(
        month=TruncMonth('buy_date')
    ).values('month').annotate(
        total_compras=Sum('total_amount'),
        cantidad_compras=Count('id'),
        promedio_orden=Avg('total_amount')
    ).order_by('month')

    # Calcular tendencias
    monthly_list = list(monthly_purchases)
    for i in range(1, len(monthly_list)):
        previous = monthly_list[i-1]['total_compras'] or 1
        current = monthly_list[i]['total_compras'] or 0
        monthly_list[i]['tendencia'] = ((current - previous) / previous) * 100
    if monthly_list:
        monthly_list[0]['tendencia'] = 0

    # Calcular métricas adicionales
    avg_purchase_value = total_general['total_sum'] / total_general['count_purchases'] if total_general['count_purchases'] > 0 else 0
    discount_percentage = (total_general['discount_sum'] / total_general['subtotal_sum'] * 100) if total_general['subtotal_sum'] > 0 else 0

    context = {
        'purchases': purchases,
        'suppliers_totals': suppliers_totals,
        'top_products_by_supplier': top_products_by_supplier,
        'top_products_by_category': top_products_by_category,
        'monthly_purchases': monthly_list,
        'today': today,
        'total_general': total_general['total_sum'] or 0,
        'subtotal_general': total_general['subtotal_sum'] or 0,
        'discount_general': total_general['discount_sum'] or 0,
        'tax_general': total_general['tax_sum'] or 0,
        'count_purchases': total_general['count_purchases'] or 0,
        'avg_purchase_value': avg_purchase_value,
        'discount_percentage': discount_percentage,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'request': request,
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'inline; filename="reporte_compras_analitico.pdf"'
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

def purchase_report_filter(request):
    """Vista para mostrar el formulario de filtros del reporte"""
    return render(request, 'purchases/report_filter.html')

def print_purchase_report(request, purchase_id):
    template_path = 'purchases/print_purchase_report.html'
    today = timezone.now()
    
    # Obtener la compra específica
    try:
        purchase = PurchaseOrder.objects.get(id=purchase_id)
    except PurchaseOrder.DoesNotExist:
        return HttpResponse('Purchase not found')
    
    purchase_items = PurchaseItem.objects.filter(purchase_order=purchase)
    
    context = {
        'obj': [purchase],  # Pasar como lista para mantener consistencia en la plantilla
        'items': purchase_items,
        'today': today,
        'total_general': purchase.total_amount,
        'subtotal_general': purchase.subtotal,
        'discount_general': purchase.discount,
        'tax_general': purchase.tax,
        'request': request,
    }

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="reporte_compra_{purchase.order_number}.pdf"'
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
