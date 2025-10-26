from users.models import AuditLog
from django.utils.deprecation import MiddlewareMixin


class AuditLoggingMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        user = request.user if request.user.is_authenticated else None
        ip = self.get_client_ip(request)
        action = f"{request.method} {request.path}"
        # Save log
        AuditLog.objects.create(user=user, action=action, ip_address=ip)
        return None

    def get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip
