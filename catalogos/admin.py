from django.contrib import admin
from .models import (
    Proveedor, Categoria, UnidadMedida, 
    Producto, ProductoSucursal, MovimientoInventario
)

@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'telefono', 'email', 'activo', 'fecha_creacion')
    list_filter = ('activo',)
    search_fields = ('nombre', 'email', 'telefono')
    list_per_page = 20


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'padre', 'activa', 'fecha_creacion')
    list_filter = ('activa', 'padre')
    search_fields = ('nombre', 'descripcion')
    list_per_page = 20


@admin.register(UnidadMedida)
class UnidadMedidaAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'abreviatura')
    search_fields = ('nombre', 'abreviatura')


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nombre', 'categoria', 'proveedor', 'activo', 'fecha_creacion')
    list_filter = ('activo', 'tipo', 'categoria', 'proveedor')
    search_fields = ('codigo', 'nombre', 'descripcion')
    list_per_page = 20
    readonly_fields = ('fecha_creacion', 'fecha_actualizacion')


@admin.register(ProductoSucursal)
class ProductoSucursalAdmin(admin.ModelAdmin):
    list_display = ('producto', 'sucursal', 'precio_venta', 'stock', 'activo')
    list_filter = ('activo', 'sucursal')
    search_fields = ('producto__nombre', 'producto__codigo')
    list_per_page = 20
    readonly_fields = ('ultima_actualizacion',)


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = ('producto_sucursal', 'tipo', 'cantidad', 'usuario', 'fecha')
    list_filter = ('tipo', 'fecha')
    search_fields = ('producto_sucursal__producto__nombre', 'motivo')
    list_per_page = 20
    readonly_fields = ('fecha',)