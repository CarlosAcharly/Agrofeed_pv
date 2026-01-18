from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps

def solo_superadmin(user):
    return user.is_authenticated and user.rol == 'superadmin'

def superadmin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not solo_superadmin(request.user):
            raise PermissionDenied("Solo el superadministrador puede cambiar precios")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_o_superadmin(user):
    return user.is_authenticated and user.rol in ['admin', 'superadmin']

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not admin_o_superadmin(request.user):
            raise PermissionDenied("No tienes permisos de administrador")
        return view_func(request, *args, **kwargs)
    return _wrapped_view