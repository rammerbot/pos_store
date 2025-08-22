from django import forms

from .models import Supplier

# Forms for Supplier
class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'phone', 'email', 'address', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre del proveedor...'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre del contacto...'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'unique': True, 'placeholder': 'Ingrese el telefono...'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el correo electronico...', 'unique': True}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Ingrese la direccion...', 'rows': 3}),
        }
        labels = {
            'name': 'Proveedor',
            'contact_person': 'Contacto',
            'phone': 'Telefono',
            'email': 'Email Address',
            'address': 'Direccion',
        }