from django.db import models

from applications.home.models import BaseModel

# Create your models here.

class Supplier(BaseModel):
    name = models.CharField(max_length=255, verbose_name='Proveedor')
    contact_person = models.CharField(max_length=255, verbose_name='Contacto', blank=True, null=True)
    phone = models.CharField(max_length=20, verbose_name='Telefono', blank=True, null=True, unique=True)
    email = models.EmailField(verbose_name='Email Address', blank=True, null=True, unique=True)
    address = models.TextField(verbose_name='Direccion', blank=True, null=True)

    class Meta:
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return self.name

    def save(self):
        self.name = self.name.upper()
        return super(Supplier, self).save()

    def toggle_status(self):
        self.status = not self.status
        self.save()
        return self.status