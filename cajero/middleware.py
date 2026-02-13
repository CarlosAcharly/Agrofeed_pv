from django.shortcuts import redirect
from django.urls import reverse

class CajeroRedirectMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Si el usuario está autenticado y es cajero
        if request.user.is_authenticated and hasattr(request.user, 'rol'):
            if request.user.rol == 'cajero':
                # Redirigir de la página principal a dashboard de cajero
                if request.path == '/' or request.path == '/dashboard/':
                    return redirect('cajero_dashboard')
                
                # Evitar que cajeros accedan a admin
                admin_paths = ['/admin/', '/catalogos/', '/sucursales/', '/usuarios/']
                if any(request.path.startswith(path) for path in admin_paths):
                    return redirect('cajero_dashboard')
        
        return response