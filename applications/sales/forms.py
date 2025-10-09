from django import forms

from .models import Customer, Sale

# Forms for Customer
class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'last_name','dni' , 'phone', 'email', 'address','type_customer', 'gender', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el nombre del cliente...'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el Apellido...'}),
            'dni': forms.TextInput(attrs={'class': 'form-control', 'unique': True, 'placeholder': 'Ingrese el DNI...'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'unique': True, 'placeholder': 'Ingrese el telefono...'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Ingrese el correo electronico...', 'unique': True}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Ingrese la direccion...', 'rows': 3}),
            'type_customer': forms.Select(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Cliente',
            'last_name': 'Apellido',
            'dni': 'DNI',
            'phone': 'Telefono',
            'email': 'Email Address',
            'address': 'Direccion',
            'type_customer': 'Tipo de Cliente',
            'gender': 'Genero',
        }


class SaleForm(forms.ModelForm):
    date = forms.DateInput()
    
    class Meta:
        model=Sale
        fields=['customer', 'observation', 
            'subtotal', 'discount', 'tax', 'total_amount', 'discount']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in iter(self.fields):
            self.fields[field].widget.attrs.update({
                'class': 'form-control'
            })
        self.fields['subtotal'].widget.attrs['readonly'] = True
        self.fields['discount'].widget.attrs['readonly'] = True
        self.fields['tax'].widget.attrs['readonly'] = True
        self.fields['total_amount'].widget.attrs['readonly'] = True

