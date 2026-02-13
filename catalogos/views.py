from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import transaction
from django.db.models import Q, Sum, Count, F
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.http import require_POST

from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
import json

from caja import models
from dashboard import models
from ventas import models
from catalogos import models

from .models import (
    Proveedor, Categoria, UnidadMedida,
    Producto, ProductoSucursal, MovimientoInventario,
    Cliente, HistorialDescuento
    
)

from .forms import (
    ProveedorForm, CategoriaForm, UnidadMedidaForm,
    ProductoForm, ProductoSucursalForm,
    ClienteForm, ClienteFilterForm
)

from sucursales.models import Sucursal
from usuarios.decorators import admin_required, puede_editar_precios, superadmin_required

# =========== PROVEEDORES ===========
@login_required
@admin_required
def proveedores_lista(request):
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', 'todos')
    
    proveedores = Proveedor.objects.all()
    
    if query:
        proveedores = proveedores.filter(
            Q(nombre__icontains=query) |
            Q(email__icontains=query) |
            Q(telefono__icontains=query) |
            Q(rfc__icontains=query)
        )
    
    if estado == 'activos':
        proveedores = proveedores.filter(activo=True)
    elif estado == 'inactivos':
        proveedores = proveedores.filter(activo=False)
    
    # Paginación
    paginator = Paginator(proveedores, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'proveedores': page_obj,
        'query': query,
        'estado': estado,
        'total_count': proveedores.count(),
        'activos_count': Proveedor.objects.filter(activo=True).count(),
        'inactivos_count': Proveedor.objects.filter(activo=False).count(),
    }
    return render(request, 'catalogos/proveedores/lista.html', context)


@login_required
@admin_required
def proveedores_crear(request):
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            proveedor = form.save()
            messages.success(request, 'Proveedor creado exitosamente')
            return redirect('proveedores_lista')
    else:
        form = ProveedorForm()
    
    return render(request, 'catalogos/proveedores/form.html', {
        'form': form,
        'titulo': 'Nuevo Proveedor',
        'accion': 'Crear'
    })


@login_required
@admin_required
def proveedores_editar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            proveedor = form.save()
            messages.success(request, 'Proveedor actualizado exitosamente')
            return redirect('proveedores_lista')
    else:
        form = ProveedorForm(instance=proveedor)
    
    return render(request, 'catalogos/proveedores/form.html', {
        'form': form,
        'titulo': 'Editar Proveedor',
        'accion': 'Actualizar',
        'proveedor': proveedor
    })


@login_required
@admin_required
def proveedores_eliminar(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    
    if request.method == 'POST':
        # Verificar si hay productos asociados
        productos_count = Producto.objects.filter(proveedor=proveedor).count()
        
        if productos_count > 0:
            messages.error(request, f'No se puede eliminar el proveedor. Tiene {productos_count} productos asociados.')
            return redirect('proveedores_lista')
        
        proveedor.delete()
        messages.success(request, 'Proveedor eliminado exitosamente')
        return redirect('proveedores_lista')
    
    return render(request, 'catalogos/proveedores/eliminar.html', {
        'proveedor': proveedor
    })


@login_required
@admin_required
def proveedores_toggle(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    proveedor.activo = not proveedor.activo
    proveedor.save()
    
    estado = "activado" if proveedor.activo else "desactivado"
    messages.success(request, f'Proveedor {estado} exitosamente')
    return redirect('proveedores_lista')


@login_required
@admin_required
def proveedores_detalle(request, pk):
    proveedor = get_object_or_404(Proveedor, pk=pk)
    productos = Producto.objects.filter(proveedor=proveedor)
    
    return render(request, 'catalogos/proveedores/detalle.html', {
        'proveedor': proveedor,
        'productos': productos,
        'productos_count': productos.count()
    })


# =========== CATEGORÍAS ===========
@login_required
@admin_required
def categorias_lista(request):
    categorias = Categoria.objects.filter(padre__isnull=True)
    
    return render(request, 'catalogos/categorias/lista.html', {
        'categorias': categorias
    })


@login_required
@admin_required
def categorias_crear(request):
    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, 'Categoría creada exitosamente')
            return redirect('categorias_lista')
    else:
        form = CategoriaForm()
    
    return render(request, 'catalogos/categorias/form.html', {
        'form': form,
        'titulo': 'Nueva Categoría',
        'accion': 'Crear'
    })


@login_required
@admin_required
def categorias_editar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            categoria = form.save()
            messages.success(request, 'Categoría actualizada exitosamente')
            return redirect('categorias_lista')
    else:
        form = CategoriaForm(instance=categoria)
    
    return render(request, 'catalogos/categorias/form.html', {
        'form': form,
        'titulo': 'Editar Categoría',
        'accion': 'Actualizar',
        'categoria': categoria
    })


@login_required
@admin_required
def categorias_eliminar(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    
    if request.method == 'POST':
        # Verificar si tiene subcategorías
        subcategorias_count = categoria.subcategorias.count()
        productos_count = Producto.objects.filter(categoria=categoria).count()
        
        if subcategorias_count > 0 or productos_count > 0:
            messages.error(
                request, 
                f'No se puede eliminar la categoría. '
                f'Tiene {subcategorias_count} subcategorías y {productos_count} productos asociados.'
            )
            return redirect('categorias_lista')
        
        categoria.delete()
        messages.success(request, 'Categoría eliminada exitosamente')
        return redirect('categorias_lista')
    
    return render(request, 'catalogos/categorias/eliminar.html', {
        'categoria': categoria
    })


@login_required
@admin_required
def categorias_toggle(request, pk):
    categoria = get_object_or_404(Categoria, pk=pk)
    categoria.activa = not categoria.activa
    categoria.save()
    
    estado = "activada" if categoria.activa else "desactivada"
    messages.success(request, f'Categoría {estado} exitosamente')
    return redirect('categorias_lista')


# =========== UNIDADES DE MEDIDA ===========
@login_required
@admin_required
def unidades_lista(request):
    unidades = UnidadMedida.objects.all()
    
    return render(request, 'catalogos/unidades/lista.html', {
        'unidades': unidades
    })


@login_required
@admin_required
def unidades_crear(request):
    if request.method == 'POST':
        form = UnidadMedidaForm(request.POST)
        if form.is_valid():
            unidad = form.save()
            messages.success(request, 'Unidad de medida creada exitosamente')
            return redirect('unidades_lista')
    else:
        form = UnidadMedidaForm()
    
    return render(request, 'catalogos/unidades/form.html', {
        'form': form,
        'titulo': 'Nueva Unidad de Medida',
        'accion': 'Crear'
    })


@login_required
@admin_required
def unidades_editar(request, pk):
    unidad = get_object_or_404(UnidadMedida, pk=pk)
    
    if request.method == 'POST':
        form = UnidadMedidaForm(request.POST, instance=unidad)
        if form.is_valid():
            unidad = form.save()
            messages.success(request, 'Unidad de medida actualizada exitosamente')
            return redirect('unidades_lista')
    else:
        form = UnidadMedidaForm(instance=unidad)
    
    return render(request, 'catalogos/unidades/form.html', {
        'form': form,
        'titulo': 'Editar Unidad de Medida',
        'accion': 'Actualizar',
        'unidad': unidad
    })


@login_required
@admin_required
def unidades_eliminar(request, pk):
    unidad = get_object_or_404(UnidadMedida, pk=pk)
    
    if request.method == 'POST':
        # Verificar si hay productos asociados
        productos_count = Producto.objects.filter(unidad_medida=unidad).count()
        
        if productos_count > 0:
            messages.error(request, f'No se puede eliminar la unidad. Tiene {productos_count} productos asociados.')
            return redirect('unidades_lista')
        
        unidad.delete()
        messages.success(request, 'Unidad de medida eliminada exitosamente')
        return redirect('unidades_lista')
    
    return render(request, 'catalogos/unidades/eliminar.html', {
        'unidad': unidad
    })


# =========== PRODUCTOS ===========
@login_required
def productos_lista(request):
    query = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')
    proveedor_id = request.GET.get('proveedor', '')
    estado = request.GET.get('estado', 'activos')
    sucursal = request.user.sucursal
    
    productos = Producto.objects.all()
    
    if query:
        productos = productos.filter(
            Q(codigo__icontains=query) |
            Q(nombre__icontains=query) |
            Q(descripcion__icontains=query)
        )
    
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)
    
    if proveedor_id:
        productos = productos.filter(proveedor_id=proveedor_id)
    
    if estado == 'activos':
        productos = productos.filter(activo=True)
    elif estado == 'inactivos':
        productos = productos.filter(activo=False)
    
    # Si el usuario tiene sucursal, agregar información de stock
    productos_info = []
    for producto in productos:
        info = {
            'id': producto.id,
            'codigo': producto.codigo,
            'nombre': producto.nombre,
            'descripcion': producto.descripcion,
            'tipo': producto.get_tipo_display(),
            'categoria': producto.categoria,
            'proveedor': producto.proveedor,
            'costo_promedio': producto.costo_promedio,
            'activo': producto.activo,
            'tiene_iva': producto.tiene_iva,
            'precio_venta_promedio': producto.precio_venta_promedio,
            'stock_total': producto.stock_total,
        }
        
        # Agregar información específica de la sucursal
        if sucursal:
            producto_sucursal = ProductoSucursal.objects.filter(
                producto=producto,
                sucursal=sucursal
            ).first()
            
            if producto_sucursal:
                info.update({
                    'precio_venta': producto_sucursal.precio_venta,
                    'stock': producto_sucursal.stock,
                    'stock_minimo': producto_sucursal.stock_minimo,
                    'stock_maximo': producto_sucursal.stock_maximo,
                    'estado_stock': producto_sucursal.estado_stock,
                    'producto_sucursal_id': producto_sucursal.id,
                })
        
        productos_info.append(info)
    
    # Paginación
    paginator = Paginator(productos_info, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categorias = Categoria.objects.filter(activa=True)
    proveedores = Proveedor.objects.filter(activo=True)
    
    context = {
        'productos': page_obj,
        'query': query,
        'categoria_id': categoria_id,
        'proveedor_id': proveedor_id,
        'estado': estado,
        'sucursal': sucursal,
        'categorias': categorias,
        'proveedores': proveedores,
        'total_count': productos.count(),
        'activos_count': Producto.objects.filter(activo=True).count(),
        'inactivos_count': Producto.objects.filter(activo=False).count(),
    }
    return render(request, 'catalogos/productos/lista.html', context)


@login_required
@admin_required
def productos_crear(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            producto = form.save()
            
            # Si el usuario tiene sucursal, crear ProductoSucursal
            if request.user.sucursal:
                ProductoSucursal.objects.create(
                    producto=producto,
                    sucursal=request.user.sucursal,
                    precio_venta=0,
                    stock=0
                )
            
            messages.success(request, 'Producto creado exitosamente')
            return redirect('productos_lista')
    else:
        form = ProductoForm()
    
    categorias = Categoria.objects.filter(activa=True)
    proveedores = Proveedor.objects.filter(activo=True)
    unidades = UnidadMedida.objects.all()
    
    return render(request, 'catalogos/productos/form.html', {
        'form': form,
        'titulo': 'Nuevo Producto',
        'accion': 'Crear',
        'categorias': categorias,
        'proveedores': proveedores,
        'unidades': unidades
    })


@login_required
@puede_editar_precios
def productos_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            producto = form.save()
            messages.success(request, 'Producto actualizado exitosamente')
            return redirect('productos_lista')
    else:
        form = ProductoForm(instance=producto)
    
    categorias = Categoria.objects.filter(activa=True)
    proveedores = Proveedor.objects.filter(activo=True)
    unidades = UnidadMedida.objects.all()
    
    return render(request, 'catalogos/productos/form.html', {
        'form': form,
        'titulo': 'Editar Producto',
        'accion': 'Actualizar',
        'producto': producto,
        'categorias': categorias,
        'proveedores': proveedores,
        'unidades': unidades
    })


@login_required
@admin_required
def productos_eliminar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    
    if request.method == 'POST':
        # Verificar si hay ventas asociadas
        from ventas.models import DetalleVenta
        ventas_count = DetalleVenta.objects.filter(producto__producto=producto).count()
        
        if ventas_count > 0:
            messages.error(request, f'No se puede eliminar el producto. Tiene {ventas_count} ventas asociadas.')
            return redirect('productos_lista')
        
        producto.delete()
        messages.success(request, 'Producto eliminado exitosamente')
        return redirect('productos_lista')
    
    return render(request, 'catalogos/productos/eliminar.html', {
        'producto': producto
    })


@login_required
@admin_required
def productos_toggle(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    producto.activo = not producto.activo
    producto.save()
    
    estado = "activado" if producto.activo else "desactivado"
    messages.success(request, f'Producto {estado} exitosamente')
    return redirect('productos_lista')


@login_required
@admin_required
def productos_detalle(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    sucursal = request.user.sucursal
    
    # Obtener información por sucursal
    productos_sucursal = ProductoSucursal.objects.filter(producto=producto)
    
    # Si el usuario tiene sucursal, obtener movimientos recientes
    movimientos = None
    if sucursal:
        producto_sucursal = productos_sucursal.filter(sucursal=sucursal).first()
        if producto_sucursal:
            movimientos = MovimientoInventario.objects.filter(
                producto_sucursal=producto_sucursal
            ).order_by('-fecha')[:10]
    else:
        # Superadmin: obtener todos los movimientos
        movimientos = MovimientoInventario.objects.filter(
            producto_sucursal__producto=producto
        ).order_by('-fecha')[:10]
    
    return render(request, 'catalogos/productos/detalle.html', {
        'producto': producto,
        'productos_sucursal': productos_sucursal,
        'movimientos': movimientos,
        'sucursal': sucursal
    })


@login_required
@puede_editar_precios
def productos_precios(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    productos_sucursal = ProductoSucursal.objects.filter(
        producto=producto
    ).select_related('sucursal')
    
    # Crear ProductoSucursal para sucursales que no lo tengan
    sucursales_existentes = productos_sucursal.values_list('sucursal_id', flat=True)
    sucursales_faltantes = Sucursal.objects.filter(activa=True).exclude(id__in=sucursales_existentes)
    
    for sucursal in sucursales_faltantes:
        ProductoSucursal.objects.create(
            producto=producto,
            sucursal=sucursal,
            precio_venta=0,
            stock=0
        )
    
    # Re-obtener todos
    productos_sucursal = ProductoSucursal.objects.filter(
        producto=producto
    ).select_related('sucursal')
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                for ps in productos_sucursal:
                    precio_key = f'precio_{ps.id}'
                    stock_key = f'stock_{ps.id}'
                    stock_min_key = f'stock_min_{ps.id}'
                    stock_max_key = f'stock_max_{ps.id}'
                    
                    if precio_key in request.POST:
                        precio = request.POST[precio_key]
                        if precio:
                            ps.precio_venta = float(precio)
                    
                    if stock_key in request.POST:
                        stock = request.POST[stock_key]
                        if stock:
                            ps.stock = float(stock)
                    
                    if stock_min_key in request.POST:
                        stock_min = request.POST[stock_min_key]
                        if stock_min:
                            ps.stock_minimo = float(stock_min)
                    
                    if stock_max_key in request.POST:
                        stock_max = request.POST[stock_max_key]
                        if stock_max:
                            ps.stock_maximo = float(stock_max)
                    
                    ps.save()
            
            messages.success(request, 'Precios y stocks actualizados exitosamente')
            return redirect('productos_lista')
            
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    
    return render(request, 'catalogos/productos/precios.html', {
        'producto': producto,
        'productos_sucursal': productos_sucursal
    })


# =========== INVENTARIO ===========
@login_required
@admin_required
def inventario_lista(request):
    sucursal = request.user.sucursal
    if not sucursal:
        messages.error(request, "No tienes una sucursal asignada")
        return redirect('dashboard')
    
    query = request.GET.get('q', '')
    estado = request.GET.get('estado', 'todos')
    
    productos_sucursal = ProductoSucursal.objects.filter(
        sucursal=sucursal
    ).select_related('producto', 'producto__categoria', 'producto__proveedor')
    
    if query:
        productos_sucursal = productos_sucursal.filter(
            Q(producto__codigo__icontains=query) |
            Q(producto__nombre__icontains=query) |
            Q(producto__descripcion__icontains=query)
        )
    
    if estado == 'bajo':
        productos_sucursal = productos_sucursal.filter(stock__lte=models.F('stock_minimo'))
    elif estado == 'normal':
        productos_sucursal = productos_sucursal.filter(
            stock__gt=models.F('stock_minimo'),
            stock__lt=models.F('stock_maximo')
        )
    elif estado == 'alto':
        productos_sucursal = productos_sucursal.filter(stock__gte=models.F('stock_maximo'))
    
    # Estadísticas
    total_productos = productos_sucursal.count()
    productos_bajo_stock = productos_sucursal.filter(stock__lte=models.F('stock_minimo')).count()
    valor_inventario = sum(ps.producto.costo_promedio * ps.stock for ps in productos_sucursal)
    
    # Paginación
    paginator = Paginator(productos_sucursal, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'productos_sucursal': page_obj,
        'sucursal': sucursal,
        'query': query,
        'estado': estado,
        'total_productos': total_productos,
        'productos_bajo_stock': productos_bajo_stock,
        'valor_inventario': valor_inventario,
    }
    return render(request, 'catalogos/inventario/lista.html', context)


@login_required
@admin_required
def inventario_ajuste(request):
    sucursal = request.user.sucursal
    if not sucursal:
        messages.error(request, "No tienes una sucursal asignada")
        return redirect('dashboard')
    
    if request.method == 'POST':
        producto_id = request.POST.get('producto')
        tipo = request.POST.get('tipo')
        cantidad = request.POST.get('cantidad')
        motivo = request.POST.get('motivo')
        
        try:
            producto_sucursal = ProductoSucursal.objects.get(
                id=producto_id,
                sucursal=sucursal
            )
            
            cantidad = float(cantidad)
            
            if tipo == 'entrada':
                nuevo_stock = producto_sucursal.stock + cantidad
            elif tipo == 'salida':
                if cantidad > producto_sucursal.stock:
                    messages.error(request, 'No hay suficiente stock disponible')
                    return redirect('inventario_ajuste')
                nuevo_stock = producto_sucursal.stock - cantidad
            else:  # ajuste
                nuevo_stock = cantidad
            
            # Registrar movimiento
            MovimientoInventario.objects.create(
                producto_sucursal=producto_sucursal,
                tipo='ajuste',
                cantidad=abs(nuevo_stock - producto_sucursal.stock),
                cantidad_anterior=producto_sucursal.stock,
                cantidad_nueva=nuevo_stock,
                motivo=motivo,
                usuario=request.user,
                referencia='Ajuste manual'
            )
            
            # Actualizar stock
            producto_sucursal.stock = nuevo_stock
            producto_sucursal.save()
            
            messages.success(request, 'Ajuste de inventario registrado exitosamente')
            return redirect('inventario_lista')
            
        except Exception as e:
            messages.error(request, f'Error al realizar ajuste: {str(e)}')
    
    productos = ProductoSucursal.objects.filter(
        sucursal=sucursal,
        activo=True
    ).select_related('producto')
    
    return render(request, 'catalogos/inventario/ajuste.html', {
        'sucursal': sucursal,
        'productos': productos
    })


@login_required
@admin_required
def inventario_movimientos(request):
    sucursal = request.user.sucursal
    if not sucursal:
        messages.error(request, "No tienes una sucursal asignada")
        return redirect('dashboard')
    
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    tipo = request.GET.get('tipo', '')
    
    movimientos = MovimientoInventario.objects.filter(
        producto_sucursal__sucursal=sucursal
    ).select_related(
        'producto_sucursal__producto',
        'usuario'
    ).order_by('-fecha')
    
    if fecha_inicio:
        movimientos = movimientos.filter(fecha__date__gte=fecha_inicio)
    
    if fecha_fin:
        movimientos = movimientos.filter(fecha__date__lte=fecha_fin)
    
    if tipo:
        movimientos = movimientos.filter(tipo=tipo)
    
    # Estadísticas
    entradas = movimientos.filter(tipo='entrada').aggregate(
        total=Sum('cantidad')
    )['total'] or 0
    
    salidas = movimientos.filter(tipo='salida').aggregate(
        total=Sum('cantidad')
    )['total'] or 0
    
    # Paginación
    paginator = Paginator(movimientos, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'movimientos': page_obj,
        'sucursal': sucursal,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin,
        'tipo': tipo,
        'entradas': entradas,
        'salidas': salidas,
        'diferencia': entradas - salidas,
    }
    return render(request, 'catalogos/inventario/movimientos.html', context)


@login_required
@admin_required
def inventario_reporte(request):
    sucursal = request.user.sucursal
    if not sucursal:
        messages.error(request, "No tienes una sucursal asignada")
        return redirect('dashboard')
    
    # Obtener productos con bajo stock
    productos_bajo_stock = ProductoSucursal.objects.filter(
        sucursal=sucursal,
        stock__lte=models.F('stock_minimo'),
        activo=True
    ).select_related('producto').order_by('stock')
    
    # Obtener productos más vendidos (últimos 30 días)
    from django.db.models import Sum
    from ventas.models import DetalleVenta
    from datetime import datetime, timedelta
    
    fecha_inicio = datetime.now() - timedelta(days=30)
    
    productos_vendidos = DetalleVenta.objects.filter(
        venta__sucursal=sucursal,
        venta__fecha__gte=fecha_inicio
    ).values(
        'producto__producto__codigo',
        'producto__producto__nombre'
    ).annotate(
        total_vendido=Sum('cantidad')
    ).order_by('-total_vendido')[:10]
    
    # Obtener valor total del inventario
    valor_inventario = ProductoSucursal.objects.filter(
        sucursal=sucursal,
        activo=True
    ).aggregate(
        total=models.Sum(models.F('stock') * models.F('producto__costo_promedio'))
    )['total'] or 0
    
    context = {
        'sucursal': sucursal,
        'productos_bajo_stock': productos_bajo_stock,
        'productos_vendidos': productos_vendidos,
        'valor_inventario': valor_inventario,
        'total_productos': ProductoSucursal.objects.filter(sucursal=sucursal, activo=True).count(),
        'productos_sin_stock': ProductoSucursal.objects.filter(sucursal=sucursal, stock=0, activo=True).count(),
    }
    return render(request, 'catalogos/inventario/reporte.html', context)

# Clientes=============================================
# =========== CLIENTES ===========
@login_required
def clientes_lista(request):
    """Lista de clientes con filtros"""
    form = ClienteFilterForm(request.GET)
    clientes = Cliente.objects.all()
    
    if form.is_valid():
        query = form.cleaned_data.get('q')
        tipo_cliente = form.cleaned_data.get('tipo_cliente')
        estado = form.cleaned_data.get('estado')
        
        if query:
            clientes = clientes.filter(
                Q(codigo__icontains=query) |
                Q(nombre__icontains=query) |
                Q(apellido__icontains=query) |
                Q(telefono__icontains=query) |
                Q(email__icontains=query) |
                Q(rfc__icontains=query)
            )
        
        if tipo_cliente:
            clientes = clientes.filter(tipo_cliente=tipo_cliente)
        
        if estado == 'activos':
            clientes = clientes.filter(activo=True)
        elif estado == 'inactivos':
            clientes = clientes.filter(activo=False)
    
    # Estadísticas
    total_clientes = clientes.count()
    clientes_activos = clientes.filter(activo=True).count()
    clientes_normal = clientes.filter(tipo_cliente='normal').count()
    clientes_frecuente = clientes.filter(tipo_cliente='frecuente').count()
    clientes_premium = clientes.filter(tipo_cliente='premium').count()
    
    # Paginación
    paginator = Paginator(clientes, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'clientes': page_obj,
        'form': form,
        'total_clientes': total_clientes,
        'clientes_activos': clientes_activos,
        'clientes_inactivos': total_clientes - clientes_activos,
        'clientes_normal': clientes_normal,
        'clientes_frecuente': clientes_frecuente,
        'clientes_premium': clientes_premium,
    }
    return render(request, 'catalogos/clientes/lista.html', context)


@login_required
def clientes_crear(request):
    """Crear nuevo cliente"""
    if request.method == 'POST':
        form = ClienteForm(request.POST, request=request)
        if form.is_valid():
            cliente = form.save(commit=False)
            
            # Si es cajero, asegurar que sea cliente normal sin descuento
            if not (request.user.es_admin or request.user.es_superadmin):
                cliente.tipo_cliente = 'normal'
                cliente.porcentaje_descuento = 0
            
            # Asignar sucursal de registro
            cliente.sucursal_registro = request.user.sucursal
            cliente.save()
            
            messages.success(request, 'Cliente creado exitosamente')
            return redirect('clientes_lista')
    else:
        # Generar código automático
        ultimo_cliente = Cliente.objects.order_by('-id').first()
        ultimo_numero = int(ultimo_cliente.codigo[3:]) if ultimo_cliente and ultimo_cliente.codigo.startswith('CLI') else 0
        nuevo_codigo = f"CLI{str(ultimo_numero + 1).zfill(6)}"
        
        form = ClienteForm(initial={'codigo': nuevo_codigo}, request=request)
    
    return render(request, 'catalogos/clientes/form.html', {
        'form': form,
        'titulo': 'Nuevo Cliente',
        'accion': 'Crear',
        'puede_editar_descuento': request.user.es_admin or request.user.es_superadmin
    })


@login_required
def clientes_editar(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente, request=request)
        if form.is_valid():
            # Solo admin/superadmin pueden cambiar descuentos
            if not (request.user.es_admin or request.user.es_superadmin):
                # Revertir cambios de descuento si no es admin
                cliente_data = form.cleaned_data
                if (cliente_data.get('tipo_cliente') != cliente.tipo_cliente or 
                    cliente_data.get('porcentaje_descuento') != cliente.porcentaje_descuento):
                    messages.error(request, 'Solo administradores pueden modificar descuentos')
                    return redirect('clientes_lista')
            
            cliente = form.save()
            messages.success(request, 'Cliente actualizado exitosamente')
            return redirect('clientes_lista')


@login_required
@admin_required
def clientes_eliminar(request, pk):
    """Eliminar cliente"""
    cliente = get_object_or_404(Cliente, pk=pk)
    
    if request.method == 'POST':
        # Verificar si tiene ventas asociadas
        from ventas.models import Venta
        ventas_count = Venta.objects.filter(cliente=cliente).count()
        
        if ventas_count > 0:
            messages.error(request, f'No se puede eliminar el cliente. Tiene {ventas_count} ventas asociadas.')
            return redirect('clientes_lista')
        
        cliente.delete()
        messages.success(request, 'Cliente eliminado exitosamente')
        return redirect('clientes_lista')
    
    return render(request, 'catalogos/clientes/eliminar.html', {
        'cliente': cliente
    })


@login_required
@admin_required
def clientes_toggle(request, pk):
    """Activar/Desactivar cliente"""
    cliente = get_object_or_404(Cliente, pk=pk)
    cliente.activo = not cliente.activo
    cliente.save()
    
    estado = "activado" if cliente.activo else "desactivado"
    messages.success(request, f'Cliente {estado} exitosamente')
    return redirect('clientes_lista')


@login_required
def clientes_detalle(request, pk):
    """Detalle del cliente con historial de compras"""
    cliente = get_object_or_404(Cliente, pk=pk)
    
    # Obtener ventas del cliente
    from ventas.models import Venta
    ventas = Venta.objects.filter(cliente=cliente).order_by('-fecha')
    
    # Obtener historial de descuentos
    historial_descuentos = HistorialDescuento.objects.filter(cliente=cliente).order_by('-fecha_cambio')
    
    # Estadísticas
    total_ventas = ventas.count()
    monto_total = cliente.monto_total_compras
    ultima_compra = ventas.first()
    
    # Paginación de ventas
    paginator = Paginator(ventas, 10)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    context = {
        'cliente': cliente,
        'ventas': page_obj,
        'historial_descuentos': historial_descuentos,
        'total_ventas': total_ventas,
        'monto_total': monto_total,
        'ultima_compra': ultima_compra,
        'puede_editar_descuento': request.user.es_admin or request.user.es_superadmin
    }
    return render(request, 'catalogos/clientes/detalle.html', context)


@login_required
@admin_required
def clientes_historial(request, pk):
    """Historial completo del cliente"""
    cliente = get_object_or_404(Cliente, pk=pk)
    
    # Obtener todas las ventas
    from ventas.models import Venta
    ventas = Venta.objects.filter(cliente=cliente).order_by('-fecha')
    
    # Obtener historial de descuentos
    historial_descuentos = HistorialDescuento.objects.filter(cliente=cliente).order_by('-fecha_cambio')
    
    context = {
        'cliente': cliente,
        'ventas': ventas,
        'historial_descuentos': historial_descuentos,
    }
    return render(request, 'catalogos/clientes/historial.html', context)


@login_required
def clientes_buscar(request):
    """Búsqueda rápida de clientes para ventas"""
    query = request.GET.get('q', '')
    
    if query:
        clientes = Cliente.objects.filter(
            Q(codigo__icontains=query) |
            Q(nombre__icontains=query) |
            Q(apellido__icontains=query) |
            Q(telefono__icontains=query) |
            Q(email__icontains=query)
        ).filter(activo=True)[:10]
    else:
        clientes = Cliente.objects.filter(activo=True)[:10]
    
    results = []
    for cliente in clientes:
        results.append({
            'id': cliente.id,
            'codigo': cliente.codigo,
            'nombre': cliente.nombre_completo,
            'telefono': cliente.telefono,
            'email': cliente.email,
            'tipo_cliente': cliente.get_tipo_cliente_display(),
            'descuento': float(cliente.porcentaje_descuento),
            'direccion': cliente.direccion_facturacion,
        })
    
    return JsonResponse({'clientes': results})


@login_required
@admin_required
@require_POST
def clientes_cambiar_descuento(request, pk):
    """Cambiar descuento del cliente (solo admin/superadmin)"""
    cliente = get_object_or_404(Cliente, pk=pk)
    
    tipo_cliente = request.POST.get('tipo_cliente')
    porcentaje = request.POST.get('porcentaje_descuento')
    motivo = request.POST.get('motivo', '')
    
    try:
        porcentaje = Decimal(porcentaje)
        
        # Validar rangos según tipo de cliente
        if tipo_cliente == 'normal' and porcentaje != 0:
            return JsonResponse({
                'success': False,
                'message': 'Los clientes normales no pueden tener descuento'
            })
        elif tipo_cliente == 'frecuente' and not (1 <= porcentaje <= 15):
            return JsonResponse({
                'success': False,
                'message': 'El descuento para clientes frecuentes debe estar entre 1% y 15%'
            })
        elif tipo_cliente == 'premium' and not (16 <= porcentaje <= 50):
            return JsonResponse({
                'success': False,
                'message': 'El descuento para clientes premium debe estar entre 16% y 50%'
            })
        
        # Guardar valores anteriores
        tipo_cliente_anterior = cliente.tipo_cliente
        porcentaje_anterior = cliente.porcentaje_descuento
        
        # Actualizar cliente
        cliente.tipo_cliente = tipo_cliente
        cliente.porcentaje_descuento = porcentaje
        cliente.save()
        
        # Registrar en historial
        HistorialDescuento.objects.create(
            cliente=cliente,
            tipo_cliente_anterior=tipo_cliente_anterior,
            tipo_cliente_nuevo=tipo_cliente,
            porcentaje_anterior=porcentaje_anterior,
            porcentaje_nuevo=porcentaje,
            usuario=request.user,
            motivo=motivo
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Descuento actualizado exitosamente',
            'tipo_cliente': cliente.get_tipo_cliente_display(),
            'porcentaje_descuento': float(cliente.porcentaje_descuento)
        })
        
    except (ValueError, InvalidOperation) as e:
        return JsonResponse({
            'success': False,
            'message': 'Porcentaje inválido'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        })