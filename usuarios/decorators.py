# usuarios/decorators.py (ACTUALIZAR con esta versión)
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from functools import wraps

def superadmin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'es_superadmin') or not request.user.es_superadmin:
            from django.contrib import messages
            messages.error(request, 'No tienes permisos de superadministrador')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'es_admin') or not request.user.es_admin:
            from django.contrib import messages
            messages.error(request, 'No tienes permisos de administrador')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def cajero_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'es_cajero') or not request.user.es_cajero:
            from django.contrib import messages
            messages.error(request, 'No tienes permisos de cajero')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# ===== NUEVOS DECORADORES ESPECÍFICOS =====
def puede_editar_precios(view_func):
    """Solo admin y superadmin pueden editar precios"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'es_admin') or not request.user.es_admin:
            from django.contrib import messages
            messages.error(request, 'No tienes permiso para editar precios')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def puede_eliminar_ventas(view_func):
    """Solo admin y superadmin pueden eliminar ventas"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'es_admin') or not request.user.es_admin:
            from django.contrib import messages
            messages.error(request, 'No tienes permiso para eliminar ventas')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def puede_gestionar_sucursales(view_func):
    """Solo superadmin puede gestionar sucursales"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'es_superadmin') or not request.user.es_superadmin:
            from django.contrib import messages
            messages.error(request, 'Solo superadmin puede gestionar sucursales')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def puede_transferir_productos(view_func):
    """Solo superadmin puede transferir productos"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not hasattr(request.user, 'es_superadmin') or not request.user.es_superadmin:
            from django.contrib import messages
            messages.error(request, 'Solo superadmin puede transferir productos')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view