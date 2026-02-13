from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Count, Sum
from django.core.paginator import Paginator
from django.utils import timezone

from catalogos import models
from .models import Sucursal, ConfiguracionSucursal, TransferenciaInventario, DetalleTransferencia
from usuarios.decorators import puede_gestionar_sucursales, puede_transferir_productos, superadmin_required
from .forms import SucursalForm, ConfiguracionSucursalForm, TransferenciaForm
from catalogos.models import ProductoSucursal
from ventas.models import Venta, CorteCaja
from usuarios.models import Usuario
import json
from datetime import datetime, timedelta

# =========== LISTA DE SUCURSALES ===========
@login_required
@puede_gestionar_sucursales
def sucursales_lista(request):
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', 'todas')
    
    sucursales = Sucursal.objects.all()
    
    if query:
        sucursales = sucursales.filter(
            Q(codigo__icontains=query) |
            Q(nombre__icontains=query) |
            Q(direccion__icontains=query) |
            Q(ciudad__icontains=query) |
            Q(encargado__icontains=query)
        )
    
    if estado == 'activas':
        sucursales = sucursales.filter(activa=True)
    elif estado == 'inactivas':
        sucursales = sucursales.filter(activa=False)
    elif estado == 'ventas':
        sucursales = sucursales.filter(permite_ventas=True)
    elif estado == 'compras':
        sucursales = sucursales.filter(permite_compras=True)
    
    # Estadísticas
    total_sucursales = sucursales.count()
    activas_count = Sucursal.objects.filter(activa=True).count()
    inactivas_count = Sucursal.objects.filter(activa=False).count()
    
    # Obtener información adicional para cada sucursal
    sucursales_info = []
    for sucursal in sucursales:
        info = {
            'sucursal': sucursal,
            'usuarios_count': Usuario.objects.filter(sucursal=sucursal).count(),
            'productos_count': ProductoSucursal.objects.filter(sucursal=sucursal).count(),
            'ventas_hoy': Venta.objects.filter(
                sucursal=sucursal,
                fecha__date=timezone.now().date()
            ).count(),
            'caja_abierta': CorteCaja.objects.filter(
                sucursal=sucursal,
                fecha_fin__isnull=True
            ).exists(),
        }
        sucursales_info.append(info)
    
    # Paginación
    paginator = Paginator(sucursales_info, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'sucursales_info': page_obj,
        'query': query,
        'estado': estado,
        'total_sucursales': total_sucursales,
        'activas_count': activas_count,
        'inactivas_count': inactivas_count,
    }
    return render(request, 'sucursales/lista.html', context)


# =========== CREAR SUCURSAL ===========
@login_required
@puede_gestionar_sucursales
def sucursales_crear(request):
    if request.method == 'POST':
        form = SucursalForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    sucursal = form.save()
                    
                    # Crear configuración por defecto
                    ConfiguracionSucursal.objects.create(sucursal=sucursal)
                    
                    messages.success(request, 'Sucursal creada exitosamente')
                    return redirect('sucursales_lista')
                    
            except Exception as e:
                messages.error(request, f'Error al crear sucursal: {str(e)}')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario')
    else:
        form = SucursalForm()
    
    return render(request, 'sucursales/form.html', {
        'form': form,
        'titulo': 'Nueva Sucursal',
        'accion': 'Crear'
    })


# =========== EDITAR SUCURSAL ===========
@login_required
@superadmin_required
def sucursales_editar(request, pk):
    sucursal = get_object_or_404(Sucursal, pk=pk)
    
    if request.method == 'POST':
        form = SucursalForm(request.POST, instance=sucursal)
        if form.is_valid():
            sucursal = form.save()
            messages.success(request, 'Sucursal actualizada exitosamente')
            return redirect('sucursales_lista')
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario')
    else:
        form = SucursalForm(instance=sucursal)
    
    return render(request, 'sucursales/form.html', {
        'form': form,
        'titulo': 'Editar Sucursal',
        'accion': 'Actualizar',
        'sucursal': sucursal
    })


# =========== ELIMINAR SUCURSAL ===========
@login_required
@superadmin_required
def sucursales_eliminar(request, pk):
    sucursal = get_object_or_404(Sucursal, pk=pk)
    
    # Verificar dependencias
    usuarios_count = Usuario.objects.filter(sucursal=sucursal).count()
    productos_count = ProductoSucursal.objects.filter(sucursal=sucursal).count()
    ventas_count = Venta.objects.filter(sucursal=sucursal).count()
    
    if request.method == 'POST':
        if usuarios_count > 0 or productos_count > 0 or ventas_count > 0:
            messages.error(
                request, 
                'No se puede eliminar la sucursal porque tiene dependencias activas'
            )
            return redirect('sucursales_lista')
        
        sucursal.delete()
        messages.success(request, 'Sucursal eliminada exitosamente')
        return redirect('sucursales_lista')
    
    return render(request, 'sucursales/eliminar.html', {
        'sucursal': sucursal,
        'usuarios_count': usuarios_count,
        'productos_count': productos_count,
        'ventas_count': ventas_count,
    })


# =========== DETALLE SUCURSAL ===========
@login_required
@superadmin_required
def sucursales_detalle(request, pk):
    sucursal = get_object_or_404(Sucursal, pk=pk)
    
    # Obtener estadísticas
    usuarios = Usuario.objects.filter(sucursal=sucursal)
    productos_sucursal = ProductoSucursal.objects.filter(sucursal=sucursal)
    
    # Ventas del mes
    inicio_mes = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    ventas_mes = Venta.objects.filter(
        sucursal=sucursal,
        fecha__gte=inicio_mes
    )
    total_ventas_mes = sum(venta.total for venta in ventas_mes)
    
    # Caja actual
    caja_actual = CorteCaja.objects.filter(
        sucursal=sucursal,
        fecha_fin__isnull=True
    ).first()
    
    # Transferencias recientes
    transferencias_salida = TransferenciaInventario.objects.filter(
        sucursal_origen=sucursal
    ).order_by('-fecha_solicitud')[:5]
    
    transferencias_entrada = TransferenciaInventario.objects.filter(
        sucursal_destino=sucursal
    ).order_by('-fecha_solicitud')[:5]
    
    # Productos con bajo stock
    productos_bajo_stock = productos_sucursal.filter(
        stock__lte=models.F('stock_minimo')
    ).select_related('producto')[:10]
    
    context = {
        'sucursal': sucursal,
        'usuarios': usuarios,
        'usuarios_count': usuarios.count(),
        'productos_count': productos_sucursal.count(),
        'ventas_mes_count': ventas_mes.count(),
        'total_ventas_mes': total_ventas_mes,
        'caja_actual': caja_actual,
        'transferencias_salida': transferencias_salida,
        'transferencias_entrada': transferencias_entrada,
        'productos_bajo_stock': productos_bajo_stock,
        'valor_inventario': sum(
            ps.stock * ps.producto.costo_promedio 
            for ps in productos_sucursal
        ),
    }
    return render(request, 'sucursales/detalle.html', context)


# =========== CONFIGURACIÓN SUCURSAL ===========
@login_required
@superadmin_required
def sucursales_configuracion(request, pk):
    sucursal = get_object_or_404(Sucursal, pk=pk)
    
    # Obtener o crear configuración
    configuracion, created = ConfiguracionSucursal.objects.get_or_create(
        sucursal=sucursal,
        defaults={
            'stock_minimo_global': 5,
            'stock_maximo_global': 100,
            'iva_porcentaje': 16.00,
            'redondeo_ventas': True,
            'mostrar_stock': True,
            'max_intentos_login': 3,
            'tiempo_bloqueo': 15,
            'generar_reporte_diario': True,
            'hora_reporte': '22:00:00',
        }
    )
    
    if request.method == 'POST':
        form = ConfiguracionSucursalForm(request.POST, instance=configuracion)
        if form.is_valid():
            configuracion = form.save()
            messages.success(request, 'Configuración actualizada exitosamente')
            return redirect('sucursales_detalle', pk=sucursal.id)
        else:
            messages.error(request, 'Por favor corrige los errores en el formulario')
    else:
        form = ConfiguracionSucursalForm(instance=configuracion)
    
    return render(request, 'sucursales/configuracion.html', {
        'sucursal': sucursal,
        'form': form,
        'configuracion': configuracion,
    })


# =========== TRANSFERENCIAS ===========
@login_required
@puede_transferir_productos
def sucursales_transferencias_lista(request):
    estado = request.GET.get('estado', 'todas')
    sucursal_id = request.GET.get('sucursal', '')
    
    transferencias = TransferenciaInventario.objects.all().select_related(
        'sucursal_origen', 'sucursal_destino'
    ).order_by('-fecha_solicitud')
    
    if estado != 'todas':
        transferencias = transferencias.filter(estado=estado)
    
    if sucursal_id:
        transferencias = transferencias.filter(
            Q(sucursal_origen_id=sucursal_id) | Q(sucursal_destino_id=sucursal_id)
        )
    
    # Estadísticas
    estadisticas = {
        'total': transferencias.count(),
        'pendientes': transferencias.filter(estado='pendiente').count(),
        'en_proceso': transferencias.filter(estado='en_proceso').count(),
        'completadas': transferencias.filter(estado='completada').count(),
        'canceladas': transferencias.filter(estado='cancelada').count(),
    }
    
    # Paginación
    paginator = Paginator(transferencias, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    sucursales = Sucursal.objects.filter(activa=True)
    
    context = {
        'transferencias': page_obj,
        'estado': estado,
        'sucursal_id': sucursal_id,
        'estadisticas': estadisticas,
        'sucursales': sucursales,
    }
    return render(request, 'sucursales/transferencias/lista.html', context)


@login_required
@superadmin_required
def sucursales_transferencias_crear(request):
    if request.method == 'POST':
        form = TransferenciaForm(request.POST)
        if form.is_valid():
            # Lógica para crear transferencia
            pass
    
    sucursal_actual = request.user.sucursal
    form = TransferenciaForm()
    
    return render(request, 'sucursales/transferencias/crear.html', {
        'form': form,
        'sucursal_actual': sucursal_actual,
    })


@login_required
@superadmin_required
def sucursales_transferencias_detalle(request, pk):
    transferencia = get_object_or_404(TransferenciaInventario, pk=pk)
    detalles = transferencia.detalles.all().select_related('producto')
    
    return render(request, 'sucursales/transferencias/detalle.html', {
        'transferencia': transferencia,
        'detalles': detalles,
    })


# =========== REPORTES SUCURSAL ===========
@login_required
@superadmin_required
def sucursales_reportes(request, pk):
    sucursal = get_object_or_404(Sucursal, pk=pk)
    
    # Parámetros de fechas
    fecha_inicio = request.GET.get('fecha_inicio', '')
    fecha_fin = request.GET.get('fecha_fin', '')
    
    # Ventas
    ventas = Venta.objects.filter(sucursal=sucursal)
    if fecha_inicio:
        ventas = ventas.filter(fecha__date__gte=fecha_inicio)
    if fecha_fin:
        ventas = ventas.filter(fecha__date__lte=fecha_fin)
    
    total_ventas = sum(venta.total for venta in ventas)
    ventas_diarias = ventas.values('fecha__date').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('-fecha__date')[:30]
    
    # Inventario
    productos_sucursal = ProductoSucursal.objects.filter(
        sucursal=sucursal
    ).select_related('producto')
    
    valor_inventario = sum(
        ps.stock * ps.producto.costo_promedio 
        for ps in productos_sucursal
    )
    productos_bajo_stock = productos_sucursal.filter(
        stock__lte=models.F('stock_minimo')
    ).count()
    
    # Usuarios
    usuarios = Usuario.objects.filter(sucursal=sucursal)
    usuarios_activos = usuarios.filter(is_active=True).count()
    
    context = {
        'sucursal': sucursal,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'total_ventas': total_ventas,
        'ventas_count': ventas.count(),
        'ventas_diarias': ventas_diarias,
        'valor_inventario': valor_inventario,
        'productos_count': productos_sucursal.count(),
        'productos_bajo_stock': productos_bajo_stock,
        'usuarios_count': usuarios.count(),
        'usuarios_activos': usuarios_activos,
    }
    return render(request, 'sucursales/reportes.html', context)


# =========== API PARA SUCURSALES ===========
@login_required
def sucursales_estadisticas_api(request):
    sucursales = Sucursal.objects.filter(activa=True)
    
    data = []
    for sucursal in sucursales:
        # Ventas del día
        ventas_hoy = Venta.objects.filter(
            sucursal=sucursal,
            fecha__date=timezone.now().date()
        ).count()
        
        # Caja abierta
        caja_abierta = CorteCaja.objects.filter(
            sucursal=sucursal,
            fecha_fin__isnull=True
        ).exists()
        
        # Productos con bajo stock
        productos_bajo_stock = ProductoSucursal.objects.filter(
            sucursal=sucursal,
            stock__lte=models.F('stock_minimo')
        ).count()
        
        data.append({
            'id': sucursal.id,
            'nombre': sucursal.nombre,
            'codigo': sucursal.codigo,
            'ventas_hoy': ventas_hoy,
            'caja_abierta': caja_abierta,
            'productos_bajo_stock': productos_bajo_stock,
            'estado_operativo': sucursal.estado_operativo,
        })
    
    return JsonResponse({'sucursales': data})


# =========== TOGGLE ESTADO SUCURSAL ===========
@login_required
@superadmin_required
def sucursales_toggle(request, pk):
    sucursal = get_object_or_404(Sucursal, pk=pk)
    
    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        if accion == 'activar':
            sucursal.activa = True
            mensaje = 'Sucursal activada exitosamente'
        elif accion == 'desactivar':
            sucursal.activa = False
            mensaje = 'Sucursal desactivada exitosamente'
        elif accion == 'toggle_ventas':
            sucursal.permite_ventas = not sucursal.permite_ventas
            estado = 'habilitadas' if sucursal.permite_ventas else 'deshabilitadas'
            mensaje = f'Ventas {estado} en la sucursal'
        elif accion == 'toggle_compras':
            sucursal.permite_compras = not sucursal.permite_compras
            estado = 'habilitadas' if sucursal.permite_compras else 'deshabilitadas'
            mensaje = f'Compras {estado} en la sucursal'
        else:
            messages.error(request, 'Acción no válida')
            return redirect('sucursales_detalle', pk=pk)
        
        sucursal.save()
        messages.success(request, mensaje)
    
    return redirect('sucursales_detalle', pk=pk)