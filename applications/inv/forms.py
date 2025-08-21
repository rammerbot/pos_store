from django import forms

from .models import Category, SubCategory, Brand, UnitMeasure, Product

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'description', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Categoria'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descripcion de la Categoria'}),
        }
        labels = {
            'name' : 'Categoria',
            'description' : 'Descripcion', 
            'status': 'Activo'
            }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError("El nombre de la categoria es obligatorio.")
        return name.upper()  # Ensure the name is stored in uppercase
    
class SubCategoryForm(forms.ModelForm):
    class Meta:
        model = SubCategory
        fields = ['category','name', 'description', 'status']
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la SubCategoria'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descripcion de la SubCategoria'}),
        }
        labels = {
            'category': 'Categoria',
            'name' : 'Sub Categoria',
            'description' : 'Descripcion',
            'status': 'Activo'
            }
    
    
    def __init__(self, *args, **kwargs):
        super(SubCategoryForm, self).__init__(*args, **kwargs)
        
        # Filtrar solo las categorías activas para el queryset
        self.fields['category'].queryset = Category.objects.filter(status=True).order_by('name')
        
        # Mejorar la presentación del select de categoría
        self.fields['category'].empty_label = "Seleccione una categoría"
        self.fields['category'].widget.attrs.update({'class': 'form-control'})

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError("El nombre de la categoria es obligatorio.")
        return name.upper()  # Ensure the name is stored in uppercase
    

class BrandForm(forms.ModelForm):
    class Meta:
        model = Brand
        fields = ['name','description', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Marca'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descripcion de la Marca'}),
        }
        labels = {
            'name': 'Marca',
            'description' : 'Descripcion',
            'status': 'Activo'
            }

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError("El nombre de la Marca es obligatorio.")
        return name.upper()  # Ensure the name is stored in uppercase
    

class UnitMeasureForm(forms.ModelForm):
    class Meta:
        model = UnitMeasure
        fields = ['name', 'description', 'status']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la Unidad de Medida'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Descripcion de la Unidad de Medida'}),
        }
        labels = {
            'name' : 'Unidad de Medida',
            'description' : 'Descripcion',
            'status': 'Activo'
            }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError("El nombre de la unidad de medida es obligatorio.")
        return name.upper()  # Ensure the name is stored in uppercase
    

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
                'code', 'bar_code', 'subcategory', 'brand',
                  'name', 'description','price', 'stock', 'unit_measure',  'status', 'last_purchase_price', 'last_buy_date'
                  ]
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control ml-2', 'placeholder': 'Codigo del Producto'}),
            'bar_code': forms.TextInput(attrs={'class': 'form-control ml-2', 'placeholder': 'Codigo de Barras'}),
            'subcategory': forms.Select(attrs={'class': 'form-control ml-4'}),
            'brand': forms.Select(attrs={'class': 'form-control ml-2'}),
            'name': forms.TextInput(attrs={'class': 'form-control ml-2', 'placeholder': 'Nombre del Producto'}),
            'description': forms.TextInput(attrs={'class': 'form-control ml-2', 'placeholder': 'Descripcion del Producto'}),
            'price': forms.NumberInput(attrs={'class': 'form-control ml-2', 'placeholder': 'Precio del Producto'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control ml-2', 'placeholder': 'cantidad de Stock'}),
            'unit_measure': forms.Select(attrs={'class': 'form- ml-2'}),
            'last_purchase_price': forms.NumberInput(attrs={'class': 'form-control ml-2', 'placeholder': 'Ultimo Precio de Compra', 'readonly': 'True'}),
            'last_buy_date' : forms.DateInput(attrs={'class': 'form-control ml-2', 'placeholder': 'Ultima Fecha de Compra', 'type': 'date', 'readonly': 'True'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input ml-2'})


        }
        labels = {
            'code': 'Codigo',
            'bar_code': 'Codigo de Barras',
            'subcategory': 'Sub Categoria',
            'brand': 'Marca',
            'name' : 'Nombre del Producto',
            'description' : 'Descripcion',
            'price': 'Precio',
            'stock': 'Cantidad en Stock',
            'unit_measure': 'Unidad de Medida',
            'status': 'Activo',
            'last_purchase_price': 'Ultimo Precio de Compra',
            'last_buy_date': 'Ultima Fecha de Compra'

            }
    
    
    def __init__(self, *args, **kwargs):
        super(ProductForm, self).__init__(*args, **kwargs)
        
        # Filtrar solo las Subcategorías activas para el queryset
        self.fields['subcategory'].queryset = SubCategory.objects.filter(status=True).order_by('name')
        
        # Mejorar la presentación del select de Subcategoría
        self.fields['subcategory'].empty_label = "Seleccione una Subcategoría"
        self.fields['subcategory'].widget.attrs.update({'class': 'form-control'})

         # Filtrar solo las Marcas activas para el queryset
        self.fields['brand'].queryset = Brand.objects.filter(status=True).order_by('name')
        
        # Mejorar la presentación del select de categoría
        self.fields['brand'].empty_label = "Seleccione una Marca"
        self.fields['brand'].widget.attrs.update({'class': 'form-control'})

         # Filtrar solo las unidades de medidas activas para el queryset
        self.fields['unit_measure'].queryset = UnitMeasure.objects.filter(status=True).order_by('name')
        
        # Mejorar la presentación del select de categoría
        self.fields['unit_measure'].empty_label = "Seleccione una Unidad de Medida"
        self.fields['unit_measure'].widget.attrs.update({'class': 'form-control'})

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name:
            raise forms.ValidationError("El nombre del producto es obligatorio.")
        return name.upper()  # Ensure the name is stored in uppercase