from datetime import datetime, timedelta

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth import authenticate, login
from django.urls import reverse_lazy
from django.contrib.auth.models import User, Group
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncMonth, TruncDay

from applications.inv.models import Product, Category, Brand
from applications.sales.models import Sale, SaleDetail, Customer
from applications.purchases.models import PurchaseOrder, Supplier
from .forms import CustomUserCreationForm, CustomUserChangeForm
from .mixins import AdminRequiredMixin, SellerRequiredMixin


# Create your views here.


# Custom User

class UserListView(LoginRequiredMixin, AdminRequiredMixin, PermissionRequiredMixin, ListView):
    model = User
    template_name = 'auth/user_list.html'
    permission_required = 'auth.view_user'
    context_object_name = 'users'
    
    def get_queryset(self):
        return User.objects.all().prefetch_related('groups')

class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, PermissionRequiredMixin, CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = 'auth/user_form.html'
    permission_required = 'auth.add_user'
    success_url = reverse_lazy('home:user_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Asignar grupos seleccionados
        groups = form.cleaned_data.get('groups')
        if groups:
            self.object.groups.set(groups)
        messages.success(
            self.request, 
            f'✅ El Usuario"{form.instance.username}" ha sido creado exitosamente.'
        )
        return response
    
    def form_invalid(self, form):
        if self.request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'errors': form.errors})
        return super().form_invalid(form)

class UserUpdateView(LoginRequiredMixin, AdminRequiredMixin,  PermissionRequiredMixin, UpdateView):
    model = User
    form_class = CustomUserChangeForm
    template_name = 'auth/user_form.html'
    permission_required = 'auth.change_user'
    success_url = reverse_lazy('home:user_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'] = self.object
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        # Actualizar grupos
        groups = form.cleaned_data.get('groups')
        if groups:
            self.object.groups.set(groups)
        messages.success(
            self.request, 
            f'✅ El Usuario "{form.instance.username}" ha sido Actualizado exitosamente.'
        )
        return response
    
    

class UserDeleteView(LoginRequiredMixin,AdminRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = User
    template_name = 'users/user_confirm_delete.html'
    permission_required = 'auth.delete_user'
    success_url = reverse_lazy('users:user_list')
    
    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Usuario eliminado exitosamente'})
        return super().delete(request, *args, **kwargs)

class ToggleUserStatusView(LoginRequiredMixin, AdminRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'auth.change_user'
    
    def post(self, request, *args, **kwargs):
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        user.is_active = not user.is_active
        user.save()
        
        return JsonResponse({
            'success': True, 
            'new_status': user.is_active,
            'message': f'Usuario {"activado" if user.is_active else "desactivado"} exitosamente',
            'user_name': user.username
        })

# Home View
class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home/home.html'
    login_url = '/login/'  # Redirect to login page if not authenticated

# Login View
class NewLoginView(LoginView):
    template_name = 'home/login.html'
    redirect_authenticated_user = True
    def form_valid(self, form):
        user = authenticate(username=form.cleaned_data['username'], password=form.cleaned_data['password'])
        if user is not None:
            login(self.request, user)
            return super().form_valid(form)
        else:
            form.add_error(None, "Invalid username or password")
            return self.form_invalid(form)

# logout View
class NewLogoutView(LogoutView):
    next_page = '/'




@login_required
def dashboard_view(request):
    # Fechas para filtros
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    start_of_week = today - timedelta(days=today.weekday())
    
    # Ventas del mes
    monthly_sales = Sale.objects.filter(
        date__gte=start_of_month, 
        status=True
    ).aggregate(
        total=Sum('total_amount'),
        count=Count('id'),
        avg=Avg('total_amount')
    )
    
    # Ventas de la semana
    weekly_sales = Sale.objects.filter(
        date__gte=start_of_week,
        status=True
    ).aggregate(
        total=Sum('total_amount')
    )
    
    # Productos más vendidos del mes
    top_products = SaleDetail.objects.filter(
        sale__date__gte=start_of_month,
        sale__status=True,
        status=True
    ).values(
        'product__name',
        'product__code'
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_sold')[:10]
    
    # Productos con stock bajo (menos de 10 unidades)
    low_stock_products = Product.objects.filter(
        stock__lt=10,
        status=True
    ).order_by('stock')[:10]
    
    # Compras del mes
    monthly_purchases = PurchaseOrder.objects.filter(
        buy_date__gte=start_of_month,
        status=True
    ).aggregate(
        total=Sum('total_amount'),
        count=Count('id')
    )
    
    # Ventas por día (últimos 7 días)
    last_7_days = today - timedelta(days=7)
    daily_sales = Sale.objects.filter(
        date__gte=last_7_days,
        status=True
    ).annotate(
        day=TruncDay('date')
    ).values('day').annotate(
        total=Sum('total_amount'),
        count=Count('id')
    ).order_by('day')
    
    # Métricas generales
    total_products = Product.objects.filter(status=True).count()
    total_customers = Customer.objects.filter(status=True).count()
    total_suppliers = Supplier.objects.filter(status=True).count()
    
    # Productos por categoría
    products_by_category = Product.objects.filter(
        status=True
    ).values(
        'subcategory__category__name'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    # Ventas por categoría
    sales_by_category = SaleDetail.objects.filter(
        sale__status=True,
        status=True
    ).values(
        'product__subcategory__category__name'
    ).annotate(
        total_sales=Sum('total_price'),
        total_units=Sum('quantity')
    ).order_by('-total_sales')[:5]
    
    context = {
        'today': today,
        'monthly_sales': monthly_sales,
        'weekly_sales': weekly_sales,
        'top_products': top_products,
        'low_stock_products': low_stock_products,
        'monthly_purchases': monthly_purchases,
        'daily_sales': daily_sales,
        'total_products': total_products,
        'total_customers': total_customers,
        'total_suppliers': total_suppliers,
        'products_by_category': products_by_category,
        'sales_by_category': sales_by_category,
    }
    
    return render(request, 'home/dashboard.html', context)