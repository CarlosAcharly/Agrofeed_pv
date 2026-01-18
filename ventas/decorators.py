from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from functools import wraps

def admin_required(view_func):
    """Requiere que el usuario sea admin o superadmin"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.rol in ['admin', 'superadmin']:
            return view_func(request, *args, **kwargs)
        
        from django.contrib import messages
        messages.error(request, 'No tienes permisos de administrador para acceder a esta página.')
        return redirect('dashboard')
    return _wrapped_view

def superadmin_required(view_func):
    """Requiere que el usuario sea superadmin"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.rol == 'superadmin':
            return view_func(request, *args, **kwargs)
        
        from django.contrib import messages
        messages.error(request, 'No tienes permisos de superadministrador para acceder a esta página.')
        return redirect('dashboard')
    return _wrapped_view

def cajero_required(view_func):
    """Requiere que el usuario sea cajero"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        
        if request.user.rol == 'cajero':
            return view_func(request, *args, **kwargs)
        
        from django.contrib import messages
        messages.error(request, 'No tienes permisos de cajero para acceder a esta página.')
        return redirect('dashboard')
    return _wrapped_view