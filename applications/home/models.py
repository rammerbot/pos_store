from django.db import models
from django.contrib.auth.models import User

# Create your models here.

class BaseModel(models.Model):

    status = models.BooleanField("Estado", default=True)
    created_at = models.DateTimeField("Fecha de creacion", auto_now_add=True)
    updated_at = models.DateTimeField("Fecha de modificacion",auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='%(class)s_created_by', verbose_name="Creado por")
    modified_by = models.IntegerField("Modificado por", null=True, blank=True)

    class Meta:
        abstract = True