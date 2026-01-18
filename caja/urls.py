from django.urls import path
from . import views

urlpatterns = [
    path('', views.caja_principal, name='caja_principal'),
    path('apertura/', views.apertura_caja, name='apertura_caja'),
    path('cierre/', views.cierre_caja, name='cierre_caja'),
    path('historial/', views.historial_cortes, name='historial_cortes'),
    path('corte/<int:pk>/', views.detalle_corte, name='detalle_corte'),
]