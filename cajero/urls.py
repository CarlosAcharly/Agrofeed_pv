from django.urls import path
from . import views

app_name = 'cajero'

urlpatterns = [
    # Dashboard
    path('', views.cajero_dashboard, name='cajero_dashboard'),
    
    # Ventas
    path('venta/nueva/', views.cajero_nueva_venta, name='cajero_nueva_venta'),
    path('venta/procesar/', views.cajero_procesar_venta, name='cajero_procesar_venta'),
    path('venta/limpiar/', views.cajero_limpiar_carrito, name='cajero_limpiar_carrito'),
    path('ventas/', views.cajero_lista_ventas, name='cajero_lista_ventas'),
    path('venta/<int:pk>/', views.cajero_detalle_venta, name='cajero_detalle_venta'),
    path('venta/<int:pk>/ticket/', views.cajero_generar_ticket, name='cajero_generar_ticket'),
    
    # Productos
    path('productos/', views.cajero_productos, name='cajero_productos'),
    path('productos/buscar/', views.cajero_buscar_productos, name='cajero_buscar_productos'),
    path('producto/<int:pk>/detalle/', views.cajero_detalle_producto, name='cajero_detalle_producto'),
    
    # Clientes
    path('clientes/', views.cajero_clientes, name='cajero_clientes'),
    path('clientes/buscar/', views.cajero_buscar_clientes, name='cajero_buscar_clientes'),
    path('cliente/nuevo/', views.cajero_nuevo_cliente, name='cajero_nuevo_cliente'),
    path('cliente/<int:pk>/', views.cajero_detalle_cliente, name='cajero_detalle_cliente'),
    
    # Cortes de Caja
    path('cortes/', views.cajero_cortes, name='cajero_cortes'),
    path('corte/apertura/', views.cajero_apertura_caja, name='cajero_apertura_caja'),
    path('corte/cierre/', views.cajero_cierre_caja, name='cajero_cierre_caja'),
    path('corte/<int:pk>/', views.cajero_detalle_corte, name='cajero_detalle_corte'),
    
    # Reportes
    path('reportes/ventas/', views.cajero_reportes_ventas, name='cajero_reportes_ventas'),
    path('reportes/productos/', views.cajero_reportes_productos, name='cajero_reportes_productos'),
    
    # AJAX endpoints
    path('ajax/agregar-carrito/', views.ajax_agregar_carrito, name='ajax_agregar_carrito'),
    path('ajax/remover-carrito/', views.ajax_remover_carrito, name='ajax_remover_carrito'),
    path('ajax/actualizar-cantidad/', views.ajax_actualizar_cantidad, name='ajax_actualizar_cantidad'),
    path('ajax/seleccionar-cliente/', views.ajax_seleccionar_cliente, name='ajax_seleccionar_cliente'),
    path('ajax/calcular-totales/', views.ajax_calcular_totales, name='ajax_calcular_totales'),
]