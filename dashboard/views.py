from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from ventas.models import Venta
from catalogos.models import ProductoSucursal
from sucursales.models import Sucursal
from usuarios.models import Usuario
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@login_required
def dashboard(request):
    sucursal = request.user.sucursal
    hoy = timezone.now()
    
    # Estadísticas para el dashboard
    if sucursal:
        # Ventas de hoy
        ventas_hoy = Venta.objects.filter(
            sucursal=sucursal,
            fecha__date=hoy.date()
        )
        total_hoy = sum(venta.total for venta in ventas_hoy) if ventas_hoy else 0
        
        # Productos con bajo stock
        productos_bajo_stock = ProductoSucursal.objects.filter(
            sucursal=sucursal,
            stock__lt=10
        ).count()
        
        context = {
            'ventas_hoy': ventas_hoy.count(),
            'total_hoy': total_hoy,
            'productos_bajo_stock': productos_bajo_stock,
            'sucursal': sucursal,
        }
    else:
        # Vista para superadmin
        ventas_hoy = Venta.objects.filter(fecha__date=hoy.date())
        total_hoy = sum(venta.total for venta in ventas_hoy) if ventas_hoy else 0
        
        context = {
            'ventas_hoy': ventas_hoy.count(),
            'total_hoy': total_hoy,
            'sucursales_count': Sucursal.objects.count(),
            'usuarios_count': Usuario.objects.count(),
        }
    
    return render(request, 'dashboard/dashboard.html', context)

@csrf_exempt
@login_required
def set_sidebar_state(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            collapsed = data.get('collapsed', False)
            request.session['sidebar_collapsed'] = collapsed
            return JsonResponse({'status': 'success'})
        except:
            return JsonResponse({'status': 'error'}, status=400)
    return JsonResponse({'status': 'error'}, status=405)