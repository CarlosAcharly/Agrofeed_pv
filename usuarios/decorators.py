from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps

def superadmin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        # Verificar si tiene la propiedad es_superadmin
        if not hasattr(request.user, 'es_superadmin') or not request.user.es_superadmin:
            raise PermissionDenied("No tienes permiso para acceder a esta página")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        # Verificar si tiene la propiedad es_admin
        if not hasattr(request.user, 'es_admin') or not request.user.es_admin:
            raise PermissionDenied("No tienes permiso para acceder a esta página")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def cajero_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        # Verificar si tiene la propiedad es_cajero
        if not hasattr(request.user, 'es_cajero') or not request.user.es_cajero:
            raise PermissionDenied("No tienes permiso para acceder a esta página")
        return view_func(request, *args, **kwargs)
    return _wrapped_view