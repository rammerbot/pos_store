# home/templatetags/auth_extras.py
from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """Verifica si el usuario pertenece a un grupo específico"""
    if user.is_authenticated:
        return user.groups.filter(name=group_name).exists()
    return False

@register.simple_tag
def user_in_groups(user, *group_names):
    """Verifica si el usuario pertenece a alguno de los grupos especificados"""
    if user.is_authenticated:
        return user.groups.filter(name__in=group_names).exists()
    return False