from django.urls import path
from . import views

urlpatterns = [
    # =========== VENTAS ===========
    path('', views.lista_ventas, name='ventas_lista'),
    path('nueva/', views.nueva_venta, name='venta_nueva'),
    path('agregar-item/', views.agregar_item, name='venta_agregar_item'),
    path('remover-item/', views.remover_item, name='venta_remover_item'),
    path('actualizar-cantidad/', views.actualizar_cantidad, name='venta_actualizar_cantidad'),
    path('seleccionar-cliente/', views.seleccionar_cliente, name='venta_seleccionar_cliente'),
    path('buscar-cliente/', views.buscar_cliente, name='venta_buscar_cliente'),
    path('finalizar/', views.finalizar_venta, name='venta_finalizar'),
    path('limpiar/', views.limpiar_carrito, name='venta_limpiar'),
    path('<int:pk>/', views.detalle_venta, name='venta_detalle'),
    path('<int:pk>/cancelar/', views.cancelar_venta, name='venta_cancelar'),
    path('<int:pk>/ticket/', views.generar_ticket, name='venta_ticket'),
    
    # =========== CORTES DE CAJA ===========
    path('cortes/', views.cortes_caja_lista, name='cortes_caja_lista'),
    path('cortes/nuevo/', views.corte_caja_nuevo, name='corte_caja_nuevo'),
    path('cortes/<int:pk>/', views.corte_caja_detalle, name='corte_caja_detalle'),
    path('cortes/<int:pk>/cerrar/', views.corte_caja_cerrar, name='corte_caja_cerrar'),
    path('cortes/<int:pk>/verificar/', views.corte_caja_verificar, name='corte_caja_verificar'),
    
    # =========== REPORTES ===========
    path('reportes/', views.reporte_ventas, name='reporte_ventas'),
    
    # =========== AJAX ===========
    path('ajax/producto-info/', views.get_producto_info, name='ajax_producto_info'),
    path('ajax/ventas-dia/', views.get_ventas_dia, name='ajax_ventas_dia'),
]