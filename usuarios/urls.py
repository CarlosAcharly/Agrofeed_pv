from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_usuarios, name='usuarios_lista'),
    path('crear/', views.crear_usuario, name='usuarios_crear'),
    path('editar/<int:pk>/', views.editar_usuario, name='usuarios_editar'),
    path('eliminar/<int:pk>/', views.eliminar_usuario, name='usuarios_eliminar'),
]