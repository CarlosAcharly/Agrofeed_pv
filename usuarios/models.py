from django.contrib.auth.models import AbstractUser
from django.db import models

class Usuario(AbstractUser):
    SUPERADMIN = 'superadmin'
    ADMIN = 'admin'
    CAJERO = 'cajero'

    ROL_CHOICES = [
        (SUPERADMIN, 'Superadmin'),
        (ADMIN, 'Administrador'),
        (CAJERO, 'Cajero'),
    ]

    rol = models.CharField(
        max_length=20,
        choices=ROL_CHOICES
    )

    sucursal = models.ForeignKey(
        'sucursales.Sucursal',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.username

    # =========== NUEVAS PROPIEDADES ===========
    @property
    def es_superadmin(self):
        return self.rol == self.SUPERADMIN
    
    @property
    def es_admin(self):
        return self.rol in [self.ADMIN, self.SUPERADMIN]
    
    @property
    def es_cajero(self):
        return self.rol == self.CAJERO
    
    @property
    def nombre_completo(self):
        """Retorna el nombre completo del usuario"""
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip() if full_name.strip() else self.username