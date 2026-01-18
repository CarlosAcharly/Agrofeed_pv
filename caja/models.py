from django.db import models

# Este archivo puede estar vacío o tener otros modelos relacionados con caja
# El modelo CorteCaja está en ventas/models.py

class ConfiguracionCaja(models.Model):
    """Configuración específica para la caja si es necesaria"""
    nombre = models.CharField(max_length=100)
    valor = models.TextField()
    
    def __str__(self):
        return self.nombre