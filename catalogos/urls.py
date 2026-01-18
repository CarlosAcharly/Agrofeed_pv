from django.urls import path
from . import views

urlpatterns = [
    # =========== PROVEEDORES ===========
    path('proveedores/', views.proveedores_lista, name='proveedores_lista'),
    path('proveedores/crear/', views.proveedores_crear, name='proveedores_crear'),
    path('proveedores/editar/<int:pk>/', views.proveedores_editar, name='proveedores_editar'),
    path('proveedores/eliminar/<int:pk>/', views.proveedores_eliminar, name='proveedores_eliminar'),
    path('proveedores/toggle/<int:pk>/', views.proveedores_toggle, name='proveedores_toggle'),
    path('proveedores/detalle/<int:pk>/', views.proveedores_detalle, name='proveedores_detalle'),
    
    # =========== CATEGORÍAS ===========
    path('categorias/', views.categorias_lista, name='categorias_lista'),
    path('categorias/crear/', views.categorias_crear, name='categorias_crear'),
    path('categorias/editar/<int:pk>/', views.categorias_editar, name='categorias_editar'),
    path('categorias/eliminar/<int:pk>/', views.categorias_eliminar, name='categorias_eliminar'),
    path('categorias/toggle/<int:pk>/', views.categorias_toggle, name='categorias_toggle'),
    
    # =========== UNIDADES DE MEDIDA ===========
    path('unidades/', views.unidades_lista, name='unidades_lista'),
    path('unidades/crear/', views.unidades_crear, name='unidades_crear'),
    path('unidades/editar/<int:pk>/', views.unidades_editar, name='unidades_editar'),
    path('unidades/eliminar/<int:pk>/', views.unidades_eliminar, name='unidades_eliminar'),
    
    # =========== PRODUCTOS ===========
    path('productos/', views.productos_lista, name='productos_lista'),
    path('productos/crear/', views.productos_crear, name='productos_crear'),
    path('productos/editar/<int:pk>/', views.productos_editar, name='productos_editar'),
    path('productos/eliminar/<int:pk>/', views.productos_eliminar, name='productos_eliminar'),
    path('productos/toggle/<int:pk>/', views.productos_toggle, name='productos_toggle'),
    path('productos/detalle/<int:pk>/', views.productos_detalle, name='productos_detalle'),
    path('productos/precios/<int:pk>/', views.productos_precios, name='productos_precios'),
    
    # =========== INVENTARIO ===========
    path('inventario/', views.inventario_lista, name='inventario_lista'),
    path('inventario/ajuste/', views.inventario_ajuste, name='inventario_ajuste'),
    path('inventario/movimientos/', views.inventario_movimientos, name='inventario_movimientos'),
    path('inventario/reporte/', views.inventario_reporte, name='inventario_reporte'),

    # ============ Clientes ===========
    # Agrega estas rutas al final del urlpatterns

    # =========== CLIENTES ===========
    path('clientes/', views.clientes_lista, name='clientes_lista'),
    path('clientes/crear/', views.clientes_crear, name='clientes_crear'),
    path('clientes/editar/<int:pk>/', views.clientes_editar, name='clientes_editar'),
    path('clientes/eliminar/<int:pk>/', views.clientes_eliminar, name='clientes_eliminar'),
    path('clientes/toggle/<int:pk>/', views.clientes_toggle, name='clientes_toggle'),
    path('clientes/detalle/<int:pk>/', views.clientes_detalle, name='clientes_detalle'),
    path('clientes/historial/<int:pk>/', views.clientes_historial, name='clientes_historial'),
    path('clientes/buscar/', views.clientes_buscar, name='clientes_buscar'),
    path('clientes/descuento/<int:pk>/', views.clientes_cambiar_descuento, name='clientes_cambiar_descuento'),
]