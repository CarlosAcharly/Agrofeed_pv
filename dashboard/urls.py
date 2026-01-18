from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('set-sidebar-state/', views.set_sidebar_state, name='set_sidebar_state'),
]