from datetime import datetime, timedelta
import json
from decimal import Decimal, InvalidOperation
from xhtml2pdf import pisa

from django.contrib import messages
from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, View, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse
from django.template.loader import get_template
from django.conf import settings


from .models import Customer, Sale, SaleDetail, CashRegister
from applications.inv.models import Product
from .forms import CustomerForm, SaleForm, CashRegisterForm
from applications.home.mixins import AdminRequiredMixin, SellerRequiredMixin
from .forms import CustomerForm, SaleForm



# Create your views here.
class CustomerListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Customer
    template_name = 'sales/customers_list.html'
    context_object_name = 'customers'
    login_url = reverse_lazy('home:login')

class CreateCustomerView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'sales/customer_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('sales:customers_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Es una solicitud AJAX
            self.object = form.save()
            return JsonResponse({
                'success': True, 
                'message': 'Cliente Cargado exitosamente'
            })
        else:
            # Solicitud normal
            return super().form_valid(form)
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Es una solicitud AJAX - regresar el formulario con errores
            html = render_to_string(self.template_name, {
                'form': form, 
                'customer': self.object
            }, request=self.request)
            return JsonResponse({
                'success': False, 
                'html': html
            })
        else:
            # Solicitud normal
            return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('sales:customers_list')
    
class ToggleCustomerStatusView(AdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        customer_id = request.POST.get('customer_id')
        try:
            customer = Customer.objects.get(id=customer_id)
            new_status = customer.toggle_status()
            return JsonResponse({'success': True, 'new_status': new_status})
        except Customer.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Cliente no encontrada'})
        
class UpdateCustomerView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Customer
    form_class = CustomerForm
    template_name = 'sales/customer_form.html'
    login_url = reverse_lazy('home:login')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Es una solicitud AJAX
            self.object = form.save()
            return JsonResponse({
                'success': True, 
                'message': 'Proveedor actualizado exitosamente'
            })
        else:
            # Solicitud normal
            return super().form_valid(form)
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Es una solicitud AJAX - regresar el formulario con errores
            html = render_to_string(self.template_name, {
                'form': form, 
                'customer': self.object
            }, request=self.request)
            return JsonResponse({
                'success': False, 
                'html': html
            })
        else:
            # Solicitud normal
            return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('sales:customers_list')
    
class SalesListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = 'sales/sales_list.html'
    context_object_name = 'sales'
    login_url = reverse_lazy('home:login')

    def get(self, request, *args, **kwargs):
        # Verificar estado de la caja
        today = datetime.now().date()
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        # Verificar si hay caja abierta HOY
        is_cash_open_today = CashRegister.objects.filter(
            operation_type=CashRegister.CASH_OPEN,
            date__range=(start_of_day, end_of_day),
            status=True,
            user=request.user
        ).exists()

        if not is_cash_open_today:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'No hay caja abierta hoy. Debe abrir una para realizar ventas.'
                }, status=403)
            else:
                messages.error(request, 'No hay caja abierta hoy. Debe abrir una para realizar ventas.')
                return redirect('sales:cash_register')
        
        return super().get(request, *args, **kwargs)

@login_required(login_url='/login/')
def sale_order_view(request, sale_id=None):
     # Verificar estado de la caja
    today = datetime.now().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    
    # Verificar si hay caja abierta HOY
    is_cash_open_today = CashRegister.objects.filter(
        operation_type=CashRegister.CASH_OPEN,
        date__range=(start_of_day, end_of_day),
        status=True,
        user=request.user
    ).exists()

    if not is_cash_open_today:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'No hay caja abierta hoy. Debe abrir una para realizar ventas.'
            }, status=403)
        else:
            messages.error(request, 'No hay caja abierta hoy. Debe abrir una para realizar ventas.')
            return redirect('sales:cash_register')

    template_name = "sales/sale.html"
    products = Product.objects.filter(status=True)
    customers = Customer.objects.filter(status=True)
    sale_form = {}
    context = {}

    if request.method =='GET':
        sale_form = SaleForm()
        header = Sale.objects.filter(pk=sale_id).first() if sale_id else None

        if header:
            sale_item = SaleDetail.objects.filter(sale=header)
            e = {
                'customer': header.customer,
                'observation': header.observation,
                'invoice_number': header.invoice_number,
                'subtotal': header.subtotal,
                'discount': header.discount,
                'tax': header.tax,
                'total_amount': header.total_amount
            }

            sale_form = SaleForm(e)
        else:
            sale_item = None
        
        context = {'products': products, 'header': header, 'sale_items': sale_item, 'sale_form': sale_form, 'customers': customers}
 

    if request.method == 'POST':
        observation = request.POST.get("observation")
        customer = request.POST.get("customer")
        print_invoice = request.POST.get("print_invoice") == 'true'
       
        if not sale_id:
            customer_ = Customer.objects.get(pk=customer)

            header = Sale(
                observation=observation,
                customer=customer_,
                created_by=request.user
            )
            if header:
                header.save()
                sale_id = header.id
                
                # Procesar múltiples productos si existen
                products_data = request.POST.get("products_data")
                if products_data:
                    products_added = process_multiple_sale_products(header, products_data, request.user)
                    if products_added:
                        update_sale_totals(header)
                
                # SI SE SOLICITA IMPRIMIR, DEVOLVER URL DE IMPRESIÓN
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    if print_invoice:
                        return JsonResponse({
                            'success': True,
                            'message': 'Factura creada exitosamente',
                            'invoice_number': header.invoice_number,
                            'total_amount': str(header.total_amount),
                            'print_url': reverse_lazy('sales:print_invoice', kwargs={'sale_id': header.id}),
                            'redirect_url': f'/sales/sales/update/{sale_id}/'
                        })
                    else:
                        return JsonResponse({
                            'success': True,
                            'message': 'Factura creada exitosamente',
                            'redirect_url': f'/sales/sales/update/{sale_id}/'
                        })
                else:
                    if print_invoice:
                        return redirect("sales:print_invoice", sale_id=sale_id)
                    else:
                        return redirect("sales:sale_update", sale_id=sale_id)
        else:
            header = Sale.objects.filter(pk=sale_id).first()
            if header:
                header.observation = observation
                header.modified_by = request.user.id
                header.save()
        
        # PROCESAR MÚLTIPLES PRODUCTOS (para facturas existentes)
        products_data = request.POST.get("products_data")
        if products_data:
            products_added = process_multiple_sale_products(header, products_data, request.user)
            if products_added > 0:
                update_sale_totals(header)
                
                # SI SE SOLICITA IMPRIMIR, DEVOLVER URL DE IMPRESIÓN
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    if print_invoice:
                        return JsonResponse({
                            'success': True,
                            'message': f'{products_added} productos agregados correctamente',
                            'invoice_number': header.invoice_number,
                            'total_amount': str(header.total_amount),
                            'print_url': reverse_lazy('sales:print_invoice', kwargs={'sale_id': header.id}),
                            'updated_totals': {
                                'subtotal': str(header.subtotal),
                                'discount': str(header.discount),
                                'tax': str(header.tax),
                                'total_amount': str(header.total_amount),
                            }
                        })
                    else:
                        return JsonResponse({
                            'success': True,
                            'message': f'{products_added} productos agregados correctamente',
                            'updated_totals': {
                                'subtotal': str(header.subtotal),
                                'discount': str(header.discount),
                                'tax': str(header.tax),
                                'total_amount': str(header.total_amount),
                            }
                        })
                else:
                    messages.success(request, f'{products_added} productos agregados correctamente.')
                    if print_invoice:
                        return redirect("sales:print_invoice", sale_id=sale_id)
                    else:
                        return redirect("sales:sale_update", sale_id=sale_id)
            else:
                error_msg = 'No se pudieron agregar los productos'
        
        # MANTENER COMPATIBILIDAD CON EL SISTEMA ANTIGUO (un solo producto)
        individual_product = request.POST.get("id_id_producto")
        if individual_product:
            product = individual_product
            quantity = request.POST.get("id_cantidad_detalle")
            price = request.POST.get("id_precio_detalle")
            subtotal = request.POST.get("id_sub_total_detalle")
            discount = request.POST.get("id_descuento_detalle")
            tax = request.POST.get("id_impuesto")
            total_amount = request.POST.get("id_total_detalle")
            
            # Validar que todos los campos necesarios estén presentes
            if not all([product, quantity, price, subtotal, total_amount]):
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'Faltan campos requeridos'
                    })
                return redirect("sales:sale_update", sale_id=sale_id)
            
            try:
                prod = Product.objects.get(pk=product)
                
                det = SaleDetail(
                    sale=header,
                    product=prod,
                    quantity=quantity,
                    unit_price=price,
                    discount=discount or 0,
                    subtotal=subtotal,
                    tax=tax or 0,
                    total_price=total_amount,
                    created_by=request.user
                )

                if det:
                    det.save()
                    # Recalcular totales
                    update_sale_totals(header)

                    # Si es AJAX, devolver JSON
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        if print_invoice:
                            return JsonResponse({
                                'success': True,
                                'message': 'Producto agregado correctamente',
                                'invoice_number': header.invoice_number,
                                'total_amount': str(header.total_amount),
                                'print_url': reverse_lazy('sales:print_invoice', kwargs={'sale_id': header.id}),
                                'updated_totals': {
                                    'subtotal': str(header.subtotal),
                                    'discount': str(header.discount),
                                    'tax': str(header.tax),
                                    'total_amount': str(header.total_amount),
                                }
                            })
                        else:
                            return JsonResponse({
                                'success': True,
                                'message': 'Producto agregado correctamente',
                                'updated_totals': {
                                    'subtotal': str(header.subtotal),
                                    'discount': str(header.discount),
                                    'tax': str(header.tax),
                                    'total_amount': str(header.total_amount),
                                }
                            })
                    else:
                        messages.success(request, 'Producto agregado correctamente.')
                        if print_invoice:
                            return redirect("sales:print_invoice", sale_id=sale_id)
                        else:
                            return redirect("sales:sale_update", sale_id=sale_id)
            
            except Product.DoesNotExist:
                error_msg = 'Producto no encontrado'
            except Exception as e:
                error_msg = f'Error al guardar: {str(e)}'
            
            # Manejar errores
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': error_msg
                })
            else:
                messages.error(request, error_msg)
                return redirect("sales:sale_update", sale_id=sale_id)
        
        else:
            # No hay productos para agregar, solo actualizar la cabecera
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if print_invoice:
                    return JsonResponse({
                        'success': True,
                        'message': 'Factura actualizada correctamente',
                        'invoice_number': header.invoice_number,
                        'total_amount': str(header.total_amount),
                        'print_url': reverse_lazy('sales:print_invoice', kwargs={'sale_id': header.id}),
                        'updated_totals': {
                            'subtotal': str(header.subtotal),
                            'discount': str(header.discount),
                            'tax': str(header.tax),
                            'total_amount': str(header.total_amount),
                        }
                    })
                else:
                    return JsonResponse({
                        'success': True,
                        'message': 'Factura actualizada correctamente',
                        'updated_totals': {
                            'subtotal': str(header.subtotal),
                            'discount': str(header.discount),
                            'tax': str(header.tax),
                            'total_amount': str(header.total_amount),
                        }
                    })
            else:
                messages.success(request, 'Factura actualizada correctamente.')
                if print_invoice:
                    return redirect("sales:print_invoice", sale_id=sale_id)
                else:
                    return redirect("sales:sale_update", sale_id=sale_id)

    return render(request, template_name, context)

def process_multiple_sale_products(sale_order, products_data, user):
    """
    Procesa múltiples productos desde un string JSON para ventas
    """
    try:
        products = json.loads(products_data)
        products_added = 0
        
        for product_data in products:
            try:
                product = Product.objects.get(pk=product_data['id'])
                
                # Calcular valores
                quantity = float(product_data['quantity'])
                unit_price = float(product_data['price'])
                discount_percent = float(product_data.get('discount_percent', 0))
                apply_tax = product_data.get('apply_tax', False)
                
                # Calcular subtotal, descuento e impuesto
                subtotal = quantity * unit_price
                discount_amount = subtotal * (discount_percent / 100)
                tax_amount = (subtotal - discount_amount) * 0.13 if apply_tax else 0
                total_price = subtotal - discount_amount + tax_amount
                
                # Crear el item de venta
                sale_item = SaleDetail(
                    sale=sale_order,
                    product=product,
                    quantity=quantity,
                    unit_price=unit_price,
                    discount=discount_amount,
                    subtotal=subtotal,
                    tax=tax_amount,
                    total_price=total_price,
                    created_by=user
                )
                sale_item.save()
                products_added += 1
                
            except Product.DoesNotExist:
                continue
            except Exception as e:
                print(f"Error al procesar producto {product_data.get('id')}: {str(e)}")
                continue
        
        return products_added
        
    except json.JSONDecodeError:
        return 0
    except Exception as e:
        print(f"Error general al procesar productos: {str(e)}")
        return 0

def update_sale_totals(sale_order):
    """
    Recalcula los totales de una venta
    """
    items = SaleDetail.objects.filter(sale=sale_order, status=True)
    
    subtotal = items.aggregate(Sum('subtotal'))['subtotal__sum'] or 0
    discount = items.aggregate(Sum('discount'))['discount__sum'] or 0
    tax = items.aggregate(Sum('tax'))['tax__sum'] or 0
    
    sale_order.subtotal = subtotal
    sale_order.discount = discount
    sale_order.tax = tax
    sale_order.total_amount = subtotal - discount + tax
    sale_order.save()

# NUEVA VISTA PARA AGREGAR MÚLTIPLES PRODUCTOS A UNA VENTA EXISTENTE
@login_required(login_url='/login/')
def add_multiple_sale_products_view(request, sale_id):
    """
    Vista específica para agregar múltiples productos a una venta existente
    """
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            header = Sale.objects.get(pk=sale_id)
            products_data = request.POST.get("products_data")
            
            if products_data:
                products_added = process_multiple_sale_products(header, products_data, request.user)
                
                if products_added > 0:
                    # Recalcular totales
                    update_sale_totals(header)
                    
                    return JsonResponse({
                        'success': True,
                        'message': f'{products_added} productos agregados correctamente',
                        'updated_totals': {
                            'subtotal': str(header.subtotal),
                            'discount': str(header.discount),
                            'tax': str(header.tax),
                            'total_amount': str(header.total_amount),
                        }
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'error': 'No se pudieron agregar los productos'
                    })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No se recibieron datos de productos'
                })
                
        except Sale.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Venta no encontrada'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': f'Error al procesar: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'error': 'Método no permitido'
    })

class SaleDeleteView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, sale_id, pk):
        try:
            sale_item = SaleDetail.objects.get(pk=pk, sale_id=sale_id)
            sale_order = sale_item.sale
            
            # Eliminar el item
            sale_item.delete()
            
            # Recalcular totales
            self.update_sale_totals(sale_order)
            
            # Devolver respuesta JSON para AJAX
            return JsonResponse({
                'success': True,
                'message': 'Item eliminado correctamente',
                'updated_totals': {
                    'subtotal': str(sale_order.subtotal),
                    'discount': str(sale_order.discount),
                    'tax': str(sale_order.tax),
                    'total_amount': str(sale_order.total_amount),
                }
            })
            
        except SaleDetail.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Item no encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def update_sale_totals(self, sale_order):
        """Recalcular totales después de eliminar un item"""
        items = SaleDetail.objects.filter(sale=sale_order)
        
        subtotal = items.aggregate(Sum('subtotal'))['subtotal__sum'] or 0
        discount = items.aggregate(Sum('discount'))['discount__sum'] or 0
        tax = items.aggregate(Sum('tax'))['tax__sum'] or 0
        
        sale_order.subtotal = subtotal
        sale_order.discount = discount
        sale_order.tax = tax
        sale_order.total_amount = subtotal - discount + tax
        sale_order.save()


class SaleAnularView(LoginRequiredMixin, View):
    def post(self, request, sale_id, pk):
        try:
            data = json.loads(request.body)
            admin_password = data.get('admin_password')
            
            # Verificar contraseña de administrador
            user = authenticate(username=request.user.username, password=admin_password)
            if not user or not user.is_staff:
                return JsonResponse({
                    'success': False,
                    'error': 'Contraseña de administrador incorrecta o usuario no tiene permisos'
                }, status=403)
            
            with transaction.atomic():
                sale_item = SaleDetail.objects.get(pk=pk, sale_id=sale_id)
                sale_order = sale_item.sale
                
                # Verificar que el item no esté ya anulado
                if not sale_item.status:
                    return JsonResponse({
                        'success': False,
                        'error': 'Este item ya está anulado'
                    })
                
                # Anular el item (cambiar status a False)
                sale_item.status = False
                sale_item.modified_by = request.user.id  # ← CORREGIDO: usar ID en lugar de instancia
                sale_item.save()
                
                # Devolver el producto al inventario
                product = sale_item.product
                product.stock += sale_item.quantity
                product.save()
                
                # Recalcular totales de la factura
                self.update_sale_totals(sale_order)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Item anulado correctamente',
                    'updated_totals': {
                        'subtotal': str(sale_order.subtotal),
                        'discount': str(sale_order.discount),
                        'tax': str(sale_order.tax),
                        'total_amount': str(sale_order.total_amount),
                    }
                })
                
        except SaleDetail.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Item no encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def update_sale_totals(self, sale_order):
        """Recalcular totales considerando solo items activos"""
        items = SaleDetail.objects.filter(sale=sale_order, status=True)
        
        subtotal = items.aggregate(Sum('subtotal'))['subtotal__sum'] or 0
        discount = items.aggregate(Sum('discount'))['discount__sum'] or 0
        tax = items.aggregate(Sum('tax'))['tax__sum'] or 0
        
        sale_order.subtotal = subtotal
        sale_order.discount = discount
        sale_order.tax = tax
        sale_order.total_amount = subtotal - discount + tax
        sale_order.save()


def get_customers_json(request):
    customers = Customer.objects.filter(status=True).values('id', 'name', 'last_name', 'dni')
    
    # Formatear los datos para el select
    customers_list = []
    for customer in customers:
        customers_list.append({
            'id': customer['id'],
            'full_name': f"{customer['name']} {customer['last_name']}",
            'dni': customer['dni']
        })
    
    return JsonResponse({'customers': customers_list})

class CashRegisterView(LoginRequiredMixin, View):
    def get(self, request):
        # Primero, cerrar cajas antiguas automáticamente
        self.close_old_cash_registers(request.user)
        
        hoy = timezone.now().date()
        start_of_day = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
        end_of_day = timezone.make_aware(datetime.combine(hoy, datetime.max.time()))
        
        # Todos los movimientos del día
        cash_movements = CashRegister.objects.filter(
            date__range=(start_of_day, end_of_day),
            user=request.user
        ).order_by('-date')
        
        # Caja abierta HOY
        open_register_today = CashRegister.objects.filter(
            operation_type=CashRegister.CASH_OPEN,
            date__range=(start_of_day, end_of_day),
            status=True,
            user=request.user
        ).first()
        
        is_cash_open_today = open_register_today is not None
        
        # Caja cerrada HOY
        closed_register_today = CashRegister.objects.filter(
            operation_type=CashRegister.CASH_OPEN,
            date__range=(start_of_day, end_of_day),
            status=False,
            user=request.user
        ).first()
        
        # Saldo actual: último movimiento activo del usuario
        last_active = CashRegister.objects.filter(
            user=request.user
        ).order_by('-date', '-id').first()
        
        current_balance = last_active.current_balance if last_active else Decimal('0.00')
        
        # Saldo inicial del turno actual
        opening_balance = open_register_today.amount if open_register_today else Decimal('0.00')
        
        # Ventas del día
        sales_today = Sale.objects.filter(
            date__date=hoy,
            status=True,
            created_by=request.user
        ).order_by('-date')
        
        total_sales_today = sales_today.aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
        
        # Formulario para movimiento manual
        form = CashRegisterForm()
        
        context = {
            'cash_movements': cash_movements,
            'current_balance': current_balance,
            'opening_balance': opening_balance,
            'is_cash_open': is_cash_open_today,  # Solo true si hay caja abierta HOY
            'open_register': open_register_today,
            'closed_register_today': closed_register_today,  # Para mostrar mensaje
            'today': hoy,
            'form': form,
            'sales_today': sales_today,
            'total_sales_today': total_sales_today,
            'is_cash_closed': not is_cash_open_today,
            'has_cash_closed_today': closed_register_today is not None,  # Nueva variable
        }
        return render(request, 'sales/cash_register.html', context)
    
    def close_old_cash_registers(self, user):
        """Cierra automáticamente cajas abiertas de días anteriores"""
        hoy = timezone.now().date()
        start_of_day = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
        
        # Encontrar y cerrar cajas abiertas de días anteriores
        old_open_cash = CashRegister.objects.filter(
            operation_type=CashRegister.CASH_OPEN,
            date__lt=start_of_day,
            status=True,
            user=user
        )
        
        for cash in old_open_cash:
            cash.status = False
            cash.save()
            
            # Registrar cierre automático
            CashRegister.objects.create(
                operation_type=CashRegister.CASH_CLOSE,
                amount=cash.current_balance,
                user=user,
                description=f"Cierre automático - caja del {cash.date.date()}",
                current_balance=cash.current_balance,
                created_by=user
            )


class OpenCashRegisterView(LoginRequiredMixin, View):
    def post(self, request):
        amount = request.POST.get('amount')
        description = request.POST.get('description', '').strip() or 'Apertura de caja'
        
        if not amount:
            messages.error(request, 'El monto de apertura es obligatorio.')
            return redirect('sales:cash_register')
        
        try:
            amount = Decimal(amount)
            if amount < 0:
                raise ValueError()
            
            # 1. Cerrar cajas abiertas de días anteriores
            self.close_old_cash_registers(request.user)
            
            hoy = timezone.now().date()
            start_of_day = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
            end_of_day = timezone.make_aware(datetime.combine(hoy, datetime.max.time()))
            
            # 2. Verificar si ya existe caja abierta HOY
            open_cash_today = CashRegister.objects.filter(
                operation_type=CashRegister.CASH_OPEN,
                date__range=(start_of_day, end_of_day),
                status=True,
                user=request.user
            ).first()
            
            if open_cash_today:
                messages.warning(request, 'Ya tienes una caja abierta hoy.')
                return redirect('sales:cash_register')
            
            # 3. Verificar si existe caja cerrada HOY
            closed_cash_today = CashRegister.objects.filter(
                operation_type=CashRegister.CASH_OPEN,
                date__range=(start_of_day, end_of_day),
                status=False,  # Cerrada
                user=request.user
            ).first()
            
            if closed_cash_today:
                # Ofrecer reabrir la caja existente
                # En lugar de crear nueva, cambiamos el estado
                closed_cash_today.status = True
                closed_cash_today.amount = amount
                closed_cash_today.current_balance = amount
                closed_cash_today.save()
                
                messages.success(request, f'Caja reabierta con saldo inicial de ${amount:,.2f}')
                return redirect('sales:cash_register')
            
            # 4. Crear nueva apertura (primera del día)
            CashRegister.objects.create(
                operation_type=CashRegister.CASH_OPEN,
                amount=amount,
                user=request.user,
                description=f"{description} - {request.user.get_full_name() or request.user.username}",
                created_by=request.user,
                status=True,
                current_balance=amount  # Importante: establecer saldo inicial
            )
            
            messages.success(request, f'Caja abierta correctamente con ${amount:,.2f}')
            return redirect('sales:cash_register')
            
        except (InvalidOperation, ValueError):
            messages.error(request, 'Monto inválido.')
            return redirect('sales:cash_register')
    
    def close_old_cash_registers(self, user):
        """Cierra automáticamente cajas abiertas de días anteriores"""
        hoy = timezone.now().date()
        start_of_day = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
        
        # Encontrar y cerrar cajas abiertas de días anteriores
        old_open_cash = CashRegister.objects.filter(
            operation_type=CashRegister.CASH_OPEN,
            date__lt=start_of_day,
            status=True,
            user=user
        )
        
        for cash in old_open_cash:
            cash.status = False
            cash.save()
            
            # Registrar cierre automático
            CashRegister.objects.create(
                operation_type=CashRegister.CASH_CLOSE,
                amount=cash.current_balance,
                user=user,
                description=f"Cierre automático - caja del {cash.date.date()}",
                current_balance=cash.current_balance,
                created_by=user
            )


class CloseCashRegisterView(LoginRequiredMixin, View):
    def post(self, request):
        real_amount = request.POST.get('real_amount')
        observations = request.POST.get('observations', '').strip()
        
        # Buscar la caja abierta HOY
        hoy = timezone.now().date()
        start_of_day = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
        end_of_day = timezone.make_aware(datetime.combine(hoy, datetime.max.time()))
        
        open_register = CashRegister.objects.filter(
            operation_type=CashRegister.CASH_OPEN,
            date__range=(start_of_day, end_of_day),
            status=True,
            user=request.user
        ).first()
        
        if not open_register:
            messages.error(request, 'No hay ninguna caja abierta hoy para cerrar.')
            return redirect('sales:cash_register')
        
        try:
            real_amount = Decimal(real_amount) if real_amount else open_register.current_balance
        except (InvalidOperation, TypeError):
            messages.error(request, 'Monto real inválido.')
            return redirect('sales:cash_register')
        
        theoretical_balance = open_register.current_balance
        difference = real_amount - theoretical_balance
        
        # Crear cierre de caja
        CashRegister.objects.create(
            operation_type=CashRegister.CASH_CLOSE,
            amount=real_amount,
            user=request.user,
            description=f"Cierre de caja - {request.user.get_full_name() or request.user.username} | "
                       f"Teórico: ${theoretical_balance:,.2f} | Real: ${real_amount:,.2f} | "
                       f"Diferencia: ${difference:,.2f} | {observations}",
            created_by=request.user,
            status=True,
            current_balance=real_amount
        )
        
        # Marcar apertura como cerrada
        open_register.status = False
        open_register.save()
        
        messages.success(request, f'Caja cerrada correctamente. Diferencia: ${difference:,.2f}')
        return redirect('sales:cash_register')


class AddCashMovementView(LoginRequiredMixin, View):
    def post(self, request):
        # Verificar si hay caja abierta HOY
        hoy = timezone.now().date()
        start_of_day = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
        end_of_day = timezone.make_aware(datetime.combine(hoy, datetime.max.time()))
        
        open_register = CashRegister.objects.filter(
            operation_type=CashRegister.CASH_OPEN,
            date__range=(start_of_day, end_of_day),
            status=True,
            user=request.user
        ).exists()
        
        if not open_register:
            messages.error(request, 'No hay caja abierta hoy.')
            return redirect('sales:cash_register')
        
        form = CashRegisterForm(request.POST)
        if form.is_valid():
            movement = form.save(commit=False)
            movement.user = request.user
            movement.status = True
            movement.created_by = request.user
            
            # Evitar abrir o cerrar desde este formulario
            if movement.operation_type in [CashRegister.CASH_OPEN, CashRegister.CASH_CLOSE]:
                messages.error(request, 'No puedes abrir o cerrar caja desde este formulario.')
                return redirect('sales:cash_register')
            
            movement.save()
            messages.success(request, 'Movimiento agregado correctamente.')
        else:
            messages.error(request, 'Error en el formulario.')
        
        return redirect('sales:cash_register')


class ForceOpenCashRegisterView(LoginRequiredMixin, View):
    """Vista para forzar apertura cuando ya existe caja cerrada hoy"""
    def post(self, request):
        amount = request.POST.get('amount', '0')
        
        try:
            amount = Decimal(amount)
            if amount < 0:
                raise ValueError()
            
            hoy = timezone.now().date()
            start_of_day = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
            end_of_day = timezone.make_aware(datetime.combine(hoy, datetime.max.time()))
            
            # Cerrar cualquier caja abierta de días anteriores
            self.close_old_cash_registers(request.user)
            
            # Buscar caja cerrada hoy
            closed_cash_today = CashRegister.objects.filter(
                operation_type=CashRegister.CASH_OPEN,
                date__range=(start_of_day, end_of_day),
                status=False,
                user=request.user
            ).first()
            
            if closed_cash_today:
                # Cambiar la existente a abierta
                closed_cash_today.status = True
                closed_cash_today.amount = amount
                closed_cash_today.current_balance = amount
                closed_cash_today.save()
                messages.success(request, f'Caja reabierta con ${amount:,.2f}')
            else:
                # Crear nueva
                CashRegister.objects.create(
                    operation_type=CashRegister.CASH_OPEN,
                    amount=amount,
                    user=request.user,
                    description=f"Apertura forzada - {request.user.username}",
                    created_by=request.user,
                    status=True,
                    current_balance=amount
                )
                messages.success(request, f'Caja abierta con ${amount:,.2f}')
            
            return redirect('sales:cash_register')
            
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
            return redirect('sales:cash_register')
    
    def close_old_cash_registers(self, user):
        """Cierra automáticamente cajas abiertas de días anteriores"""
        hoy = timezone.now().date()
        start_of_day = timezone.make_aware(datetime.combine(hoy, datetime.min.time()))
        
        # Encontrar y cerrar cajas abiertas de días anteriores
        old_open_cash = CashRegister.objects.filter(
            operation_type=CashRegister.CASH_OPEN,
            date__lt=start_of_day,
            status=True,
            user=user
        )
        
        for cash in old_open_cash:
            cash.status = False
            cash.save()
            
            # Registrar cierre automático
            CashRegister.objects.create(
                operation_type=CashRegister.CASH_CLOSE,
                amount=cash.current_balance,
                user=user,
                description=f"Cierre automático - caja del {cash.date.date()}",
                current_balance=cash.current_balance,
                created_by=user
            )


class BudgetCreateView(LoginRequiredMixin, View):
    def get(self, request):
        template_name = "sales/budget.html"
        products = Product.objects.filter(status=True)
        customers = Customer.objects.filter(status=True)
        
        context = {
            'products': products,
            'customers': customers,
        }
        return render(request, template_name, context)


class DailyReportSelectDateView(LoginRequiredMixin, View):
    def get(self, request):
        template_name = 'sales/daily_report_select_date.html'
        
        # Obtener las fechas disponibles que tienen ventas o movimientos de caja
        available_dates = Sale.objects.filter(status=True).dates('date', 'day', order='DESC')[:30]
        
        context = {
            'available_dates': available_dates,
        }
        return render(request, template_name, context)

# VISTA DE IMPRESIÓN DE FACTURA (ASEGURARSE DE QUE EXISTA)
@login_required(login_url='/login/')
def print_invoice(request, sale_id):
    """
    Vista para imprimir factura
    """
    try:
        sale = Sale.objects.get(id=sale_id)
        sale_details = SaleDetail.objects.filter(sale=sale, status=True)
        
        context = {
            'sale': sale,
            'sale_details': sale_details,
            'business_name': 'Tu Negocio',  # Reemplazar con datos reales
            'business_address': 'Dirección de tu negocio',
            'business_phone': 'Teléfono de tu negocio',
        }
        
        template = get_template('sales/invoice_print.html')
        html = template.render(context)
        
        # Crear respuesta PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'filename="factura_{sale.invoice_number}.pdf"'
        
        # Generar PDF
        pisa_status = pisa.CreatePDF(html, dest=response)
        
        if pisa_status.err:
            return HttpResponse('Error al generar PDF', status=500)
        
        return response
        
    except Sale.DoesNotExist:
        messages.error(request, 'Factura no encontrada.')
        return redirect('sales:sales_list')