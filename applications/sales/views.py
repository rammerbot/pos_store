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
    template_name = 'sales/Customers_list.html'
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
        
        cash_movements = CashRegister.objects.filter(
            date__range=(start_of_day, end_of_day),
            status=True
        )
        
        is_cash_open = cash_movements.filter(operation_type=CashRegister.CASH_OPEN).exists()
        is_cash_closed = cash_movements.filter(operation_type=CashRegister.CASH_CLOSE).exists()
        
        # Si la caja no está abierta o ya está cerrada, mostrar error
        if not is_cash_open or is_cash_closed:
            messages.error(request, '❌ No se puede acceder a las ventas. La caja no está abierta o ya fue cerrada.')
            return redirect('sales:cash_register')
        
        return super().get(request, *args, **kwargs)

@login_required(login_url='/login/')
def sale_order_view(request, sale_id=None):

     # Verificar estado de la caja
    today = datetime.now().date()
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    
    cash_movements = CashRegister.objects.filter(
        date__range=(start_of_day, end_of_day),
        status=True
    )
    
    is_cash_open = cash_movements.filter(operation_type=CashRegister.CASH_OPEN).exists()
    is_cash_closed = cash_movements.filter(operation_type=CashRegister.CASH_CLOSE).exists()
    
    # Si la caja no está abierta o ya está cerrada, mostrar error
    if not is_cash_open or is_cash_closed:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': 'No se puede realizar ventas. La caja no está abierta o ya fue cerrada.'
            }, status=403)
        else:
            messages.error(request, '❌ No se puede realizar ventas. La caja no está abierta o ya fue cerrada.')
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
       
        if not sale_id:
            customer_ = Customer.objects.get(pk=customer)

            header = Sale(
                observation=observation,
                customer=customer_,
                created_by=request.user
            )
            if header:
                header.save()
                sale_id = header.id  # Aquí se genera el sale_id
                
                # REDIRIGIR A LA EDICIÓN DE LA NUEVA FACTURA CREADA
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': True,
                        'message': 'Factura creada exitosamente',
                        'redirect_url': f'/sales/sales/update/{sale_id}/'  # Agregar esta línea
                    })
                else:
                    # Redirigir a la vista de edición de la nueva factura
                    return redirect("sales:sale_update", sale_id=sale_id)
                    
        else:
            header = Sale.objects.filter(pk=sale_id).first()
            if header:
                header.observation = observation
                header.modified_by = request.user.id
                header.save()
        
        # Si llegamos aquí y no hay sale_id, hubo un error
        if not sale_id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Error al crear la orden de compra'
                })
            return redirect("sales:sale_list")
        
        product = request.POST.get("id_id_producto")
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
                sub_total = SaleDetail.objects.filter(sale=sale_id).aggregate(Sum('subtotal'))['subtotal__sum'] or 0
                discount_total = SaleDetail.objects.filter(sale=sale_id).aggregate(Sum('discount'))['discount__sum'] or 0
                tax_total = SaleDetail.objects.filter(sale=sale_id).aggregate(Sum('tax'))['tax__sum'] or 0
                
                header.subtotal = sub_total
                header.discount = discount_total
                header.tax = tax_total
                header.total_amount = sub_total - discount_total + tax_total
                header.save()

                # Si es AJAX, devolver JSON
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
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

    return render(request, template_name, context)

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
        # Usar datetime.now() para obtener la fecha local correcta
        today = datetime.now().date()
        
        # Obtener el inicio y fin del día para filtrar correctamente
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        # Filtrar movimientos del día actual
        cash_movements = CashRegister.objects.filter(
            date__range=(start_of_day, end_of_day),
            status=True
        ).order_by('-date')
        
        # Obtener el saldo actual (último movimiento)
        last_movement = cash_movements.first()
        current_balance = last_movement.current_balance if last_movement else 0
        
        # Obtener saldo de apertura si existe
        opening_record = cash_movements.filter(operation_type=CashRegister.CASH_OPEN).first()
        opening_balance = opening_record.amount if opening_record else 0
        
        # Verificar si ya hay caja abierta hoy
        is_cash_open = cash_movements.filter(
            operation_type=CashRegister.CASH_OPEN
        ).exists()
        
        # Verificar si ya hay caja cerrada hoy
        is_cash_closed = cash_movements.filter(
            operation_type=CashRegister.CASH_CLOSE
        ).exists()
        
        # DEBUG: Información para diagnóstico
        print(f"DEBUG - Fecha: {today}")
        print(f"DEBUG - Rango: {start_of_day} a {end_of_day}")
        print(f"DEBUG - Movimientos: {cash_movements.count()}")
        print(f"DEBUG - Aperturas encontradas: {cash_movements.filter(operation_type=CashRegister.CASH_OPEN).count()}")
        print(f"DEBUG - Cierres encontrados: {cash_movements.filter(operation_type=CashRegister.CASH_CLOSE).count()}")
        print(f"DEBUG - is_cash_open: {is_cash_open}")
        print(f"DEBUG - is_cash_closed: {is_cash_closed}")
        
        form = CashRegisterForm()
        
        context = {
            'cash_movements': cash_movements,
            'current_balance': current_balance,
            'opening_balance': opening_balance,
            'today': today,
            'form': form,
            'is_cash_open': is_cash_open,
            'is_cash_closed': is_cash_closed,
        }
        return render(request, 'sales/cash_register.html', context)
    
    def post(self, request):
        form = CashRegisterForm(request.POST)
        if form.is_valid():
            cash_register = form.save(commit=False)
            cash_register.user = request.user
            cash_register.created_by = request.user
            cash_register.save()
            
            messages.success(request, 'Movimiento de caja registrado correctamente.')
            return redirect('sales:cash_register')
        
        # Si el formulario no es válido, recargar la página con errores
        today = datetime.now().date()
        
        # Obtener el inicio y fin del día para filtrar correctamente
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        cash_movements = CashRegister.objects.filter(
            date__range=(start_of_day, end_of_day),
            status=True
        ).order_by('-date')
        
        last_movement = cash_movements.first()
        current_balance = last_movement.current_balance if last_movement else 0
        
        opening_record = cash_movements.filter(operation_type=CashRegister.CASH_OPEN).first()
        opening_balance = opening_record.amount if opening_record else 0
        
        is_cash_open = cash_movements.filter(
            operation_type=CashRegister.CASH_OPEN
        ).exists()
        
        is_cash_closed = cash_movements.filter(
            operation_type=CashRegister.CASH_CLOSE
        ).exists()
        
        context = {
            'cash_movements': cash_movements,
            'current_balance': current_balance,
            'opening_balance': opening_balance,
            'today': today,
            'form': form,
            'is_cash_open': is_cash_open,
            'is_cash_closed': is_cash_closed,
        }
        return render(request, 'sales/cash_register.html', context)

class OpenCashRegisterView(LoginRequiredMixin, View):
    def post(self, request):
        amount = request.POST.get('amount')
        description = request.POST.get('description', 'Apertura de caja')
        
        if not amount:
            messages.error(request, 'El monto de apertura es requerido.')
            return redirect('sales:cash_register')
        
        try:
            amount = Decimal(amount)
            if amount < 0:
                raise ValueError("El monto no puede ser negativo")
                
            # Verificar si ya hay una caja abierta hoy
            today = datetime.now().date()
            existing_open = CashRegister.objects.filter(
                date__date=today,
                operation_type=CashRegister.CASH_OPEN,
                status=True
            ).exists()
            
            if existing_open:
                messages.warning(request, 'Ya existe una apertura de caja para hoy.')
                return redirect('sales:cash_register')
            
            # Verificar si ya hay caja cerrada hoy
            existing_closed = CashRegister.objects.filter(
                date__date=today,
                operation_type=CashRegister.CASH_CLOSE,
                status=True
            ).exists()
            
            if existing_closed:
                messages.warning(request, 'La caja ya fue cerrada hoy. No se puede abrir nuevamente.')
                return redirect('sales:cash_register')
            
            # Crear registro de apertura con el usuario
            cash_register = CashRegister(
                operation_type=CashRegister.CASH_OPEN,
                amount=amount,
                user=request.user,
                description=description,
            )
            
            cash_register.created_by = request.user
            cash_register.save()
            
            messages.success(request, f'Caja abierta con ${amount:.2f}')
            
        except (ValueError, InvalidOperation) as e:
            messages.error(request, f'Error al abrir caja: {str(e)}')
        
        return redirect('sales:cash_register')

class CloseCashRegisterView(LoginRequiredMixin, View):
    def post(self, request):
        today = datetime.now().date()
        
        # Obtener el inicio y fin del día para filtrar correctamente
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        # Obtener el saldo actual
        last_movement = CashRegister.objects.filter(
            date__range=(start_of_day, end_of_day),
            status=True
        ).order_by('-date').first()
        
        if not last_movement:
            messages.error(request, 'No hay caja abierta para cerrar.')
            return redirect('sales:cash_register')
        
        current_balance = last_movement.current_balance
        
        # Crear registro de cierre
        cash_register = CashRegister(
            operation_type=CashRegister.CASH_CLOSE,
            amount=current_balance,
            user=request.user,
            description='Cierre de caja diario',
        )
        
        cash_register.created_by = request.user
        cash_register.save()
        
        messages.success(request, f'Caja cerrada. Saldo final: ${current_balance:.2f}')
        return redirect('sales:cash_register')
    
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