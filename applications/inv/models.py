from django.db import models
from applications.home.models import BaseModel

# Create your models here.

class Category(BaseModel):
    name = models.CharField("Categoria", max_length=100, unique=True)
    description = models.TextField("Descripcion", blank=True, null=True)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def save(self):
        self.name = self.name.upper()
        return super(Category, self).save()
    
    def toggle_status(self):
        self.status = not self.status
        self.save()
        return self.status
    
class SubCategory(BaseModel):
    name = models.CharField("SubCategoria", max_length=100)
    description = models.TextField("Descripcion", blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')

    class Meta:
        verbose_name = "SubCategoria"
        verbose_name_plural = "SubCategorias"
        ordering = ['name']
        unique_together = ('category', 'name')

    def __str__(self):
        return f'{self.category.name} : {self.name}'
    
    def save(self):
        self.name = self.name.upper()
        return super(SubCategory, self).save()
    
    def toggle_status(self):
        self.status = not self.status
        self.save()
        return self.status
    
class Brand(BaseModel):
    name = models.CharField("Marca", max_length=100, unique=True)
    description = models.TextField("Descripcion", blank=True, null=True)

    class Meta:
        verbose_name = "Marca"
        verbose_name_plural = "Marcas"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def save(self):
        self.name = self.name.upper()
        return super(Brand, self).save()
    
    def toggle_status(self):
        self.status = not self.status
        self.save()
        return self.status

class UnitMeasure(BaseModel):
    name = models.CharField("Unidad de Medida", max_length=50, unique=True)
    description = models.TextField("Descripcion", blank=True, null=True)

    class Meta:
        verbose_name = "Unidad de Medida"
        verbose_name_plural = "Unidades de Medida"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def save(self):
        self.name = self.name.upper()
        return super(UnitMeasure, self).save()

    def toggle_status(self):
        self.status = not self.status
        self.save()
        return self.status
    
class Product(BaseModel):
    code = models.CharField("Codigo", max_length=50, unique=True)
    bar_code = models.CharField("Codigo de Barras", max_length=50, blank=True, unique=True, null=True)
    name = models.CharField("Producto", max_length=100)
    description = models.TextField("Descripcion", blank=True, null=True)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name='products', blank=True, null=True)
    brand = models.ForeignKey(Brand, on_delete=models.CASCADE, related_name='products', blank=True, null=True)
    price = models.DecimalField("Precio", max_digits=10, decimal_places=2, default=0.00)
    stock = models.PositiveIntegerField("Stock", default=0)
    unit_measure = models.ForeignKey(UnitMeasure, on_delete=models.CASCADE, related_name='products', blank=True, null=True)
    last_purchase_price = models.DecimalField("Ultimo Precio de Compra", max_digits=10, decimal_places=2, default=0.00)
    last_buy_date = models.DateField("Ultima Fecha de Compra", blank=True, null=True)


    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ['name']
        unique_together = ('subcategory', 'name')

    def __str__(self):
        return f'{self.brand.name}: {self.name}'
    
    def save(self):
        self.name = self.name.upper()
        return super(Product, self).save()
    
    def toggle_status(self):
        self.status = not self.status
        self.save()
        return self.status