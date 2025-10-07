from django import forms

from .models import Supplier, PurchaseOrder, PurchaseItem

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


class PurchaseForm(forms.ModelForm):
    buy_date = forms.DateInput()
    order_date = forms.DateInput()
    
    class Meta:
        model=PurchaseOrder
        fields=['supplier', 'buy_date', 'observations', 'order_number', 
            'order_date', 'subtotal', 'discount', 'tax', 'total_amount']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control'
            })
        self.fields['buy_date'].widget.attrs['readonly'] = True
        self.fields['order_date'].widget.attrs['readonly'] = True
        self.fields['subtotal'].widget.attrs['readonly'] = True
        self.fields['discount'].widget.attrs['readonly'] = True
        self.fields['tax'].widget.attrs['readonly'] = True
        self.fields['total_amount'].widget.attrs['readonly'] = True

