from django.shortcuts import render
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.http import JsonResponse

from .models import Category, SubCategory, Brand, UnitMeasure, Product
from .forms import CategoryForm, SubCategoryForm, BrandForm, UnitMeasureForm, ProductForm
from applications.home.mixins import AdminRequiredMixin, SellerRequiredMixin
# Create your views here.

# Category Views

class CategoryListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Category
    template_name = 'inv/category_list.html'
    context_object_name = 'categories'
    login_url = reverse_lazy('home:login')

class CreateCategoryView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inv/category_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:category_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'✅ La categoría "{form.instance.name}" ha sido creada exitosamente.'
        )
        return response
    
class ToggleCategoryStatusView(AdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        category_id = request.POST.get('category_id')
        try:
            category = Category.objects.get(id=category_id)
            new_status = category.toggle_status()

            return JsonResponse({'success': True, 'new_status': new_status, 'category_name': category.name})
        except Category.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Categoría no encontrada'})
        
class UpdateCategoryView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inv/category_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:category_list')

    def form_valid(self, form):
        form.instance.modified_by = self.request.user.id
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'✅ La Categoría "{form.instance.name}" ha sido Actualizada exitosamente.'
        )
        return response
    
# SubCategory Views

class SubCategoryListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = SubCategory
    template_name = 'inv/sub_category_list.html'
    context_object_name = 'subcategories'
    login_url = reverse_lazy('home:login')

class CreateSubCategoryView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = SubCategory
    form_class = SubCategoryForm
    template_name = 'inv/sub_category_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:sub_category_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'✅ La SubCategoría "{form.instance.name}" ha sido creada exitosamente.'
        )
        return response
    

class ToggleSubCategoryStatusView(AdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        sub_category_id = request.POST.get('sub_category_id')
        try:
            subcategory = SubCategory.objects.get(id=sub_category_id)
            new_status = subcategory.toggle_status()
            return JsonResponse({'success': True, 'new_status': new_status, 'sub_category_name': subcategory.name})
        except SubCategory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Sub Categoría no encontrada'})
        
class UpdateSubCategoryView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = SubCategory
    form_class = SubCategoryForm
    template_name = 'inv/category_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:sub_category_list')

    def form_valid(self, form):
        form.instance.modified_by = self.request.user.id
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'✅ La SubCategoría "{form.instance.name}" ha sido Actualizada exitosamente.'
        )
        return response
    
# Brand Views
class BrandListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = Brand
    template_name = 'inv/brand_list.html'
    context_object_name = 'brands'
    login_url = reverse_lazy('home:login')

class CreateBrandView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Brand
    form_class = BrandForm
    template_name = 'inv/brand_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:brand_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'✅ La Marca "{form.instance.name}" ha sido creada exitosamente.'
        )
        return response
    

class ToggleBrandStatusView(AdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        brand_id = request.POST.get('brand_id')
        try:
            brand = Brand.objects.get(id=brand_id)
            new_status = brand.toggle_status()
            return JsonResponse({'success': True, 'new_status': new_status, 'brand_name': brand.name})
            
        except Brand.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Marca no encontrada'})
        
class UpdateBrandView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = Brand
    form_class = BrandForm
    template_name = 'inv/brand_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:brand_list')

    def form_valid(self, form):
        form.instance.modified_by = self.request.user.id
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'✅ La Marca "{form.instance.name}" ha sido Actualizada exitosamente.'
        )
        return response
    
# UnitMeasure Views
class UnitMeasureListView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    model = UnitMeasure
    template_name = 'inv/unit_measure_list.html'
    context_object_name = 'unit_measures'
    login_url = reverse_lazy('home:login')

class CreateUnitMeasureView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = UnitMeasure
    form_class = UnitMeasureForm
    template_name = 'inv/unit_measure_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:unit_measure_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'✅ La Unidad de Medida "{form.instance.name}" ha sido creada exitosamente.'
        )
        return response
    
class ToggleUnitMeasureStatusView(AdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        unit_measure_id = request.POST.get('unit_measure_id')
        try:
            unit_measure = UnitMeasure.objects.get(id=unit_measure_id)
            new_status = unit_measure.toggle_status()
            return JsonResponse({'success': True, 'new_status': new_status, 'unit_measure_name': unit_measure.name})
        except Brand.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Unidad de medida no encontrada'})
        
class UpdateUnitMeasureView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    model = UnitMeasure
    form_class = UnitMeasureForm
    template_name = 'inv/unit_measure_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:unit_measure_list')

    def form_valid(self, form):
        form.instance.modified_by = self.request.user.id
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'✅ La categoría "{form.instance.name}" ha sido Actualizada exitosamente.'
        )
        return response
    
# Product Views
class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'inv/products_list.html'
    context_object_name = 'products'
    login_url = reverse_lazy('home:login')

class CreateProductView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inv/product_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:products_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'✅ El Producto "{form.instance.name}" ha sido creada exitosamente.'
        )
        return response
    
class ToggleProductStatusView(AdminRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        product_id = request.POST.get('product_id')
        try:
            product = Product.objects.get(id=product_id)
            new_status = product.toggle_status()
            return JsonResponse({'success': True, 'new_status': new_status, 'product_name': product.name})
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Producto no encontrada'})
        
class UpdateProductView(AdminRequiredMixin, LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'inv/product_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:products_list')

    def form_valid(self, form):
        form.instance.modified_by = self.request.user.id
        response = super().form_valid(form)
        messages.success(
            self.request, 
            f'✅ El producto "{form.instance.name}" ha sido Actualizado exitosamente.'
        )
        return response