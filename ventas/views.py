from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.db.models import Q, Sum, Count, Avg
from django.core.paginator import Paginator
from django.utils import timezone
from decimal import Decimal, InvalidOperation
import json
from datetime import datetime, timedelta

from usuarios.decorators import puede_eliminar_ventas

from .models import Venta, DetalleVenta, CorteCaja
from catalogos.models import ProductoSucursal, Cliente, MovimientoInventario
from sucursales.models import Sucursal
from .decorators import admin_required, superadmin_required

# =========== FUNCIONES HELPER ===========
def usuario_puede_editar_descuento(user):
    """Verifica si el usuario puede editar descuentos"""
    if not user.is_authenticated:
        return False
    
    # Usar propiedades si existen
    if hasattr(user, 'es_admin'):
        return user.es_admin or user.es_superadmin
    
    # Compatibilidad con versiones anteriores
    if hasattr(user, 'rol'):
        return user.rol in ['admin', 'superadmin']
    
    return False


def usuario_es_admin(user):
    """Verifica si el usuario es admin o superadmin"""
    if not user.is_authenticated:
        return False
    
    # Usar propiedades si existen
    if hasattr(user, 'es_admin'):
        return user.es_admin or user.es_superadmin
    
    # Compatibilidad con versiones anteriores
    if hasattr(user, 'rol'):
        return user.rol in ['admin', 'superadmin']
    
    return False
# ==========================================

# =========== VENTAS ===========
@login_required
@admin_required
def nueva_venta(request):
    """Página para crear nueva venta"""
    sucursal = request.user.sucursal
    if not sucursal:
        messages.error(request, "No tienes una sucursal asignada")
        return redirect('dashboard')
    
    # Obtener productos disponibles
    productos = ProductoSucursal.objects.filter(
        sucursal=sucursal,
        stock__gt=0,
        activo=True,
        producto__activo=True
    ).select_related('producto', 'producto__categoria')
    
    # Obtener cliente si está en sesión
    cliente_id = request.session.get('cliente_id')
    cliente = None
    if cliente_id:
        try:
            cliente = Cliente.objects.get(id=cliente_id, activo=True)
        except Cliente.DoesNotExist:
            cliente = None
    
    # Obtener carrito de sesión
    carrito = request.session.get('carrito', [])
    
    # Calcular totales
    subtotal = sum(Decimal(str(item.get('subtotal', 0))) for item in carrito)
    descuento_total = Decimal('0')
    
    if cliente and cliente.porcentaje_descuento > 0:
        descuento_total = subtotal * (cliente.porcentaje_descuento / Decimal('100'))
    
    total = subtotal - descuento_total
    
    # Obtener categorías para filtro
    from catalogos.models import Categoria
    categorias = Categoria.objects.filter(activa=True)
    
    # Obtener últimos clientes para sugerencias
    ultimos_clientes = Cliente.objects.filter(activo=True).order_by('-fecha_registro')[:10]
    
    context = {
        'productos': productos,
        'categorias': categorias,
        'carrito': carrito,
        'subtotal': subtotal,
        'descuento_total': descuento_total,
        'total': total,
        'sucursal': sucursal,
        'cliente': cliente,
        'ultimos_clientes': ultimos_clientes,
    }
    return render(request, 'ventas/nueva.html', context)

@login_required
@admin_required
@csrf_exempt
def agregar_item(request):
    """Agregar producto al carrito"""
    if request.method == 'POST':
        try:
            producto_id = request.POST.get('producto_id')
            cantidad = Decimal(request.POST.get('cantidad', 1))
            
            producto_sucursal = get_object_or_404(
                ProductoSucursal,
                id=producto_id,
                sucursal=request.user.sucursal,
                activo=True
            )
            
            if cantidad > producto_sucursal.stock:
                return JsonResponse({
                    'success': False,
                    'error': f'Stock insuficiente. Disponible: {producto_sucursal.stock}'
                })
            
            carrito = request.session.get('carrito', [])
            
            # Verificar si el producto ya está en el carrito
            item_encontrado = False
            for item in carrito:
                if item['id'] == producto_sucursal.id:
                    item['cantidad'] = float(Decimal(str(item['cantidad'])) + cantidad)
                    item['subtotal'] = float(item['precio'] * Decimal(str(item['cantidad'])))
                    item_encontrado = True
                    break
            
            # Si no está en el carrito, agregarlo
            if not item_encontrado:
                item = {
                    'id': producto_sucursal.id,
                    'nombre': producto_sucursal.producto.nombre,
                    'codigo': producto_sucursal.producto.codigo,
                    'precio': float(producto_sucursal.precio_venta),
                    'cantidad': float(cantidad),
                    'subtotal': float(producto_sucursal.precio_venta * cantidad),
                    'stock': float(producto_sucursal.stock),
                    'tiene_iva': producto_sucursal.producto.tiene_iva,
                }
                carrito.append(item)
            
            request.session['carrito'] = carrito
            request.session.modified = True
            
            # Recalcular con descuento si hay cliente
            cliente_id = request.session.get('cliente_id')
            descuento_porcentaje = 0
            
            if cliente_id:
                try:
                    cliente = Cliente.objects.get(id=cliente_id, activo=True)
                    descuento_porcentaje = float(cliente.porcentaje_descuento)
                except:
                    pass
            
            subtotal_calc = sum(item['subtotal'] for item in carrito)
            descuento_total_calc = subtotal_calc * (descuento_porcentaje / 100)
            total_calc = subtotal_calc - descuento_total_calc
            
            return JsonResponse({
                'success': True,
                'carrito': carrito,
                'carrito_count': len(carrito),
                'subtotal': subtotal_calc,
                'descuento_total': descuento_total_calc,
                'total': total_calc,
                'descuento_porcentaje': descuento_porcentaje
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
@admin_required
@csrf_exempt
def remover_item(request):
    """Remover producto del carrito"""
    if request.method == 'POST':
        try:
            item_id = int(request.POST.get('item_id'))
            carrito = request.session.get('carrito', [])
            
            carrito = [item for item in carrito if item['id'] != item_id]
            request.session['carrito'] = carrito
            request.session.modified = True
            
            # Recalcular con descuento si hay cliente
            cliente_id = request.session.get('cliente_id')
            descuento_porcentaje = 0
            
            if cliente_id:
                try:
                    cliente = Cliente.objects.get(id=cliente_id, activo=True)
                    descuento_porcentaje = float(cliente.porcentaje_descuento)
                except:
                    pass
            
            subtotal = sum(item['subtotal'] for item in carrito)
            descuento_total = subtotal * (descuento_porcentaje / 100)
            total = subtotal - descuento_total
            
            return JsonResponse({
                'success': True,
                'carrito': carrito,
                'carrito_count': len(carrito),
                'subtotal': subtotal,
                'descuento_total': descuento_total,
                'total': total,
                'descuento_porcentaje': descuento_porcentaje
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
@admin_required
@csrf_exempt
def actualizar_cantidad(request):
    """Actualizar cantidad de producto en carrito"""
    if request.method == 'POST':
        try:
            item_id = int(request.POST.get('item_id'))
            cantidad = Decimal(request.POST.get('cantidad', 1))
            
            if cantidad <= 0:
                return JsonResponse({
                    'success': False,
                    'error': 'La cantidad debe ser mayor a 0'
                })
            
            # Verificar stock
            producto_sucursal = get_object_or_404(
                ProductoSucursal,
                id=item_id,
                sucursal=request.user.sucursal
            )
            
            if cantidad > producto_sucursal.stock:
                return JsonResponse({
                    'success': False,
                    'error': f'Stock insuficiente. Disponible: {producto_sucursal.stock}'
                })
            
            carrito = request.session.get('carrito', [])
            
            for item in carrito:
                if item['id'] == item_id:
                    item['cantidad'] = float(cantidad)
                    item['subtotal'] = float(item['precio'] * cantidad)
                    break
            
            request.session['carrito'] = carrito
            request.session.modified = True
            
            # Recalcular con descuento si hay cliente
            cliente_id = request.session.get('cliente_id')
            descuento_porcentaje = 0
            
            if cliente_id:
                try:
                    cliente = Cliente.objects.get(id=cliente_id, activo=True)
                    descuento_porcentaje = float(cliente.porcentaje_descuento)
                except:
                    pass
            
            subtotal = sum(item['subtotal'] for item in carrito)
            descuento_total = subtotal * (descuento_porcentaje / 100)
            total = subtotal - descuento_total
            
            return JsonResponse({
                'success': True,
                'carrito': carrito,
                'carrito_count': len(carrito),
                'subtotal': subtotal,
                'descuento_total': descuento_total,
                'total': total,
                'descuento_porcentaje': descuento_porcentaje
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
@admin_required
@csrf_exempt
def seleccionar_cliente(request):
    """Seleccionar cliente para la venta actual"""
    if request.method == 'POST':
        try:
            cliente_id = request.POST.get('cliente_id')
            
            if cliente_id:
                cliente = get_object_or_404(Cliente, id=cliente_id, activo=True)
                request.session['cliente_id'] = cliente.id
                
                # Recalcular total con descuento
                carrito = request.session.get('carrito', [])
                subtotal = sum(item['subtotal'] for item in carrito)
                descuento_total = subtotal * (float(cliente.porcentaje_descuento) / 100)
                total = subtotal - descuento_total
                
                return JsonResponse({
                    'success': True,
                    'cliente': {
                        'id': cliente.id,
                        'nombre': cliente.nombre_completo,
                        'codigo': cliente.codigo,
                        'telefono': cliente.telefono,
                        'email': cliente.email,
                        'tipo_cliente': cliente.get_tipo_cliente_display(),
                        'tipo_cliente_valor': cliente.tipo_cliente,
                        'descuento': float(cliente.porcentaje_descuento)
                    },
                    'subtotal': subtotal,
                    'descuento_total': descuento_total,
                    'total': total,
                    'descuento_porcentaje': float(cliente.porcentaje_descuento)
                })
            else:
                # Remover cliente
                if 'cliente_id' in request.session:
                    del request.session['cliente_id']
                
                # Recalcular total sin descuento
                carrito = request.session.get('carrito', [])
                subtotal = sum(item['subtotal'] for item in carrito)
                total = subtotal
                
                return JsonResponse({
                    'success': True,
                    'cliente': None,
                    'subtotal': subtotal,
                    'descuento_total': 0,
                    'total': total,
                    'descuento_porcentaje': 0
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
@csrf_exempt
def buscar_cliente(request):
    """Búsqueda rápida de clientes"""
    if request.method == 'GET':
        query = request.GET.get('q', '')
        
        clientes = Cliente.objects.filter(
            Q(codigo__icontains=query) |
            Q(nombre__icontains=query) |
            Q(apellido__icontains=query) |
            Q(telefono__icontains=query) |
            Q(email__icontains=query) |
            Q(rfc__icontains=query),
            activo=True
        ).order_by('nombre', 'apellido')[:10]
        
        results = []
        for cliente in clientes:
            results.append({
                'id': cliente.id,
                'codigo': cliente.codigo,
                'nombre': cliente.nombre_completo,
                'telefono': cliente.telefono,
                'email': cliente.email,
                'rfc': cliente.rfc,
                'tipo_cliente': cliente.get_tipo_cliente_display(),
                'tipo_cliente_valor': cliente.tipo_cliente,
                'descuento': float(cliente.porcentaje_descuento),
                'direccion': cliente.direccion_facturacion,
                'fecha_registro': cliente.fecha_registro.strftime('%d/%m/%Y'),
                'total_compras': cliente.total_compras,
                'monto_total_compras': float(cliente.monto_total_compras)
            })
        
        return JsonResponse({'clientes': results})
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
@admin_required
def finalizar_venta(request):
    """Procesar y finalizar la venta"""
    if request.method == 'POST':
        carrito = request.session.get('carrito', [])
        
        if not carrito:
            messages.error(request, 'El carrito está vacío')
            return redirect('venta_nueva')
        
        sucursal = request.user.sucursal
        if not sucursal:
            messages.error(request, "No tienes una sucursal asignada")
            return redirect('venta_nueva')
        
        try:
            with transaction.atomic():
                # Obtener cliente si existe
                cliente_id = request.session.get('cliente_id')
                cliente = None
                if cliente_id:
                    cliente = Cliente.objects.get(id=cliente_id, activo=True)
                
                # Calcular totales
                subtotal = sum(Decimal(str(item['subtotal'])) for item in carrito)
                descuento_total = Decimal('0')
                descuento_porcentaje = Decimal('0')
                
                if cliente and cliente.porcentaje_descuento > 0:
                    descuento_porcentaje = cliente.porcentaje_descuento
                    descuento_total = subtotal * (descuento_porcentaje / Decimal('100'))
                
                total = subtotal - descuento_total
                
                # Obtener datos del formulario
                forma_pago = request.POST.get('forma_pago', 'efectivo')
                efectivo_recibido = Decimal(request.POST.get('efectivo_recibido', 0))
                observaciones = request.POST.get('observaciones', '')
                
                # Crear venta
                venta = Venta.objects.create(
                    sucursal=sucursal,
                    usuario=request.user,
                    cliente=cliente,
                    subtotal=subtotal,
                    descuento_total=descuento_total,
                    descuento_porcentaje=descuento_porcentaje,
                    total=total,
                    forma_pago=forma_pago,
                    efectivo_recibido=efectivo_recibido,
                    observaciones=observaciones,
                    creado_por=request.user
                )
                
                # Crear detalles de venta y actualizar stock
                for item in carrito:
                    producto_sucursal = get_object_or_404(
                        ProductoSucursal,
                        id=item['id'],
                        sucursal=sucursal
                    )
                    
                    # Precios
                    precio_unitario = Decimal(str(item['precio']))
                    precio_final = precio_unitario
                    descuento_unitario = Decimal('0')
                    
                    # Aplicar descuento del cliente
                    if cliente and cliente.porcentaje_descuento > 0:
                        descuento_unitario = precio_unitario * (cliente.porcentaje_descuento / Decimal('100'))
                        precio_final = precio_unitario - descuento_unitario
                    
                    # Calcular subtotal con descuento
                    cantidad = Decimal(str(item['cantidad']))
                    subtotal_item = precio_final * cantidad
                    
                    # Registrar movimiento de inventario
                    cantidad_anterior = producto_sucursal.stock
                    producto_sucursal.stock -= cantidad
                    producto_sucursal.save()
                    
                    MovimientoInventario.objects.create(
                        producto_sucursal=producto_sucursal,
                        tipo='salida',
                        cantidad=cantidad,
                        cantidad_anterior=cantidad_anterior,
                        cantidad_nueva=producto_sucursal.stock,
                        motivo=f'Venta #{venta.folio if hasattr(venta, "folio") else venta.id} - Cliente: {cliente.nombre_completo if cliente else "Público general"}',
                        usuario=request.user,
                        referencia=f'VENTA-{venta.folio if hasattr(venta, "folio") else venta.id}'
                    )
                    
                    # Crear detalle de venta
                    detalle_data = {
                        'venta': venta,
                        'producto': producto_sucursal,
                        'cantidad': cantidad,
                        'precio_unitario': precio_unitario,
                        'precio_final': precio_final,
                        'descuento_unitario': descuento_unitario,
                        'subtotal': subtotal_item,
                        'tiene_iva': item.get('tiene_iva', True)
                    }
                    
                    # Agregar descuento_porcentaje si existe el campo
                    if hasattr(DetalleVenta, 'descuento_porcentaje'):
                        detalle_data['descuento_porcentaje'] = cliente.porcentaje_descuento if cliente else Decimal('0')
                    
                    DetalleVenta.objects.create(**detalle_data)
                
                # Actualizar corte de caja actual si existe
                corte_actual = CorteCaja.objects.filter(
                    sucursal=sucursal,
                    estado='abierto',
                    usuario=request.user
                ).first()
                
                if corte_actual and hasattr(corte_actual, 'ventas_incluidas'):
                    corte_actual.ventas_incluidas.add(venta)
                    if hasattr(corte_actual, 'calcular_totales'):
                        corte_actual.calcular_totales()
                
                # Limpiar sesión
                if 'carrito' in request.session:
                    del request.session['carrito']
                if 'cliente_id' in request.session:
                    del request.session['cliente_id']
                
                folio_text = venta.folio if hasattr(venta, "folio") else venta.id
                messages.success(
                    request, 
                    f'✅ Venta {folio_text} realizada exitosamente.\n'
                    f'Total: ${total:.2f}\n'
                    f'{f"Descuento aplicado: {descuento_porcentaje}%" if cliente and cliente.porcentaje_descuento > 0 else ""}'
                )
                return redirect('venta_detalle', pk=venta.id)
        
        except Exception as e:
            messages.error(request, f'❌ Error al procesar la venta: {str(e)}')
            return redirect('venta_nueva')
    
    return redirect('venta_nueva')

@login_required
@admin_required
def limpiar_carrito(request):
    """Limpiar el carrito de compras"""
    if 'carrito' in request.session:
        del request.session['carrito']
    if 'cliente_id' in request.session:
        del request.session['cliente_id']
    
    messages.info(request, 'Carrito limpiado exitosamente')
    return redirect('venta_nueva')

@login_required
def lista_ventas(request):
    """Lista de todas las ventas"""
    sucursal = request.user.sucursal
    query = request.GET.get('q', '')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    estado = request.GET.get('estado', '')
    cliente_id = request.GET.get('cliente_id', '')
    
    # Filtrar por sucursal si no es superadmin
    if sucursal:
        ventas = Venta.objects.filter(sucursal=sucursal)
    else:
        # Superadmin ve todas las ventas
        ventas = Venta.objects.all()
    
    # Aplicar filtros
    if query:
        ventas = ventas.filter(
            Q(folio__icontains=query) if hasattr(Venta, 'folio') else Q(id__icontains=query) |
            Q(cliente__nombre__icontains=query) |
            Q(cliente__apellido__icontains=query) |
            Q(cliente__codigo__icontains=query) |
            Q(usuario__username__icontains=query)
        )
    
    if estado:
        ventas = ventas.filter(estado=estado)
    
    if cliente_id:
        ventas = ventas.filter(cliente_id=cliente_id)
    
    if fecha_inicio:
        ventas = ventas.filter(fecha__date__gte=fecha_inicio)
    
    if fecha_fin:
        ventas = ventas.filter(fecha__date__lte=fecha_fin)
    
    # Ordenar
    ventas = ventas.order_by('-fecha')
    
    # Estadísticas
    total_ventas = ventas.count()
    ventas_completadas = ventas.filter(estado='completada').count()
    ventas_canceladas = ventas.filter(estado='cancelada').count()
    
    total_hoy = ventas.filter(
        fecha__date=timezone.now().date(),
        estado='completada'
    ).aggregate(
        total=Sum('total')
    )['total'] or 0
    
    total_mes = ventas.filter(
        fecha__month=timezone.now().month,
        fecha__year=timezone.now().year,
        estado='completada'
    ).aggregate(
        total=Sum('total')
    )['total'] or 0
    
    # Paginación
    paginator = Paginator(ventas, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Clientes para filtro
    clientes = Cliente.objects.filter(activo=True).order_by('nombre')[:50]
    
    context = {
        'ventas': page_obj,
        'query': query,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'estado': estado,
        'cliente_id': cliente_id,
        'clientes': clientes,
        'total_ventas': total_ventas,
        'ventas_completadas': ventas_completadas,
        'ventas_canceladas': ventas_canceladas,
        'total_hoy': total_hoy,
        'total_mes': total_mes,
    }
    return render(request, 'ventas/lista.html', context)

@login_required
def detalle_venta(request, pk):
    """Detalle de una venta específica"""
    venta = get_object_or_404(Venta, pk=pk)
    
    # Verificar permisos
    if not hasattr(request.user, 'rol'):
        # Usar lógica de funciones helper si no hay atributo rol
        if not usuario_es_admin(request.user) and venta.usuario != request.user:
            messages.error(request, "No tienes permiso para ver esta venta")
            return redirect('ventas_lista')
    elif request.user.rol == 'cajero' and venta.usuario != request.user:
        messages.error(request, "No tienes permiso para ver esta venta")
        return redirect('ventas_lista')
    
    if request.user.sucursal and request.user.sucursal != venta.sucursal:
        messages.error(request, "Esta venta no pertenece a tu sucursal")
        return redirect('ventas_lista')
    
    detalles = venta.detalles.all().select_related('producto__producto')
    
    # Calcular IVA
    iva_total = Decimal('0')
    if hasattr(DetalleVenta, 'iva_calculado'):
        iva_total = sum(detalle.iva_calculado for detalle in detalles if hasattr(detalle, 'iva_calculado'))
    subtotal_sin_iva = venta.subtotal - iva_total
    
    context = {
        'venta': venta,
        'detalles': detalles,
        'iva_total': iva_total,
        'subtotal_sin_iva': subtotal_sin_iva,
    }
    return render(request, 'ventas/detalle.html', context)

@login_required
@puede_eliminar_ventas
def cancelar_venta(request, pk):
    """Cancelar una venta"""
    venta = get_object_or_404(Venta, pk=pk)
    
    # Verificar permisos - SOLO admin puede cancelar ventas
    if not usuario_es_admin(request.user):
        messages.error(request, "No tienes permisos para cancelar ventas")
        return redirect('venta_detalle', pk=venta.pk)
    
    if venta.estado == 'cancelada':
        messages.warning(request, "Esta venta ya está cancelada")
        return redirect('venta_detalle', pk=venta.pk)
    
    if request.method == 'POST':
        motivo = request.POST.get('motivo', '')
        
        # Usar el método cancelar del modelo si existe
        if hasattr(venta, 'cancelar'):
            if venta.cancelar(request.user, motivo):
                messages.success(request, f'Venta cancelada exitosamente')
            else:
                messages.error(request, 'Error al cancelar la venta')
        else:
            # Implementación básica si no existe el método
            try:
                with transaction.atomic():
                    # Restaurar stock
                    for detalle in venta.detalles.all():
                        producto_sucursal = detalle.producto
                        producto_sucursal.stock += detalle.cantidad
                        producto_sucursal.save()
                    
                    # Marcar como cancelada
                    venta.estado = 'cancelada'
                    venta.save()
                    
                    messages.success(request, f'Venta cancelada exitosamente')
            except Exception as e:
                messages.error(request, f'Error al cancelar: {str(e)}')
        
        return redirect('venta_detalle', pk=venta.pk)
    
    return render(request, 'ventas/cancelar.html', {'venta': venta})

@login_required
@admin_required
def generar_ticket(request, pk):
    """Generar ticket de venta"""
    venta = get_object_or_404(Venta, pk=pk)
    
    # Verificar permisos
    if request.user.sucursal and request.user.sucursal != venta.sucursal:
        messages.error(request, "Esta venta no pertenece a tu sucursal")
        return redirect('ventas_lista')
    
    detalles = venta.detalles.all().select_related('producto__producto')
    
    # Calcular IVA
    iva_total = Decimal('0')
    if hasattr(DetalleVenta, 'iva_calculado'):
        iva_total = sum(detalle.iva_calculado for detalle in detalles if hasattr(detalle, 'iva_calculado'))
    
    context = {
        'venta': venta,
        'detalles': detalles,
        'iva_total': iva_total,
        'sucursal': venta.sucursal,
    }
    
    # Para impresión directa
    if request.GET.get('print') == '1':
        response = HttpResponse(content_type='application/pdf')
        folio_text = venta.folio if hasattr(venta, "folio") else venta.id
        response['Content-Disposition'] = f'attachment; filename="ticket-{folio_text}.pdf"'
        # Aquí puedes agregar generación de PDF si tienes una librería
        return response
    
    return render(request, 'ventas/ticket.html', context)

# =========== CORTES DE CAJA ===========
@login_required
@admin_required
def cortes_caja_lista(request):
    """Lista de cortes de caja"""
    sucursal = request.user.sucursal
    if not sucursal:
        messages.error(request, "No tienes una sucursal asignada")
        return redirect('dashboard')
    
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', '')
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    cortes = CorteCaja.objects.filter(sucursal=sucursal)
    
    if query:
        cortes = cortes.filter(
            Q(folio__icontains=query) |
            Q(usuario__username__icontains=query)
        )
    
    if estado:
        cortes = cortes.filter(estado=estado)
    
    if fecha_inicio:
        cortes = cortes.filter(fecha_inicio__date__gte=fecha_inicio)
    
    if fecha_fin:
        cortes = cortes.filter(fecha_inicio__date__lte=fecha_fin)
    
    cortes = cortes.order_by('-fecha_inicio')
    
    # Estadísticas
    cortes_abiertos = cortes.filter(estado='abierto').count()
    cortes_cerrados = cortes.filter(estado='cerrado').count()
    cortes_verificados = cortes.filter(estado='verificado').count()
    
    # Paginación
    paginator = Paginator(cortes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'cortes': page_obj,
        'query': query,
        'estado': estado,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'cortes_abiertos': cortes_abiertos,
        'cortes_cerrados': cortes_cerrados,
        'cortes_verificados': cortes_verificados,
    }
    return render(request, 'ventas/cortes/lista.html', context)

@login_required
@admin_required
def corte_caja_nuevo(request):
    """Abrir nuevo corte de caja"""
    sucursal = request.user.sucursal
    if not sucursal:
        messages.error(request, "No tienes una sucursal asignada")
        return redirect('dashboard')
    
    # Verificar si ya hay un corte abierto
    corte_abierto = CorteCaja.objects.filter(
        sucursal=sucursal,
        estado='abierto',
        usuario=request.user
    ).first()
    
    if corte_abierto:
        messages.info(request, f'Ya tienes un corte abierto: {corte_abierto.folio if hasattr(corte_abierto, "folio") else corte_abierto.id}')
        return redirect('corte_caja_detalle', pk=corte_abierto.pk)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # Crear nuevo corte
                corte = CorteCaja.objects.create(
                    sucursal=sucursal,
                    usuario=request.user,
                    fecha_inicio=timezone.now(),
                    estado='abierto'
                )
                
                folio_text = corte.folio if hasattr(corte, "folio") else corte.id
                messages.success(request, f'Corte {folio_text} abierto exitosamente')
                return redirect('corte_caja_detalle', pk=corte.pk)
        
        except Exception as e:
            messages.error(request, f'Error al abrir corte: {str(e)}')
    
    return render(request, 'ventas/cortes/nuevo.html')

@login_required
@admin_required
def corte_caja_detalle(request, pk):
    """Detalle de corte de caja"""
    corte = get_object_or_404(CorteCaja, pk=pk)
    
    # Verificar permisos
    if request.user.sucursal and request.user.sucursal != corte.sucursal:
        messages.error(request, "Este corte no pertenece a tu sucursal")
        return redirect('cortes_caja_lista')
    
    # Obtener ventas del corte
    ventas = []
    if hasattr(corte, 'ventas_incluidas'):
        ventas = corte.ventas_incluidas.all().order_by('-fecha')
    else:
        # Alternativa: buscar ventas en el rango del corte
        ventas = Venta.objects.filter(
            sucursal=corte.sucursal,
            usuario=corte.usuario,
            fecha__gte=corte.fecha_inicio,
            fecha__lte=corte.fecha_fin if corte.fecha_fin else timezone.now()
        ).order_by('-fecha')
    
    # Calcular estadísticas
    ventas_por_forma_pago = []
    if ventas:
        ventas_por_forma_pago = ventas.values('forma_pago').annotate(
            total=Sum('total'),
            count=Count('id')
        )
    
    context = {
        'corte': corte,
        'ventas': ventas,
        'ventas_por_forma_pago': ventas_por_forma_pago,
        'puede_cerrar': corte.estado == 'abierto' and request.user == corte.usuario,
        'puede_verificar': corte.estado == 'cerrado' and usuario_es_admin(request.user),
    }
    return render(request, 'ventas/cortes/detalle.html', context)

@login_required
@admin_required
def corte_caja_cerrar(request, pk):
    """Cerrar corte de caja"""
    corte = get_object_or_404(CorteCaja, pk=pk)
    
    # Verificar permisos
    if corte.estado != 'abierto':
        messages.error(request, "Este corte ya está cerrado")
        return redirect('corte_caja_detalle', pk=corte.pk)
    
    if request.user != corte.usuario:
        messages.error(request, "Solo el usuario que abrió el corte puede cerrarlo")
        return redirect('corte_caja_detalle', pk=corte.pk)
    
    if request.method == 'POST':
        try:
            efectivo_real = Decimal(request.POST.get('efectivo_real', 0))
            observaciones = request.POST.get('observaciones', '')
            
            if hasattr(corte, 'cerrar_corte'):
                if corte.cerrar_corte(request.user, efectivo_real, observaciones):
                    folio_text = corte.folio if hasattr(corte, "folio") else corte.id
                    messages.success(request, f'Corte {folio_text} cerrado exitosamente')
                else:
                    messages.error(request, 'Error al cerrar el corte')
            else:
                # Implementación manual
                corte.fecha_fin = timezone.now()
                corte.efectivo_real = efectivo_real
                corte.observaciones = observaciones
                corte.estado = 'cerrado'
                corte.save()
                folio_text = corte.folio if hasattr(corte, "folio") else corte.id
                messages.success(request, f'Corte {folio_text} cerrado exitosamente')
            
            return redirect('corte_caja_detalle', pk=corte.pk)
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    # Calcular total esperado en efectivo
    ventas_efectivo = []
    if hasattr(corte, 'ventas_incluidas'):
        ventas_efectivo = corte.ventas_incluidas.filter(
            forma_pago='efectivo',
            estado='completada'
        )
    else:
        ventas_efectivo = Venta.objects.filter(
            sucursal=corte.sucursal,
            usuario=corte.usuario,
            fecha__gte=corte.fecha_inicio,
            forma_pago='efectivo',
            estado='completada'
        )
    
    total_efectivo_esperado = sum(venta.total for venta in ventas_efectivo)
    
    context = {
        'corte': corte,
        'total_efectivo_esperado': total_efectivo_esperado,
    }
    return render(request, 'ventas/cortes/cerrar.html', context)

@login_required
@admin_required
def corte_caja_verificar(request, pk):
    """Verificar corte de caja (admin/superadmin)"""
    corte = get_object_or_404(CorteCaja, pk=pk)
    
    # Verificar permisos
    if corte.estado != 'cerrado':
        messages.error(request, "Este corte no está cerrado")
        return redirect('corte_caja_detalle', pk=corte.pk)
    
    if not usuario_es_admin(request.user):
        messages.error(request, "No tienes permiso para verificar cortes")
        return redirect('corte_caja_detalle', pk=corte.pk)
    
    if request.method == 'POST':
        try:
            corte.estado = 'verificado'
            if hasattr(corte, 'verificado_por'):
                corte.verificado_por = request.user
            corte.save()
            
            folio_text = corte.folio if hasattr(corte, "folio") else corte.id
            messages.success(request, f'Corte {folio_text} verificado exitosamente')
            return redirect('corte_caja_detalle', pk=corte.pk)
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    return render(request, 'ventas/cortes/verificar.html', {'corte': corte})

@login_required
@admin_required
def reporte_ventas(request):
    """Reporte de ventas"""
    sucursal = request.user.sucursal
    if not sucursal:
        messages.error(request, "No tienes una sucursal asignada")
        return redirect('dashboard')
    
    # Parámetros del reporte
    fecha_inicio = request.GET.get('fecha_inicio', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    fecha_fin = request.GET.get('fecha_fin', timezone.now().strftime('%Y-%m-%d'))
    grupo_por = request.GET.get('grupo_por', 'dia')
    tipo_cliente = request.GET.get('tipo_cliente', '')
    
    # Filtrar ventas
    ventas = Venta.objects.filter(
        sucursal=sucursal,
        fecha__date__gte=fecha_inicio,
        fecha__date__lte=fecha_fin,
        estado='completada'
    )
    
    if tipo_cliente:
        if tipo_cliente == 'sin_cliente':
            ventas = ventas.filter(cliente__isnull=True)
        else:
            ventas = ventas.filter(cliente__tipo_cliente=tipo_cliente)
    
    # Agrupar datos según el parámetro
    datos = []
    if grupo_por == 'dia':
        # Agrupar por día
        ventas_por_dia = ventas.extra(
            select={'fecha_str': "DATE(fecha)"}
        ).values('fecha_str').annotate(
            total_ventas=Sum('total'),
            total_ventas_count=Count('id'),
            total_descuentos=Sum('descuento_total'),
            promedio_descuento=Avg('descuento_porcentaje')
        ).order_by('fecha_str')
        
        for item in ventas_por_dia:
            datos.append({
                'periodo': item['fecha_str'],
                'total_ventas': item['total_ventas'] or 0,
                'ventas_count': item['total_ventas_count'],
                'total_descuentos': item['total_descuentos'] or 0,
                'promedio_descuento': item['promedio_descuento'] or 0,
            })
    
    elif grupo_por == 'mes':
        # Agrupar por mes
        ventas_por_mes = ventas.extra(
            select={'mes': "EXTRACT(MONTH FROM fecha)", 'ano': "EXTRACT(YEAR FROM fecha)"}
        ).values('ano', 'mes').annotate(
            total_ventas=Sum('total'),
            total_ventas_count=Count('id'),
            total_descuentos=Sum('descuento_total')
        ).order_by('ano', 'mes')
        
        for item in ventas_por_mes:
            datos.append({
                'periodo': f"{int(item['mes'])}/{int(item['ano'])}",
                'total_ventas': item['total_ventas'] or 0,
                'ventas_count': item['total_ventas_count'],
                'total_descuentos': item['total_descuentos'] or 0,
            })
    
    # Estadísticas generales
    total_general = ventas.aggregate(
        total=Sum('total'),
        count=Count('id'),
        descuentos=Sum('descuento_total'),
        promedio_venta=Avg('total')
    )
    
    # Ventas por tipo de cliente
    ventas_por_tipo_cliente = ventas.values(
        'cliente__tipo_cliente'
    ).annotate(
        total=Sum('total'),
        count=Count('id')
    )
    
    # Productos más vendidos
    productos_mas_vendidos = DetalleVenta.objects.filter(
        venta__in=ventas
    ).values(
        'producto__producto__nombre',
        'producto__producto__codigo'
    ).annotate(
        cantidad_total=Sum('cantidad'),
        total_ventas=Sum('subtotal')
    ).order_by('-cantidad_total')[:10]
    
    context = {
        'datos': datos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'grupo_por': grupo_por,
        'tipo_cliente': tipo_cliente,
        'total_general': total_general,
        'ventas_por_tipo_cliente': ventas_por_tipo_cliente,
        'productos_mas_vendidos': productos_mas_vendidos,
    }
    return render(request, 'ventas/reportes/ventas.html', context)

# =========== AJAX HELPERS ===========
@login_required
@csrf_exempt
def get_producto_info(request):
    """Obtener información de producto para AJAX"""
    if request.method == 'GET':
        producto_id = request.GET.get('producto_id')
        
        try:
            producto = ProductoSucursal.objects.get(
                id=producto_id,
                sucursal=request.user.sucursal,
                activo=True
            )
            
            return JsonResponse({
                'success': True,
                'producto': {
                    'id': producto.id,
                    'nombre': producto.producto.nombre,
                    'codigo': producto.producto.codigo,
                    'precio': float(producto.precio_venta),
                    'stock': float(producto.stock),
                    'stock_minimo': float(producto.stock_minimo),
                    'categoria': producto.producto.categoria.nombre if producto.producto.categoria else '',
                    'tiene_iva': producto.producto.tiene_iva,
                }
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
def get_ventas_dia(request):
    """Obtener ventas del día actual para dashboard"""
    sucursal = request.user.sucursal
    if not sucursal:
        return JsonResponse({'success': False, 'error': 'Sin sucursal'})
    
    hoy = timezone.now().date()
    
    ventas_hoy = Venta.objects.filter(
        sucursal=sucursal,
        fecha__date=hoy,
        estado='completada'
    )
    
    total_hoy = ventas_hoy.aggregate(total=Sum('total'))['total'] or 0
    ventas_count = ventas_hoy.count()
    descuentos_hoy = ventas_hoy.aggregate(total=Sum('descuento_total'))['total'] or 0
    
    # Últimas ventas
    ultimas_ventas = ventas_hoy.order_by('-fecha')[:5].values(
        'id', 'total', 'fecha', 'cliente__nombre', 'cliente__apellido'
    )
    
    # Agregar folio si existe
    ventas_list = []
    for venta in ultimas_ventas:
        venta_data = dict(venta)
        # Intentar obtener el folio
        if 'folio' in venta_data:
            venta_data['folio'] = venta_data['folio']
        else:
            venta_data['folio'] = f"V-{venta_data['id']}"
        ventas_list.append(venta_data)
    
    return JsonResponse({
        'success': True,
        'total_hoy': float(total_hoy),
        'ventas_count': ventas_count,
        'descuentos_hoy': float(descuentos_hoy),
        'ultimas_ventas': ventas_list,
    })