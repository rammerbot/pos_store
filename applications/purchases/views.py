import datetime
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

from .models import Supplier, PurchaseItem, PurchaseOrder
from applications.inv.models import Product
from .forms import SupplierForm
from applications.home.mixins import AdminRequiredMixin, SellerRequiredMixin
from .forms import PurchaseForm

# Create your views here.

class SupplierListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Supplier
    template_name = 'purchases/suppliers_list.html'
    context_object_name = 'suppliers'
    login_url = reverse_lazy('home:login')

class CreateSupplierView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'purchases/supplier_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('purchases:suppliers_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Es una solicitud AJAX
            self.object = form.save()
            return JsonResponse({
                'success': True, 
                'message': 'Proveedor Cargado exitosamente'
            })
        else:
            # Solicitud normal
            return super().form_valid(form)
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            # Es una solicitud AJAX - regresar el formulario con errores
            html = render_to_string(self.template_name, {
                'form': form, 
                'supplier': self.object
            }, request=self.request)
            return JsonResponse({
                'success': False, 
                'html': html
            })
        else:
            # Solicitud normal
            return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('purchases:suppliers_list')
    
class ToggleSupplierStatusView(AdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        supplier_id = request.POST.get('supplier_id')
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            new_status = supplier.toggle_status()
            return JsonResponse({'success': True, 'new_status': new_status})
        except Supplier.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Proveedor no encontrada'})
        
class UpdateSupplierView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'purchases/supplier_form.html'
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
                'supplier': self.object
            }, request=self.request)
            return JsonResponse({
                'success': False, 
                'html': html
            })
        else:
            # Solicitud normal
            return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse_lazy('purchases:suppliers_list')
    
# Purchases Views    
class PurchasesListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = PurchaseOrder
    template_name = 'purchases/purchases_list.html'
    context_object_name = 'purchases'
    login_url = reverse_lazy('home:login')


@login_required(login_url='/login/')
def purchase_order_view(request, purchase_id=None):
    template_name = "purchases/purchase_form.html"
    products = Product.objects.filter(status=True)
    purchase_form = {}
    context = {}

    if request.method =='GET':
        purchase_form = PurchaseForm()
        header = PurchaseOrder.objects.filter(pk=purchase_id).first() if purchase_id else None

        if header:
            purchase_item = PurchaseItem.objects.filter(purchase_order=header)
            buy_date = datetime.date.isoformat(header.buy_date)
            order_date = datetime.date.isoformat(header.order_date)
            e = {
                'buy_date': buy_date,
                'supplier': header.supplier,
                'observations': header.observations,
                'order_number': header.order_number,
                'order_date': order_date,
                'subtotal': header.subtotal,
                'discount': header.discount,
                'tax': header.tax,
                'total_amount': header.total_amount
            }

            purchase_form = PurchaseForm(e)
        else:
            purchase_item = None
        
        context = {'products': products, 'header': header, 'purchase_items': purchase_item, 'purchase_form': purchase_form}
 

    if request.method == 'POST':
        buy_date = request.POST.get("buy_date")
        observations = request.POST.get("observations")
        order_number = request.POST.get("order_number")
        order_date = request.POST.get("order_date")
        supplier = request.POST.get("supplier")
       
        if not purchase_id:
            supplier_ = Supplier.objects.get(pk=supplier)

            header = PurchaseOrder(
                buy_date=buy_date,
                observations=observations,
                order_number=order_number,
                order_date=order_date,
                supplier=supplier_,
                created_by=request.user
            )
            if header:
                header.save()
                purchase_id = header.id
        else:
            header = PurchaseOrder.objects.filter(pk=purchase_id).first()
            if header:
                header.buy_date = buy_date
                header.observations = observations
                header.order_number = order_number
                header.order_date = order_date
                header.modified_by = request.user.id
                header.save()
        
        if not purchase_id:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'error': 'Error al crear la orden de compra'
                })
            return redirect("purchases:purchase_list")
        
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
            return redirect("purchases:purchase_update", purchase_id=purchase_id)
        
        try:
            prod = Product.objects.get(pk=product)
            
            det = PurchaseItem(
                purchase_order=header,
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
                sub_total = PurchaseItem.objects.filter(purchase_order=purchase_id).aggregate(Sum('subtotal'))['subtotal__sum'] or 0
                discount_total = PurchaseItem.objects.filter(purchase_order=purchase_id).aggregate(Sum('discount'))['discount__sum'] or 0
                tax_total = PurchaseItem.objects.filter(purchase_order=purchase_id).aggregate(Sum('tax'))['tax__sum'] or 0
                
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
                    return redirect("purchases:purchase_update", purchase_id=purchase_id)
        
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
            return redirect("purchases:purchase_update", purchase_id=purchase_id)

    return render(request, template_name, context)


class PurchaseDeleteView(LoginRequiredMixin, AdminRequiredMixin, View):
    def post(self, request, purchase_id, pk):
        try:
            purchase_item = PurchaseItem.objects.get(pk=pk, purchase_order_id=purchase_id)
            purchase_order = purchase_item.purchase_order
            
            # Eliminar el item
            purchase_item.delete()
            
            # Recalcular totales
            self.update_purchase_totals(purchase_order)
            
            # Devolver respuesta JSON para AJAX
            return JsonResponse({
                'success': True,
                'message': 'Item eliminado correctamente',
                'updated_totals': {
                    'subtotal': str(purchase_order.subtotal),
                    'discount': str(purchase_order.discount),
                    'tax': str(purchase_order.tax),
                    'total_amount': str(purchase_order.total_amount),
                }
            })
            
        except PurchaseItem.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Item no encontrado'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def update_purchase_totals(self, purchase_order):
        """Recalcular totales después de eliminar un item"""
        items = PurchaseItem.objects.filter(purchase_order=purchase_order)
        
        subtotal = items.aggregate(Sum('subtotal'))['subtotal__sum'] or 0
        discount = items.aggregate(Sum('discount'))['discount__sum'] or 0
        tax = items.aggregate(Sum('tax'))['tax__sum'] or 0
        
        purchase_order.subtotal = subtotal
        purchase_order.discount = discount
        purchase_order.tax = tax
        purchase_order.total_amount = subtotal - discount + tax
        purchase_order.save()