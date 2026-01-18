from django.core.exceptions import PermissionDenied

class SuperAdminMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.rol != 'superadmin':
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class AdminMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.rol not in ['admin', 'superadmin']:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

