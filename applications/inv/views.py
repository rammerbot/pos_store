from django.shortcuts import render
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse

from .models import Category, SubCategory, Brand, UnitMeasure, Product
from .forms import CategoryForm, SubCategoryForm, BrandForm, UnitMeasureForm, ProductForm
# Create your views here.

# Category Views

class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'inv/category_list.html'
    context_object_name = 'categories'
    login_url = reverse_lazy('home:login')

class CreateCategoryView(LoginRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inv/category_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:category_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    

class ToggleCategoryStatusView(View):
    def post(self, request, *args, **kwargs):
        category_id = request.POST.get('category_id')
        try:
            category = Category.objects.get(id=category_id)
            new_status = category.toggle_status()
            return JsonResponse({'success': True, 'new_status': new_status})
        except Category.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Categoría no encontrada'})
        
class UpdateCategoryView(LoginRequiredMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'inv/category_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:category_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)
    
# SubCategory Views

class SubCategoryListView(LoginRequiredMixin, ListView):
    model = SubCategory
    template_name = 'inv/sub_category_list.html'
    context_object_name = 'subcategories'
    login_url = reverse_lazy('home:login')

class CreateSubCategoryView(LoginRequiredMixin, CreateView):
    model = SubCategory
    form_class = SubCategoryForm
    template_name = 'inv/sub_category_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:category_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    

class ToggleSubCategoryStatusView(View):
    def post(self, request, *args, **kwargs):
        subcategory_id = request.POST.get('subcategory_id')
        try:
            subcategory = SubCategory.objects.get(id=subcategory_id)
            new_status = subcategory.toggle_status()
            return JsonResponse({'success': True, 'new_status': new_status})
        except SubCategory.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Sub Categoría no encontrada'})
        
class UpdateSubCategoryView(LoginRequiredMixin, UpdateView):
    model = SubCategory
    form_class = SubCategoryForm
    template_name = 'inv/category_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:sub_category_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)
    
# Brand Views
class BrandListView(LoginRequiredMixin, ListView):
    model = Brand
    template_name = 'inv/brand_list.html'
    context_object_name = 'brands'
    login_url = reverse_lazy('home:login')

class CreateBrandView(LoginRequiredMixin, CreateView):
    model = Brand
    form_class = BrandForm
    template_name = 'inv/brand_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:brand_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    

class ToggleBrandStatusView(View):
    def post(self, request, *args, **kwargs):
        brand_id = request.POST.get('brand_id')
        try:
            brand = Brand.objects.get(id=brand_id)
            new_status = brand.toggle_status()
            return JsonResponse({'success': True, 'new_status': new_status})
        except Brand.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Marca no encontrada'})
        
class UpdateBrandView(LoginRequiredMixin, UpdateView):
    model = Brand
    form_class = BrandForm
    template_name = 'inv/brand_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:brand_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)
    
# UnitMeasure Views
class UnitMeasureListView(LoginRequiredMixin, ListView):
    model = UnitMeasure
    template_name = 'inv/unit_measure_list.html'
    context_object_name = 'unit_measures'
    login_url = reverse_lazy('home:login')

class CreateUnitMeasureView(LoginRequiredMixin, CreateView):
    model = UnitMeasure
    form_class = UnitMeasureForm
    template_name = 'inv/unit_measure_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:unit_measure_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
class ToggleUnitMeasureStatusView(View):
    def post(self, request, *args, **kwargs):
        brand_id = request.POST.get('unit_measure_id')
        try:
            brand = Brand.objects.get(id=brand_id)
            new_status = brand.toggle_status()
            return JsonResponse({'success': True, 'new_status': new_status})
        except Brand.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Unidad de medida no encontrada'})
        
class UpdateUnitMeasureView(LoginRequiredMixin, UpdateView):
    model = UnitMeasure
    form_class = UnitMeasureForm
    template_name = 'inv/unit_measure_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:unit_measure_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)
    
# Product Views
class ProductListView(LoginRequiredMixin, ListView):
    model = Product
    template_name = 'inv/products_list.html'
    context_object_name = 'products'
    login_url = reverse_lazy('home:login')

class CreateProductView(LoginRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inv/product_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:products_list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
class ToggleProductStatusView(View):
    def post(self, request, *args, **kwargs):
        brand_id = request.POST.get('product_id')
        try:
            brand = Product.objects.get(id=brand_id)
            new_status = brand.toggle_status()
            return JsonResponse({'success': True, 'new_status': new_status})
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Producto no encontrada'})
        
class UpdateProductView(LoginRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'inv/product_form.html'
    login_url = reverse_lazy('home:login')
    success_url = reverse_lazy('inv:products_list')

    def form_valid(self, form):
        form.instance.updated_by = self.request.user
        return super().form_valid(form)