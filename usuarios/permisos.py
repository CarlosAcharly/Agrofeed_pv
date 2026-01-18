from django.core.exceptions import PermissionDenied

def solo_superadmin(user):
    return user.is_authenticated and user.rol == 'superadmin'


def superadmin_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not solo_superadmin(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_o_superadmin(user):
    return (
        user.is_authenticated and
        user.rol in ['admin', 'superadmin']
    )

def admin_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not admin_o_superadmin(request.user):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _wrapped_view
