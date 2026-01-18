from django import forms
from .models import (
    Cliente, Proveedor, Categoria, UnidadMedida, 
    Producto, ProductoSucursal
)

class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'telefono', 'email', 'direccion', 'rfc', 'contacto', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del proveedor'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Dirección'}),
            'rfc': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RFC'}),
            'contacto': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Persona de contacto'}),
        }


class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion', 'padre', 'activa']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la categoría'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción'}),
            'padre': forms.Select(attrs={'class': 'form-control'}),
        }


class UnidadMedidaForm(forms.ModelForm):
    class Meta:
        model = UnidadMedida
        fields = ['nombre', 'abreviatura', 'descripcion']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo'}),
            'abreviatura': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Abreviatura'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción'}),
        }


class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = [
            'codigo', 'nombre', 'descripcion', 'tipo', 
            'categoria', 'proveedor', 'unidad_medida',
            'costo_promedio', 'activo', 'tiene_iva', 'imagen'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código del producto'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del producto'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-control'}),
            'proveedor': forms.Select(attrs={'class': 'form-control'}),
            'unidad_medida': forms.Select(attrs={'class': 'form-control'}),
            'costo_promedio': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'tiene_iva': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class ProductoSucursalForm(forms.ModelForm):
    class Meta:
        model = ProductoSucursal
        fields = ['precio_venta', 'stock', 'stock_minimo', 'stock_maximo', 'activo']
        widgets = {
            'precio_venta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_maximo': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# Agrega esto al final del archivo forms.py

class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = [
            'codigo', 'nombre', 'apellido', 'telefono', 'email',
            'rfc', 'fecha_nacimiento', 'tipo_cliente', 
            'porcentaje_descuento', 'direccion_facturacion',
            'direccion_envio', 'ciudad', 'estado', 'codigo_postal',
            'notas', 'activo'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código único del cliente'
            }),
            'nombre': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Nombre(s)'
            }),
            'apellido': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Apellido(s)'
            }),
            'telefono': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Teléfono'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Email'
            }),
            'rfc': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'RFC'
            }),
            'fecha_nacimiento': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'tipo_cliente': forms.Select(attrs={
                'class': 'form-control select-tipo-cliente',
                'id': 'tipo_cliente_select'
            }),
            'porcentaje_descuento': forms.NumberInput(attrs={
                'class': 'form-control descuento-input',
                'step': '0.01',
                'min': '0',
                'max': '50',
                'id': 'porcentaje_descuento_input'
            }),
            'direccion_facturacion': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Dirección de facturación'
            }),
            'direccion_envio': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Dirección de envío'
            }),
            'ciudad': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Ciudad'
            }),
            'estado': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Estado'
            }),
            'codigo_postal': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Código Postal'
            }),
            'notas': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': 'Notas adicionales'
            }),
            'activo': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'porcentaje_descuento': 'Porcentaje de Descuento (%)'
        }

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        # Si no es admin o superadmin, hacer el campo de descuento de solo lectura
        if self.request and not (self.request.user.es_admin or self.request.user.es_superadmin):
            self.fields['porcentaje_descuento'].widget.attrs['readonly'] = True
            self.fields['porcentaje_descuento'].widget.attrs['title'] = 'Solo administradores pueden modificar el descuento'
            self.fields['tipo_cliente'].widget.attrs['disabled'] = True


class ClienteFilterForm(forms.Form):
    """Formulario para filtrar clientes"""
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Buscar por nombre, código, teléfono...'
    }))
    tipo_cliente = forms.ChoiceField(required=False, choices=[
        ('', 'Todos los tipos'),
        ('normal', 'Normal'),
        ('frecuente', 'Frecuente'),
        ('premium', 'Premium'),
    ], widget=forms.Select(attrs={'class': 'form-control'}))
    estado = forms.ChoiceField(required=False, choices=[
        ('', 'Todos'),
        ('activos', 'Activos'),
        ('inactivos', 'Inactivos'),
    ], widget=forms.Select(attrs={'class': 'form-control'}))