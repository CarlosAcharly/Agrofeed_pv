from django import forms
from .models import Sucursal, ConfiguracionSucursal

class SucursalForm(forms.ModelForm):
    class Meta:
        model = Sucursal
        fields = [
            'codigo', 'nombre', 'direccion', 'telefono', 'email',
            'encargado', 'rfc', 'codigo_postal', 'ciudad', 'estado', 'pais',
            'horario_apertura', 'horario_cierre', 'dias_operacion',
            'activa', 'permite_ventas', 'permite_compras'
        ]
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: SUC001'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la sucursal'}),
            'direccion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Dirección completa'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Teléfono'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'correo@sucursal.com'}),
            'encargado': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del encargado'}),
            'rfc': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'RFC'}),
            'codigo_postal': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Código Postal'}),
            'ciudad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ciudad'}),
            'estado': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Estado'}),
            'pais': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'País'}),
            'horario_apertura': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'horario_cierre': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
            'dias_operacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Lunes a Viernes'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'permite_ventas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'permite_compras': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'codigo': 'Código de Sucursal',
            'activa': 'Sucursal Activa',
        }


class ConfiguracionSucursalForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionSucursal
        fields = [
            'stock_minimo_global', 'stock_maximo_global',
            'iva_porcentaje', 'redondeo_ventas', 'mostrar_stock',
            'max_intentos_login', 'tiempo_bloqueo',
            'generar_reporte_diario', 'hora_reporte'
        ]
        widgets = {
            'stock_minimo_global': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'stock_maximo_global': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'iva_porcentaje': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'redondeo_ventas': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'mostrar_stock': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_intentos_login': forms.NumberInput(attrs={'class': 'form-control'}),
            'tiempo_bloqueo': forms.NumberInput(attrs={'class': 'form-control'}),
            'generar_reporte_diario': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'hora_reporte': forms.TimeInput(attrs={'class': 'form-control', 'type': 'time'}),
        }
        labels = {
            'iva_porcentaje': 'Porcentaje de IVA (%)',
            'max_intentos_login': 'Máximo de intentos de login',
            'tiempo_bloqueo': 'Tiempo de bloqueo (minutos)',
        }


class TransferenciaForm(forms.Form):
    sucursal_destino = forms.ModelChoiceField(
        queryset=Sucursal.objects.filter(activa=True),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Sucursal Destino"
    )
    motivo = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label="Motivo de la Transferencia"
    )
    observaciones = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        required=False,
        label="Observaciones"
    )