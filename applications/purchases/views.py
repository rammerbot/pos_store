from django.shortcuts import render
from django.views.generic import ListView, CreateView, View, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.template.loader import render_to_string

from .models import Supplier
from .forms import SupplierForm

# Create your views here.

class SupplierListView(LoginRequiredMixin, ListView):
    model = Supplier
    template_name = 'purchases/suppliers_list.html'
    context_object_name = 'suppliers'
    login_url = reverse_lazy('home:login')

class CreateSupplierView(LoginRequiredMixin, CreateView):
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
    
class ToggleSupplierStatusView(View):
    def post(self, request, *args, **kwargs):
        supplier_id = request.POST.get('supplier_id')
        try:
            supplier = Supplier.objects.get(id=supplier_id)
            new_status = supplier.toggle_status()
            return JsonResponse({'success': True, 'new_status': new_status})
        except Supplier.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Proveedor no encontrada'})
        
class UpdateSupplierView(LoginRequiredMixin, UpdateView):
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