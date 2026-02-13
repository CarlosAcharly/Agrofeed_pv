from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from decimal import Decimal
import json
from datetime import datetime, timedelta

from ventas.models import Venta, DetalleVenta, CorteCaja
from catalogos.models import ProductoSucursal, Cliente, MovimientoInventario
from sucursales.models import Sucursal
from usuarios.decorators import cajero_required

@login_required
@cajero_required
def cajero_dashboard(request):
    """Dashboard principal para cajero"""
    sucursal = request.user.sucursal
    hoy = timezone.now().date()
    
    # Estadísticas del día
    ventas_hoy = Venta.objects.filter(
        sucursal=sucursal,
        fecha__date=hoy,
        estado='completada'
    )
    
    total_hoy = sum(venta.total for venta in ventas_hoy) if ventas_hoy else 0
    cantidad_ventas_hoy = ventas_hoy.count()
    
    # Productos con bajo stock
    productos_bajo_stock = ProductoSucursal.objects.filter(
        sucursal=sucursal,
        stock__lte=models.F('stock_minimo'),
        activo=True
    ).count()
    
    # Corte de caja activo
    corte_activo = CorteCaja.objects.filter(
        sucursal=sucursal,
        estado='abierto',
        usuario=request.user
    ).first()
    
    # Últimas ventas
    ultimas_ventas = ventas_hoy.order_by('-fecha')[:5]
    
    context = {
        'sucursal': sucursal,
        'total_hoy': total_hoy,
        'cantidad_ventas_hoy': cantidad_ventas_hoy,
        'productos_bajo_stock': productos_bajo_stock,
        'corte_activo': corte_activo,
        'ultimas_ventas': ultimas_ventas,
    }
    
    return render(request, 'cajero/dashboard.html', context)

@login_required
@cajero_required
def cajero_nueva_venta(request):
    """Interfaz de nueva venta estilo ticket"""
    sucursal = request.user.sucursal
    
    # Obtener productos de la sucursal
    productos = ProductoSucursal.objects.filter(
        sucursal=sucursal,
        activo=True,
        producto__activo=True
    ).select_related('producto', 'producto__categoria').order_by('producto__nombre')
    
    # Obtener carrito de sesión
    carrito = request.session.get('carrito_cajero', [])
    
    # Obtener cliente seleccionado
    cliente_id = request.session.get('cliente_id_cajero')
    cliente = None
    if cliente_id:
        try:
            cliente = Cliente.objects.get(id=cliente_id, activo=True)
        except Cliente.DoesNotExist:
            cliente = None
    
    # Calcular totales
    subtotal = sum(Decimal(str(item.get('subtotal', 0))) for item in carrito)
    descuento_total = Decimal('0')
    descuento_porcentaje = Decimal('0')
    
    if cliente and cliente.porcentaje_descuento > 0:
        descuento_porcentaje = cliente.porcentaje_descuento
        descuento_total = subtotal * (descuento_porcentaje / Decimal('100'))
    
    total = subtotal - descuento_total
    
    # Categorías para filtro
    categorias = productos.values_list('producto__categoria__nombre', flat=True).distinct()
    
    context = {
        'productos': productos,
        'categorias': categorias,
        'carrito': carrito,
        'cliente': cliente,
        'subtotal': subtotal,
        'descuento_total': descuento_total,
        'descuento_porcentaje': descuento_porcentaje,
        'total': total,
        'sucursal': sucursal,
    }
    
    return render(request, 'cajero/nueva_venta.html', context)

@login_required
@cajero_required
@csrf_exempt
def ajax_agregar_carrito(request):
    """Agregar producto al carrito (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            producto_id = data.get('producto_id')
            cantidad = Decimal(str(data.get('cantidad', 1)))
            
            producto_sucursal = ProductoSucursal.objects.get(
                id=producto_id,
                sucursal=request.user.sucursal,
                activo=True
            )
            
            if cantidad > producto_sucursal.stock:
                return JsonResponse({
                    'success': False,
                    'error': f'Stock insuficiente. Disponible: {producto_sucursal.stock}'
                })
            
            carrito = request.session.get('carrito_cajero', [])
            
            # Buscar si ya existe en el carrito
            item_encontrado = False
            for item in carrito:
                if item['id'] == producto_sucursal.id:
                    item['cantidad'] = float(Decimal(str(item['cantidad'])) + cantidad)
                    item['subtotal'] = float(Decimal(str(item['precio'])) * Decimal(str(item['cantidad'])))
                    item_encontrado = True
                    break
            
            # Si no existe, agregarlo
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
            
            request.session['carrito_cajero'] = carrito
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'carrito': carrito,
                'carrito_count': len(carrito),
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
@cajero_required
@csrf_exempt
def ajax_remover_carrito(request):
    """Remover producto del carrito (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_id = int(data.get('item_id'))
            
            carrito = request.session.get('carrito_cajero', [])
            carrito = [item for item in carrito if item['id'] != item_id]
            
            request.session['carrito_cajero'] = carrito
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'carrito': carrito,
                'carrito_count': len(carrito),
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
@cajero_required
@csrf_exempt
def ajax_seleccionar_cliente(request):
    """Seleccionar cliente para la venta (AJAX)"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            cliente_id = data.get('cliente_id')
            
            if cliente_id:
                cliente = Cliente.objects.get(id=cliente_id, activo=True)
                request.session['cliente_id_cajero'] = cliente.id
                
                return JsonResponse({
                    'success': True,
                    'cliente': {
                        'id': cliente.id,
                        'nombre': cliente.nombre_completo,
                        'codigo': cliente.codigo,
                        'telefono': cliente.telefono,
                        'descuento': float(cliente.porcentaje_descuento)
                    }
                })
            else:
                # Remover cliente
                if 'cliente_id_cajero' in request.session:
                    del request.session['cliente_id_cajero']
                
                return JsonResponse({
                    'success': True,
                    'cliente': None
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
@cajero_required
@csrf_exempt
def cajero_procesar_venta(request):
    """Procesar la venta del cajero"""
    if request.method == 'POST':
        carrito = request.session.get('carrito_cajero', [])
        
        if not carrito:
            return JsonResponse({
                'success': False,
                'error': 'El carrito está vacío'
            })
        
        sucursal = request.user.sucursal
        
        try:
            with transaction.atomic():
                # Obtener cliente si existe
                cliente_id = request.session.get('cliente_id_cajero')
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
                data = json.loads(request.body)
                forma_pago = data.get('forma_pago', 'efectivo')
                efectivo_recibido = Decimal(str(data.get('efectivo_recibido', 0)))
                observaciones = data.get('observaciones', '')
                
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
                    cambio=max(efectivo_recibido - total, Decimal('0')),
                    observaciones=observaciones,
                    creado_por=request.user
                )
                
                # Crear detalles y actualizar stock
                for item in carrito:
                    producto_sucursal = ProductoSucursal.objects.get(
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
                    
                    # Calcular subtotal
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
                        motivo=f'Venta #{venta.folio}',
                        usuario=request.user,
                        referencia=f'VENTA-{venta.folio}'
                    )
                    
                    # Crear detalle de venta
                    DetalleVenta.objects.create(
                        venta=venta,
                        producto=producto_sucursal,
                        cantidad=cantidad,
                        precio_unitario=precio_unitario,
                        precio_final=precio_final,
                        descuento_unitario=descuento_unitario,
                        subtotal=subtotal_item,
                        tiene_iva=item.get('tiene_iva', True),
                        descuento_porcentaje=descuento_porcentaje
                    )
                
                # Actualizar corte de caja actual
                corte_actual = CorteCaja.objects.filter(
                    sucursal=sucursal,
                    estado='abierto',
                    usuario=request.user
                ).first()
                
                if corte_actual:
                    corte_actual.ventas_incluidas.add(venta)
                    corte_actual.calcular_totales()
                
                # Limpiar sesión
                if 'carrito_cajero' in request.session:
                    del request.session['carrito_cajero']
                if 'cliente_id_cajero' in request.session:
                    del request.session['cliente_id_cajero']
                
                return JsonResponse({
                    'success': True,
                    'venta_id': venta.id,
                    'folio': venta.folio,
                    'total': float(total),
                    'cambio': float(max(efectivo_recibido - total, Decimal('0')))
                })
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})

@login_required
@cajero_required
def cajero_limpiar_carrito(request):
    """Limpiar carrito de compras"""
    if 'carrito_cajero' in request.session:
        del request.session['carrito_cajero']
    if 'cliente_id_cajero' in request.session:
        del request.session['cliente_id_cajero']
    
    return JsonResponse({'success': True})

@login_required
@cajero_required
def cajero_productos(request):
    """Lista de productos para cajero"""
    sucursal = request.user.sucursal
    query = request.GET.get('q', '')
    categoria = request.GET.get('categoria', '')
    
    productos = ProductoSucursal.objects.filter(
        sucursal=sucursal,
        activo=True,
        producto__activo=True
    ).select_related('producto', 'producto__categoria')
    
    if query:
        productos = productos.filter(
            producto__nombre__icontains=query
        )
    
    if categoria:
        productos = productos.filter(producto__categoria__nombre=categoria)
    
    # Categorías para filtro
    categorias = productos.values_list('producto__categoria__nombre', flat=True).distinct()
    
    # Paginación
    paginator = Paginator(productos, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'productos': page_obj,
        'query': query,
        'categoria': categoria,
        'categorias': categorias,
    }
    
    return render(request, 'cajero/productos.html', context)

@login_required
@cajero_required
def cajero_clientes(request):
    """Lista de clientes para cajero"""
    query = request.GET.get('q', '')
    
    clientes = Cliente.objects.filter(activo=True)
    
    if query:
        clientes = clientes.filter(
            nombre__icontains=query
        )
    
    # Paginación
    paginator = Paginator(clientes, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'clientes': page_obj,
        'query': query,
    }
    
    return render(request, 'cajero/clientes.html', context)

@login_required
@cajero_required
def cajero_nuevo_cliente(request):
    """Crear nuevo cliente desde cajero"""
    if request.method == 'POST':
        # Aquí implementar la creación del cliente
        # Los cajeros solo pueden crear clientes normales
        pass
    
    return render(request, 'cajero/nuevo_cliente.html')

@login_required
@cajero_required
def cajero_cortes(request):
    """Lista de cortes de caja del cajero"""
    sucursal = request.user.sucursal
    
    cortes = CorteCaja.objects.filter(
        sucursal=sucursal,
        usuario=request.user
    ).order_by('-fecha_inicio')
    
    # Corte activo
    corte_activo = cortes.filter(estado='abierto').first()
    
    context = {
        'cortes': cortes,
        'corte_activo': corte_activo,
    }
    
    return render(request, 'cajero/cortes.html', context)

@login_required
@cajero_required
def cajero_apertura_caja(request):
    """Apertura de caja"""
    sucursal = request.user.sucursal
    
    # Verificar si ya hay un corte abierto
    corte_activo = CorteCaja.objects.filter(
        sucursal=sucursal,
        estado='abierto',
        usuario=request.user
    ).first()
    
    if corte_activo:
        messages.info(request, f'Ya tienes un corte abierto: {corte_activo.folio}')
        return redirect('cajero_cortes')
    
    if request.method == 'POST':
        try:
            # Crear nuevo corte
            corte = CorteCaja.objects.create(
                sucursal=sucursal,
                usuario=request.user,
                fecha_inicio=timezone.now(),
                estado='abierto'
            )
            
            messages.success(request, f'Corte {corte.folio} abierto exitosamente')
            return redirect('cajero_cortes')
        
        except Exception as e:
            messages.error(request, f'Error al abrir corte: {str(e)}')
    
    return render(request, 'cajero/apertura_caja.html')

@login_required
@cajero_required
def cajero_cierre_caja(request):
    """Cierre de caja"""
    sucursal = request.user.sucursal
    
    # Buscar corte activo
    corte_activo = CorteCaja.objects.filter(
        sucursal=sucursal,
        estado='abierto',
        usuario=request.user
    ).first()
    
    if not corte_activo:
        messages.error(request, "No hay caja abierta para cerrar")
        return redirect('cajero_cortes')
    
    if request.method == 'POST':
        try:
            efectivo_real = Decimal(request.POST.get('efectivo_real', 0))
            observaciones = request.POST.get('observaciones', '')
            
            # Cerrar corte
            if corte_activo.cerrar_corte(request.user, efectivo_real, observaciones):
                messages.success(request, f'Corte {corte_activo.folio} cerrado exitosamente')
            else:
                messages.error(request, 'Error al cerrar el corte')
            
            return redirect('cajero_cortes')
        
        except Exception as e:
            messages.error(request, f'Error: {str(e)}')
    
    # Calcular ventas del corte
    ventas_corte = corte_activo.ventas_incluidas.filter(estado='completada')
    total_efectivo_esperado = sum(
        venta.total for venta in ventas_corte.filter(forma_pago='efectivo')
    )
    
    context = {
        'corte': corte_activo,
        'total_efectivo_esperado': total_efectivo_esperado,
    }
    
    return render(request, 'cajero/cierre_caja.html', context)

@login_required
@cajero_required
def cajero_lista_ventas(request):
    """Lista de ventas realizadas por el cajero"""
    sucursal = request.user.sucursal
    
    ventas = Venta.objects.filter(
        sucursal=sucursal,
        usuario=request.user
    ).order_by('-fecha')
    
    # Filtros
    fecha = request.GET.get('fecha', '')
    if fecha:
        ventas = ventas.filter(fecha__date=fecha)
    
    # Paginación
    paginator = Paginator(ventas, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'ventas': page_obj,
        'fecha': fecha,
    }
    
    return render(request, 'cajero/lista_ventas.html', context)

@login_required
@cajero_required
def cajero_detalle_venta(request, pk):
    """Detalle de una venta específica"""
    venta = get_object_or_404(Venta, pk=pk)
    
    # Verificar que la venta sea del cajero
    if venta.usuario != request.user:
        messages.error(request, "No tienes permiso para ver esta venta")
        return redirect('cajero_lista_ventas')
    
    detalles = venta.detalles.all().select_related('producto__producto')
    
    context = {
        'venta': venta,
        'detalles': detalles,
    }
    
    return render(request, 'cajero/detalle_venta.html', context)

@login_required
@cajero_required
def cajero_generar_ticket(request, pk):
    """Generar ticket/recibo de venta"""
    venta = get_object_or_404(Venta, pk=pk)
    
    # Verificar que la venta sea del cajero
    if venta.usuario != request.user:
        messages.error(request, "No tienes permiso para ver esta venta")
        return redirect('cajero_lista_ventas')
    
    detalles = venta.detalles.all().select_related('producto__producto')
    
    context = {
        'venta': venta,
        'detalles': detalles,
        'sucursal': venta.sucursal,
    }
    
    return render(request, 'cajero/ticket.html', context)

@login_required
@cajero_required
def cajero_buscar_productos(request):
    """Búsqueda rápida de productos (AJAX)"""
    query = request.GET.get('q', '')
    
    productos = ProductoSucursal.objects.filter(
        sucursal=request.user.sucursal,
        producto__nombre__icontains=query,
        activo=True,
        producto__activo=True
    ).select_related('producto')[:10]
    
    results = []
    for producto in productos:
        results.append({
            'id': producto.id,
            'nombre': producto.producto.nombre,
            'codigo': producto.producto.codigo,
            'precio': float(producto.precio_venta),
            'stock': float(producto.stock),
            'categoria': producto.producto.categoria.nombre if producto.producto.categoria else '',
        })
    
    return JsonResponse({'productos': results})

@login_required
@cajero_required
def cajero_buscar_clientes(request):
    """Búsqueda rápida de clientes (AJAX)"""
    query = request.GET.get('q', '')
    
    clientes = Cliente.objects.filter(
        Q(nombre__icontains=query) | Q(codigo__icontains=query),
        activo=True
    )[:10]
    
    results = []
    for cliente in clientes:
        results.append({
            'id': cliente.id,
            'nombre': cliente.nombre_completo,
            'codigo': cliente.codigo,
            'telefono': cliente.telefono,
            'descuento': float(cliente.porcentaje_descuento),
        })
    
    return JsonResponse({'clientes': results})

@login_required
@cajero_required
def cajero_reportes_ventas(request):
    """Reporte de ventas del día"""
    sucursal = request.user.sucursal
    hoy = timezone.now().date()
    
    ventas = Venta.objects.filter(
        sucursal=sucursal,
        fecha__date=hoy,
        usuario=request.user,
        estado='completada'
    ).order_by('-fecha')
    
    # Estadísticas
    total_ventas = sum(venta.total for venta in ventas)
    cantidad_ventas = ventas.count()
    
    # Ventas por forma de pago
    ventas_efectivo = ventas.filter(forma_pago='efectivo')
    total_efectivo = sum(venta.total for venta in ventas_efectivo)
    
    ventas_tarjeta = ventas.filter(forma_pago='tarjeta')
    total_tarjeta = sum(venta.total for venta in ventas_tarjeta)
    
    ventas_transferencia = ventas.filter(forma_pago='transferencia')
    total_transferencia = sum(venta.total for venta in ventas_transferencia)
    
    context = {
        'ventas': ventas,
        'total_ventas': total_ventas,
        'cantidad_ventas': cantidad_ventas,
        'total_efectivo': total_efectivo,
        'total_tarjeta': total_tarjeta,
        'total_transferencia': total_transferencia,
        'fecha': hoy,
    }
    
    return render(request, 'cajero/reportes_ventas.html', context)