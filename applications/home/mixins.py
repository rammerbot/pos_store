from django.core.exceptions import PermissionDenied
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse_lazy


class AdminRequiredMixin(UserPassesTestMixin):
    """Requiere que el usuario sea un superusuario (Admin) para acceder a la vista."""

    def test_func(self):
        return self.request.user.groups.filter(name='Admin').exists()

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, '❌ No tienes permisos para acceder a esta sección.')
            return redirect(reverse_lazy('home:home'))
        return super().handle_no_permission()
    
class SellerRequiredMixin(UserPassesTestMixin):
    """Mixin que requiere que el usuario sea vendedor"""
    
    def test_func(self):
        return self.request.user.groups.filter(name='Vendedor').exists()
    
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            messages.error(self.request, '❌ No tienes permisos para acceder a esta sección.')
            return redirect(reverse_lazy('home:home'))
        return super().handle_no_permission()