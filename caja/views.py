from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import JsonResponse
from ventas.models import CorteCaja, Venta  # ¡Importar de ventas!
from sucursales.models import Sucursal
from usuarios.decorators import admin_required
import json

@login_required
@admin_required
def caja_principal(request):
    sucursal = request.user.sucursal
    if not sucursal:
        messages.error(request, "No tienes una sucursal asignada")
        return redirect('dashboard')
    
    # Buscar corte de caja activo
    corte_activo = CorteCaja.objects.filter(
        sucursal=sucursal,
        fecha_fin__isnull=True
    ).first()
    
    # Calcular ventas del día
    hoy = timezone.now().date()
    ventas_hoy = Venta.objects.filter(
        sucursal=sucursal,
        fecha__date=hoy
    )
    total_hoy = sum(venta.total for venta in ventas_hoy)
    
    context = {
        'sucursal': sucursal,
        'corte_activo': corte_activo,
        'ventas_hoy': ventas_hoy.count(),
        'total_hoy': total_hoy,
    }
    
    return render(request, 'caja/principal.html', context)

@login_required
@admin_required
def apertura_caja(request):
    sucursal = request.user.sucursal
    if not sucursal:
        messages.error(request, "No tienes una sucursal asignada")
        return redirect('caja_principal')
    
    # Verificar si ya hay un corte activo
    corte_activo = CorteCaja.objects.filter(
        sucursal=sucursal,
        fecha_fin__isnull=True
    ).first()
    
    if corte_activo:
        messages.warning(request, "Ya hay una caja abierta")
        return redirect('caja_principal')
    
    if request.method == 'POST':
        try:
            # Crear nuevo corte de caja
            corte = CorteCaja.objects.create(
                sucursal=sucursal,
                usuario=request.user,
                fecha_inicio=timezone.now(),
                fecha_fin=None,
                total_ventas=0
            )
            
            messages.success(request, "Caja abierta exitosamente")
            return redirect('caja_principal')
        except Exception as e:
            messages.error(request, f"Error al abrir caja: {str(e)}")
    
    return render(request, 'caja/apertura.html', {'sucursal': sucursal})

@login_required
@admin_required
def cierre_caja(request):
    sucursal = request.user.sucursal
    if not sucursal:
        messages.error(request, "No tienes una sucursal asignada")
        return redirect('caja_principal')
    
    # Buscar corte activo
    corte_activo = CorteCaja.objects.filter(
        sucursal=sucursal,
        fecha_fin__isnull=True
    ).first()
    
    if not corte_activo:
        messages.error(request, "No hay caja abierta para cerrar")
        return redirect('caja_principal')
    
    if request.method == 'POST':
        try:
            # Calcular ventas durante el período del corte
            ventas_periodo = Venta.objects.filter(
                sucursal=sucursal,
                fecha__gte=corte_activo.fecha_inicio,
                fecha__lte=timezone.now()
            )
            total_ventas = sum(venta.total for venta in ventas_periodo)
            
            # Actualizar corte
            corte_activo.fecha_fin = timezone.now()
            corte_activo.total_ventas = total_ventas
            corte_activo.save()
            
            messages.success(request, f"Caja cerrada exitosamente. Total ventas: ${total_ventas:.2f}")
            return redirect('caja_principal')
        except Exception as e:
            messages.error(request, f"Error al cerrar caja: {str(e)}")
    
    # Obtener ventas para mostrar en el resumen
    ventas_periodo = Venta.objects.filter(
        sucursal=sucursal,
        fecha__gte=corte_activo.fecha_inicio
    )
    
    context = {
        'sucursal': sucursal,
        'corte_activo': corte_activo,
        'ventas_periodo': ventas_periodo,
        'total_ventas': sum(venta.total for venta in ventas_periodo),
        'cantidad_ventas': ventas_periodo.count(),
    }
    
    return render(request, 'caja/cierre.html', context)

@login_required
@admin_required
def historial_cortes(request):
    sucursal = request.user.sucursal
    if not sucursal:
        messages.error(request, "No tienes una sucursal asignada")
        return redirect('dashboard')
    
    cortes = CorteCaja.objects.filter(
        sucursal=sucursal
    ).order_by('-fecha_inicio')
    
    return render(request, 'caja/historial.html', {
        'cortes': cortes,
        'sucursal': sucursal
    })

@login_required
@admin_required
def detalle_corte(request, pk):
    corte = get_object_or_404(CorteCaja, pk=pk)
    
    # Verificar que el corte pertenezca a la sucursal del usuario
    if request.user.sucursal != corte.sucursal:
        messages.error(request, "No tienes permiso para ver este corte")
        return redirect('historial_cortes')
    
    # Obtener ventas del período
    ventas = Venta.objects.filter(
        sucursal=corte.sucursal,
        fecha__gte=corte.fecha_inicio,
        fecha__lte=corte.fecha_fin if corte.fecha_fin else timezone.now()
    )
    
    return render(request, 'caja/detalle_corte.html', {
        'corte': corte,
        'ventas': ventas,
        'total_ventas': sum(venta.total for venta in ventas),
        'cantidad_ventas': ventas.count(),
    })