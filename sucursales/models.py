from django.db import models
from django.core.exceptions import ValidationError

class Sucursal(models.Model):
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=100)
    direccion = models.TextField()
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, verbose_name="Correo Electrónico")
    encargado = models.CharField(max_length=100, blank=True, verbose_name="Encargado")
    
    # Configuración
    activa = models.BooleanField(default=True)
    permite_ventas = models.BooleanField(default=True, verbose_name="Permite Ventas")
    permite_compras = models.BooleanField(default=True, verbose_name="Permite Compras")
    
    # Horarios
    horario_apertura = models.TimeField(default='08:00:00', verbose_name="Horario Apertura")
    horario_cierre = models.TimeField(default='18:00:00', verbose_name="Horario Cierre")
    dias_operacion = models.CharField(
        max_length=100, 
        default='Lunes a Viernes',
        verbose_name="Días de Operación"
    )
    
    # Información adicional
    rfc = models.CharField(max_length=20, blank=True, verbose_name="RFC")
    codigo_postal = models.CharField(max_length=10, blank=True, verbose_name="Código Postal")
    ciudad = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=100, blank=True)
    pais = models.CharField(max_length=100, default='México')
    
    # Metadatos
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Sucursal"
        verbose_name_plural = "Sucursales"
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"
    
    def clean(self):
        # Validar que el horario de cierre sea mayor que el de apertura
        if self.horario_cierre <= self.horario_apertura:
            raise ValidationError('El horario de cierre debe ser posterior al horario de apertura.')
    
    @property
    def horario_completo(self):
        return f"{self.horario_apertura.strftime('%H:%M')} - {self.horario_cierre.strftime('%H:%M')}"
    
    @property
    def direccion_completa(self):
        partes = []
        if self.direccion:
            partes.append(self.direccion)
        if self.ciudad:
            partes.append(self.ciudad)
        if self.estado:
            partes.append(self.estado)
        if self.codigo_postal:
            partes.append(f"CP: {self.codigo_postal}")
        if self.pais and self.pais != 'México':
            partes.append(self.pais)
        return ', '.join(partes)
    
    @property
    def estado_operativo(self):
        if not self.activa:
            return "inactiva"
        if not self.permite_ventas and not self.permite_compras:
            return "mantenimiento"
        if self.permite_ventas and self.permite_compras:
            return "completa"
        if self.permite_ventas:
            return "solo_ventas"
        return "solo_compras"


class ConfiguracionSucursal(models.Model):
    sucursal = models.OneToOneField(
        Sucursal, 
        on_delete=models.CASCADE,
        related_name='configuracion'
    )
    
    # Configuración de inventario
    stock_minimo_global = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=5,
        verbose_name="Stock Mínimo Global"
    )
    stock_maximo_global = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        default=100,
        verbose_name="Stock Máximo Global"
    )
    
    # Configuración de ventas
    iva_porcentaje = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        default=16.00,
        verbose_name="% IVA"
    )
    redondeo_ventas = models.BooleanField(
        default=True,
        verbose_name="Redondear Ventas"
    )
    mostrar_stock = models.BooleanField(
        default=True,
        verbose_name="Mostrar Stock en Ventas"
    )
    
    # Configuración de seguridad
    max_intentos_login = models.IntegerField(
        default=3,
        verbose_name="Máx. Intentos de Login"
    )
    tiempo_bloqueo = models.IntegerField(
        default=15,
        verbose_name="Tiempo Bloqueo (minutos)"
    )
    
    # Configuración de reportes
    generar_reporte_diario = models.BooleanField(
        default=True,
        verbose_name="Generar Reporte Diario"
    )
    hora_reporte = models.TimeField(
        default='22:00:00',
        verbose_name="Hora Reporte Diario"
    )
    
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración de Sucursal"
        verbose_name_plural = "Configuraciones de Sucursal"
    
    def __str__(self):
        return f"Configuración - {self.sucursal.nombre}"


class TransferenciaInventario(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('en_proceso', 'En Proceso'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]
    
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código Transferencia")
    sucursal_origen = models.ForeignKey(
        Sucursal,
        on_delete=models.PROTECT,
        related_name='transferencias_salida'
    )
    sucursal_destino = models.ForeignKey(
        Sucursal,
        on_delete=models.PROTECT,
        related_name='transferencias_entrada'
    )
    
    # Información de la transferencia
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='pendiente'
    )
    motivo = models.TextField()
    observaciones = models.TextField(blank=True)
    
    # Control de usuarios
    usuario_solicita = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        related_name='transferencias_solicitadas'
    )
    usuario_autoriza = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transferencias_autorizadas'
    )
    usuario_recibe = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transferencias_recibidas'
    )
    
    # Fechas
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_autorizacion = models.DateTimeField(null=True, blank=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)
    fecha_recepcion = models.DateTimeField(null=True, blank=True)
    fecha_completada = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Transferencia de Inventario"
        verbose_name_plural = "Transferencias de Inventario"
        ordering = ['-fecha_solicitud']
    
    def __str__(self):
        return f"Transferencia #{self.codigo} - {self.sucursal_origen} → {self.sucursal_destino}"
    
    @property
    def total_productos(self):
        return self.detalles.count()
    
    @property
    def total_cantidad(self):
        return sum(detalle.cantidad for detalle in self.detalles.all())


class DetalleTransferencia(models.Model):
    transferencia = models.ForeignKey(
        TransferenciaInventario,
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    producto = models.ForeignKey(
        'catalogos.Producto',
        on_delete=models.PROTECT
    )
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_enviada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    cantidad_recibida = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Detalle de Transferencia"
        verbose_name_plural = "Detalles de Transferencia"
        unique_together = ('transferencia', 'producto')
    
    def __str__(self):
        return f"{self.producto} - {self.cantidad}"