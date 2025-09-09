import datetime

from django.shortcuts import render, redirect
from django.views.generic import ListView, CreateView, View, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

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
def purchase(request,purchase_id=None):
    template_name="purchases/purchase_form.html"
    products =Product.objects.filter(status=True)
    purchase_form={}
    contexto={}

    if request.method=='GET':
        purchase_form=PurchaseForm()
        header = PurchaseOrder.objects.filter(pk=purchase_id).first()

        if header:
            purchase_item = PurchaseItem.objects.filter(purchase_order=header)
            buy_date = datetime.date.isoformat(header.buy_date)
            order_date = datetime.date.isoformat(header.order_date)
            e = {
                'buy_date':buy_date,
                'supplier': header.supplier,
                'observations': header.observations,
                'order_number': header.order_number,
                'order_date': header.order_date,
                'sub_total': header.subtotal,
                'descuento': header.discount,
                'total':header.total_amount
            }
            purchase_form = PurchaseForm(e)
        else:
            purchase_item=None
        
        contexto={'products':products,'header':header,'purchase_item':purchase_item,'purchase_form':purchase_form}

    if request.method=='POST':
        buy_date = request.POST.get("buy_date")
        observations = request.POST.get("observations")
        order_number = request.POST.get("order_number")
        order_date = request.POST.get("order_date")
        supplier = request.POST.get("supplier")
        sub_total = 0
        descuento = 0
        total = 0

        if not purchase_id:
            supplier_=Supplier.objects.get(pk=supplier)

            header = PurchaseOrder(
                buy_date=buy_date,
                observations=observations,
                order_number=order_number,
                order_date=order_date,
                supplier=supplier_,
                uc = request.user 
            )
            if header:
                header.save()
                purchase_id=header.id
        else:
            header=PurchaseOrder.objects.filter(pk=purchase_id).first()
            if header:
                header.buy_date = buy_date
                header.observations = observations
                header.order_number=order_number
                header.order_date=order_date
                header.modified_by=request.user.id
                header.save()

        if not purchase_id:
            return redirect("purchases:purchase_list")
        
        product = request.POST.get("id_id_producto")
        quantity = request.POST.get("id_cantidad_detalle")
        price = request.POST.get("id_precio_detalle")
        subtotal = request.POST.get("id_sub_total_detalle")
        discount  = request.POST.get("id_descuento_detalle")
        total_amount  = request.POST.get("id_total_detalle")

        prod = Product.objects.get(pk=product)

        det = PurchaseItem(
            compra=header,
            product=prod,
            cantidad=quantity,
            precio_prv=price,
            descuento=discount,
            costo=0,
            uc = request.user
        )

        if det:
            det.save()

            sub_total=PurchaseItem.objects.filter(compra=purchase_id).aggregate(Sum('sub_total'))
            descuento=PurchaseItem.objects.filter(compra=purchase_id).aggregate(Sum('descuento'))
            header.subtotal = sub_total["subtotal__sum"]
            header.discount=descuento["discount__sum"]
            header.save()

        return redirect("purchases:purchase_update",purchase_id=purchase_id)


    return render(request, template_name, contexto)