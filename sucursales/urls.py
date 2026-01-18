from django.urls import path
from . import views

urlpatterns = [
    # =========== SUCURSALES ===========
    path('', views.sucursales_lista, name='sucursales_lista'),
    path('crear/', views.sucursales_crear, name='sucursales_crear'),
    path('editar/<int:pk>/', views.sucursales_editar, name='sucursales_editar'),
    path('eliminar/<int:pk>/', views.sucursales_eliminar, name='sucursales_eliminar'),
    path('detalle/<int:pk>/', views.sucursales_detalle, name='sucursales_detalle'),
    path('configuracion/<int:pk>/', views.sucursales_configuracion, name='sucursales_configuracion'),
    path('reportes/<int:pk>/', views.sucursales_reportes, name='sucursales_reportes'),
    path('toggle/<int:pk>/', views.sucursales_toggle, name='sucursales_toggle'),
    
    # =========== TRANSFERENCIAS ===========
    path('transferencias/', views.sucursales_transferencias_lista, name='transferencias_lista'),
    path('transferencias/crear/', views.sucursales_transferencias_crear, name='transferencias_crear'),
    path('transferencias/<int:pk>/', views.sucursales_transferencias_detalle, name='transferencias_detalle'),
    
    # =========== API ===========
    path('api/estadisticas/', views.sucursales_estadisticas_api, name='sucursales_estadisticas_api'),
]