from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

User = settings.AUTH_USER_MODEL

class Venta(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('completada', 'Completada'),
        ('cancelada', 'Cancelada'),
    ]
    
    # Relaciones principales
    sucursal = models.ForeignKey(
        'sucursales.Sucursal',
        on_delete=models.PROTECT
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ventas'
    )
    cliente = models.ForeignKey(
        'catalogos.Cliente',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ventas'
    )
    
    # Información de la venta
    folio = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name="Folio de Venta"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='completada'
    )
    
    # Totales
    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    descuento_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    descuento_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    total = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )
    
    # Información adicional
    fecha = models.DateTimeField(auto_now_add=True)
    cerrada = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)
    forma_pago = models.CharField(
        max_length=50,
        default='efectivo',
        choices=[
            ('efectivo', 'Efectivo'),
            ('tarjeta', 'Tarjeta'),
            ('transferencia', 'Transferencia'),
            ('mixto', 'Mixto'),
        ]
    )
    
    # Campos para caja
    efectivo_recibido = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    cambio = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    # Auditoría
    creado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ventas_creadas',
        null=True
    )
    actualizado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='ventas_actualizadas',
        null=True,
        blank=True
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Venta"
        verbose_name_plural = "Ventas"
        ordering = ['-fecha']
        indexes = [
            models.Index(fields=['folio']),
            models.Index(fields=['fecha']),
            models.Index(fields=['cliente']),
            models.Index(fields=['estado']),
            models.Index(fields=['sucursal', 'fecha']),
        ]
        permissions = [
            ('puede_cancelar_venta', 'Puede cancelar ventas'),
            ('puede_ver_todas_ventas', 'Puede ver todas las ventas'),
            ('puede_ver_reportes', 'Puede ver reportes de ventas'),
        ]

    def __str__(self):
        return f"Venta {self.folio} - {self.fecha.strftime('%d/%m/%Y %H:%M')}"

    def save(self, *args, **kwargs):
        # Generar folio automático si no existe
        if not self.folio:
            from django.utils import timezone
            year = timezone.now().year
            last_venta = Venta.objects.filter(
                sucursal=self.sucursal,
                fecha__year=year
            ).order_by('-id').first()
            
            if last_venta and last_venta.folio:
                try:
                    last_num = int(last_venta.folio.split('-')[-1])
                    new_num = last_num + 1
                except:
                    new_num = 1
            else:
                new_num = 1
                
            self.folio = f"V-{self.sucursal.codigo}-{year}-{str(new_num).zfill(6)}"
        
        # Calcular cambio si se recibió efectivo
        if self.efectivo_recibido > 0:
            self.cambio = self.efectivo_recibido - self.total
            if self.cambio < 0:
                self.cambio = 0
        
        # Asegurar que el subtotal sea consistente
        if self.subtotal == 0 and self.total > 0:
            if self.descuento_total > 0:
                self.subtotal = self.total + self.descuento_total
            else:
                self.subtotal = self.total
        
        super().save(*args, **kwargs)

    @property
    def nombre_cliente(self):
        """Nombre completo del cliente o 'Público general'"""
        if self.cliente:
            return self.cliente.nombre_completo
        return "Público general"

    @property
    def tipo_cliente(self):
        """Tipo de cliente o 'Sin cliente'"""
        if self.cliente:
            return self.cliente.get_tipo_cliente_display()
        return "Sin cliente"

    @property
    def descuento_aplicado(self):
        """Indica si se aplicó descuento"""
        return self.descuento_total > 0

    @property
    def cantidad_productos(self):
        """Total de productos vendidos"""
        return sum(detalle.cantidad for detalle in self.detalles.all())

    @property
    def promedio_descuento(self):
        """Porcentaje promedio de descuento aplicado"""
        if self.subtotal > 0:
            return (self.descuento_total / self.subtotal) * 100
        return 0

    def calcular_totales(self):
        """Recalcular totales a partir de los detalles"""
        detalles = self.detalles.all()
        if detalles.exists():
            self.subtotal = sum(detalle.subtotal_sin_descuento for detalle in detalles)
            self.descuento_total = sum(detalle.descuento_aplicado for detalle in detalles)
            self.total = sum(detalle.subtotal for detalle in detalles)
            self.save()
    
    def cancelar(self, usuario, motivo=""):
        """Cancelar venta y devolver stock"""
        if self.estado == 'cancelada':
            return False
        
        from catalogos.models import MovimientoInventario
        
        try:
            # Restaurar stock de cada producto
            for detalle in self.detalles.all():
                producto_sucursal = detalle.producto
                
                # Registrar movimiento de inventario
                MovimientoInventario.objects.create(
                    producto_sucursal=producto_sucursal,
                    tipo='entrada',
                    cantidad=detalle.cantidad,
                    cantidad_anterior=producto_sucursal.stock,
                    cantidad_nueva=producto_sucursal.stock + detalle.cantidad,
                    motivo=f'Cancelación venta {self.folio}. {motivo}',
                    usuario=usuario,
                    referencia=f'CANCELACION-{self.folio}'
                )
                
                # Actualizar stock
                producto_sucursal.stock += detalle.cantidad
                producto_sucursal.save()
            
            # Actualizar estado de la venta
            self.estado = 'cancelada'
            self.observaciones = f"Cancelada por {usuario.username}. {motivo}"
            self.actualizado_por = usuario
            self.save()
            
            return True
            
        except Exception as e:
            print(f"Error al cancelar venta: {e}")
            return False


class DetalleVenta(models.Model):
    """Detalle de productos vendidos en una venta"""
    venta = models.ForeignKey(
        Venta,
        related_name='detalles',
        on_delete=models.CASCADE
    )
    producto = models.ForeignKey(
        'catalogos.ProductoSucursal',
        on_delete=models.PROTECT,
        related_name='ventas_detalle'
    )
    
    # Información de la venta
    cantidad = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    
    # Precios
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio original del producto"
    )
    precio_final = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Precio con descuento aplicado"
    )
    descuento_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text="Descuento aplicado por unidad"
    )
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    
    # Información adicional
    descuento_porcentaje = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    tiene_iva = models.BooleanField(default=True)
    
    # Auditoría
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Detalle de Venta"
        verbose_name_plural = "Detalles de Venta"
        ordering = ['id']
        indexes = [
            models.Index(fields=['venta']),
            models.Index(fields=['producto']),
        ]

    def __str__(self):
        return f"{self.producto.producto.nombre} - {self.cantidad} x ${self.precio_final}"

    def save(self, *args, **kwargs):
        # Calcular descuento unitario si no está definido
        if self.descuento_unitario == 0 and self.precio_unitario > self.precio_final:
            self.descuento_unitario = self.precio_unitario - self.precio_final
        
        # Calcular porcentaje de descuento
        if self.precio_unitario > 0 and self.descuento_unitario > 0:
            self.descuento_porcentaje = (self.descuento_unitario / self.precio_unitario) * 100
        
        # Calcular subtotal
        self.subtotal = self.precio_final * self.cantidad
        
        super().save(*args, **kwargs)

    @property
    def nombre_producto(self):
        return self.producto.producto.nombre

    @property
    def codigo_producto(self):
        return self.producto.producto.codigo

    @property
    def descuento_aplicado(self):
        """Descuento total aplicado a este detalle"""
        return self.descuento_unitario * self.cantidad

    @property
    def subtotal_sin_descuento(self):
        """Subtotal sin aplicar descuento"""
        return self.precio_unitario * self.cantidad

    @property
    def porcentaje_descuento_display(self):
        """Porcentaje de descuento formateado"""
        return f"{self.descuento_porcentaje:.2f}%"

    @property
    def iva_calculado(self):
        """IVA calculado para este detalle"""
        if self.tiene_iva:
            return (self.subtotal * Decimal('0.16'))  # 16% IVA
        return Decimal('0')


class CorteCaja(models.Model):
    """Registro de cierres de caja"""
    ESTADO_CHOICES = [
        ('abierto', 'Abierto'),
        ('cerrado', 'Cerrado'),
        ('verificado', 'Verificado'),
    ]
    
    sucursal = models.ForeignKey(
        'sucursales.Sucursal',
        on_delete=models.PROTECT,
        related_name='cortes_caja'
    )
    usuario = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='cortes_caja'
    )
    
    # Información del corte
    folio = models.CharField(
        max_length=20,
        unique=True,
        blank=True,
        verbose_name="Folio de Corte"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default='abierto'
    )
    
    # Fechas
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField(null=True, blank=True)
    fecha_cierre = models.DateTimeField(auto_now_add=True)
    
    # Totales
    total_ventas = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_efectivo_esperado = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_efectivo_real = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_tarjeta = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_transferencia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    total_descuentos = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    # Diferencia
    diferencia = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )
    
    # Información adicional
    observaciones = models.TextField(blank=True)
    ventas_incluidas = models.ManyToManyField(
        Venta,
        related_name='cortes_caja',
        blank=True
    )
    
    # Auditoría
    cerrado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='cortes_cerrados',
        null=True,
        blank=True
    )
    verificado_por = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='cortes_verificados',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = "Corte de Caja"
        verbose_name_plural = "Cortes de Caja"
        ordering = ['-fecha_inicio']
        indexes = [
            models.Index(fields=['folio']),
            models.Index(fields=['estado']),
            models.Index(fields=['sucursal', 'fecha_inicio']),
        ]
        permissions = [
            ('puede_cerrar_corte', 'Puede cerrar cortes de caja'),
            ('puede_verificar_corte', 'Puede verificar cortes de caja'),
            ('puede_ver_todos_cortes', 'Puede ver todos los cortes de caja'),
        ]

    def __str__(self):
        return f"Corte {self.folio} - {self.sucursal} - {self.fecha_inicio.strftime('%d/%m/%Y')}"

    def save(self, *args, **kwargs):
        # Generar folio automático si no existe
        if not self.folio:
            from django.utils import timezone
            year = timezone.now().year
            last_corte = CorteCaja.objects.filter(
                sucursal=self.sucursal,
                fecha_inicio__year=year
            ).order_by('-id').first()
            
            if last_corte and last_corte.folio:
                try:
                    last_num = int(last_corte.folio.split('-')[-1])
                    new_num = last_num + 1
                except:
                    new_num = 1
            else:
                new_num = 1
                
            self.folio = f"C-{self.sucursal.codigo}-{year}-{str(new_num).zfill(6)}"
        
        # Calcular diferencia
        if self.total_efectivo_esperado > 0 and self.total_efectivo_real > 0:
            self.diferencia = self.total_efectivo_real - self.total_efectivo_esperado
        
        # Si se cierra el corte, actualizar fecha_fin
        if self.estado == 'cerrado' and not self.fecha_fin:
            self.fecha_fin = timezone.now()
        
        super().save(*args, **kwargs)

    @property
    def total_general(self):
        """Total general de ventas (efectivo + tarjeta + transferencia)"""
        return self.total_efectivo_esperado + self.total_tarjeta + self.total_transferencia

    @property
    def ventas_count(self):
        """Número de ventas incluidas en el corte"""
        return self.ventas_incluidas.count()

    @property
    def ventas_canceladas(self):
        """Ventas canceladas en el período"""
        return self.ventas_incluidas.filter(estado='cancelada').count()

    @property
    def descuento_promedio(self):
        """Porcentaje promedio de descuento aplicado"""
        if self.total_ventas > 0 and self.total_descuentos > 0:
            return (self.total_descuentos / (self.total_ventas + self.total_descuentos)) * 100
        return 0

    def calcular_totales(self):
        """Calcular totales a partir de las ventas incluidas"""
        ventas = self.ventas_incluidas.filter(estado='completada')
        
        if ventas.exists():
            self.total_ventas = sum(venta.total for venta in ventas)
            self.total_descuentos = sum(venta.descuento_total for venta in ventas)
            
            # Calcular por forma de pago
            self.total_efectivo_esperado = sum(
                venta.total for venta in ventas.filter(forma_pago='efectivo')
            )
            self.total_tarjeta = sum(
                venta.total for venta in ventas.filter(forma_pago='tarjeta')
            )
            self.total_transferencia = sum(
                venta.total for venta in ventas.filter(forma_pago='transferencia')
            )
            
            # Para pagos mixtos, asumimos que el total está en efectivo
            self.total_efectivo_esperado += sum(
                venta.total for venta in ventas.filter(forma_pago='mixto')
            )
            
            self.save()
    
    def cerrar_corte(self, usuario, efectivo_real, observaciones=""):
        """Cerrar el corte de caja"""
        if self.estado != 'abierto':
            return False
        
        try:
            self.estado = 'cerrado'
            self.total_efectivo_real = efectivo_real
            self.observaciones = observaciones
            self.cerrado_por = usuario
            self.calcular_totales()
            self.save()
            return True
            
        except Exception as e:
            print(f"Error al cerrar corte: {e}")
            return False