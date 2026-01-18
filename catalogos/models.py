from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Avg

from sucursales.models import Sucursal


class Proveedor(models.Model):
    nombre = models.CharField(max_length=150)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    rfc = models.CharField(max_length=20, blank=True, verbose_name="RFC")
    contacto = models.CharField(max_length=100, blank=True)
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Proveedor"
        verbose_name_plural = "Proveedores"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    padre = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subcategorias'
    )
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre']

    def __str__(self):
        if self.padre:
            return f"{self.padre.nombre} > {self.nombre}"
        return self.nombre


class UnidadMedida(models.Model):
    nombre = models.CharField(max_length=50)
    abreviatura = models.CharField(max_length=10)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Unidad de Medida"
        verbose_name_plural = "Unidades de Medida"

    def __str__(self):
        return f"{self.nombre} ({self.abreviatura})"


class Producto(models.Model):
    TIPO_CHOICES = [
        ('producto', 'Producto'),
        ('servicio', 'Servicio'),
        ('insumo', 'Insumo'),
    ]
    
    codigo = models.CharField(max_length=50, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='producto')
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    unidad_medida = models.ForeignKey(
        UnidadMedida,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    costo_promedio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    activo = models.BooleanField(default=True)
    tiene_iva = models.BooleanField(default=True)
    imagen = models.ImageField(upload_to='productos/', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def precio_venta_promedio(self):
        precios = ProductoSucursal.objects.filter(producto=self)
        if precios.exists():
            return precios.aggregate(models.Avg('precio_venta'))['precio_venta__avg']
        return 0

    @property
    def stock_total(self):
        stock = ProductoSucursal.objects.filter(producto=self)
        if stock.exists():
            return stock.aggregate(models.Sum('stock'))['stock__sum']
        return 0


class ProductoSucursal(models.Model):
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name='sucursales'
    )
    sucursal = models.ForeignKey(
        Sucursal,
        on_delete=models.CASCADE
    )
    precio_venta = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    stock = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )
    stock_minimo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=5
    )
    stock_maximo = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100
    )
    activo = models.BooleanField(default=True)
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('producto', 'sucursal')
        verbose_name = "Producto por Sucursal"
        verbose_name_plural = "Productos por Sucursal"

    def __str__(self):
        return f"{self.producto} - {self.sucursal}"

    @property
    def estado_stock(self):
        if self.stock <= self.stock_minimo:
            return 'bajo'
        elif self.stock >= self.stock_maximo:
            return 'alto'
        else:
            return 'normal'


class MovimientoInventario(models.Model):
    TIPO_CHOICES = [
        ('entrada', 'Entrada'),
        ('salida', 'Salida'),
        ('ajuste', 'Ajuste'),
        ('transferencia', 'Transferencia'),
    ]
    
    producto_sucursal = models.ForeignKey(
        ProductoSucursal,
        on_delete=models.CASCADE,
        related_name='movimientos'
    )
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_anterior = models.DecimalField(max_digits=10, decimal_places=2)
    cantidad_nueva = models.DecimalField(max_digits=10, decimal_places=2)
    motivo = models.TextField()
    usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT
    )
    referencia = models.CharField(max_length=100, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']
        verbose_name = "Movimiento de Inventario"
        verbose_name_plural = "Movimientos de Inventario"

    def __str__(self):
        return f"{self.tipo} - {self.producto_sucursal} - {self.cantidad}"
    
# Agrega esto al final del archivo models.py después del modelo MovimientoInventario

class Cliente(models.Model):
    TIPO_CLIENTE_CHOICES = [
        ('normal', 'Normal (0%)'),
        ('frecuente', 'Frecuente (1-15%)'),
        ('premium', 'Premium (16-50%)'),
    ]
    
    # Información personal
    codigo = models.CharField(max_length=20, unique=True, verbose_name="Código")
    nombre = models.CharField(max_length=200)
    apellido = models.CharField(max_length=200)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    rfc = models.CharField(max_length=20, blank=True, verbose_name="RFC")
    fecha_nacimiento = models.DateField(null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)
    
    # Tipo y descuento
    tipo_cliente = models.CharField(
        max_length=20, 
        choices=TIPO_CLIENTE_CHOICES, 
        default='normal'
    )
    porcentaje_descuento = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(50)]
    )
    
    # Direcciones
    direccion_facturacion = models.TextField(blank=True, verbose_name="Dirección de Facturación")
    direccion_envio = models.TextField(blank=True, verbose_name="Dirección de Envío")
    ciudad = models.CharField(max_length=100, blank=True)
    estado = models.CharField(max_length=100, blank=True)
    codigo_postal = models.CharField(max_length=10, blank=True)
    
    # Información adicional
    notas = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    sucursal_registro = models.ForeignKey(
        Sucursal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ['nombre', 'apellido']
        indexes = [
            models.Index(fields=['codigo']),
            models.Index(fields=['tipo_cliente']),
            models.Index(fields=['activo']),
        ]
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre} {self.apellido}"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    @property
    def total_compras(self):
        """Total de compras realizadas por el cliente"""
        from ventas.models import Venta
        return Venta.objects.filter(cliente=self).count()
    
    @property
    def monto_total_compras(self):
        """Monto total de compras realizadas por el cliente"""
        from ventas.models import Venta
        ventas = Venta.objects.filter(cliente=self)
        if ventas.exists():
            return ventas.aggregate(total=Sum('total'))['total'] or 0
        return 0
    
    def get_ultima_compra(self):
        """Obtiene la última compra del cliente"""
        from ventas.models import Venta
        return Venta.objects.filter(cliente=self).order_by('-fecha').first()


class HistorialDescuento(models.Model):
    """Registro de cambios en el descuento del cliente"""
    cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE,
        related_name='historial_descuentos'
    )
    tipo_cliente_anterior = models.CharField(max_length=20)
    tipo_cliente_nuevo = models.CharField(max_length=20)
    porcentaje_anterior = models.DecimalField(max_digits=5, decimal_places=2)
    porcentaje_nuevo = models.DecimalField(max_digits=5, decimal_places=2)
    usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.PROTECT
    )
    motivo = models.TextField(blank=True)
    fecha_cambio = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-fecha_cambio']
        verbose_name = "Historial de Descuento"
        verbose_name_plural = "Historial de Descuentos"
    
    def __str__(self):
        return f"{self.cliente} - {self.porcentaje_anterior}% → {self.porcentaje_nuevo}%"