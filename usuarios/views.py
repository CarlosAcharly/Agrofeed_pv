from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Usuario  # SOLO importar Usuario
from sucursales.models import Sucursal
from .decorators import superadmin_required
from .forms import UsuarioForm

@login_required
@superadmin_required
def lista_usuarios(request):
    usuarios = Usuario.objects.all()
    return render(request, 'usuarios/lista.html', {'usuarios': usuarios})

@login_required
@superadmin_required
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)
        if form.is_valid():
            usuario = form.save(commit=False)
            password = form.cleaned_data['password']
            if password:
                usuario.set_password(password)
            usuario.save()
            messages.success(request, 'Usuario creado exitosamente')
            return redirect('usuarios_lista')
    else:
        form = UsuarioForm()
    
    return render(request, 'usuarios/form.html', {
        'form': form,
        'titulo': 'Crear Usuario'
    })

@login_required
@superadmin_required
def editar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    
    if request.method == 'POST':
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            usuario = form.save(commit=False)
            password = form.cleaned_data['password']
            if password:
                usuario.set_password(password)
            usuario.save()
            messages.success(request, 'Usuario actualizado exitosamente')
            return redirect('usuarios_lista')
    else:
        form = UsuarioForm(instance=usuario)
    
    return render(request, 'usuarios/form.html', {
        'form': form,
        'titulo': 'Editar Usuario',
        'usuario': usuario
    })

@login_required
@superadmin_required
def eliminar_usuario(request, pk):
    usuario = get_object_or_404(Usuario, pk=pk)
    if request.method == 'POST':
        usuario.delete()
        messages.success(request, 'Usuario eliminado exitosamente')
        return redirect('usuarios_lista')
    
    return render(request, 'usuarios/eliminar.html', {'usuario': usuario})