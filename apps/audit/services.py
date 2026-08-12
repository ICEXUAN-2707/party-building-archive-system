"""审计日志辅助服务。

成员5负责：admin_login、admin_logout、view_student_detail。
成员7负责：upload_excel、confirm_import、rollback_import。
"""

from .models import OperationLog


def record_operation_log(
    request,
    action: str,
    target_type: str = "",
    target_id: str = "",
    description: str = "",
) -> OperationLog | None:
    """创建一条操作日志记录。

    自动从 request 中提取操作人、角色和 IP 地址。
    如果用户未登录则跳过记录。
    """
    if not request.user.is_authenticated:
        return None

    return OperationLog.objects.create(
        operator=request.user,
        operator_role=getattr(request.user, "role", ""),
        action=action,
        target_type=target_type,
        target_id=target_id,
        description=description,
        ip_address=get_client_ip(request),
    )


def get_client_ip(request) -> str:
    """从请求中提取客户端 IP 地址。

    仅当存在可信代理配置时才信任 X-Forwarded-For 头；
    当前无可信代理时直接使用 REMOTE_ADDR，防止客户端 IP 伪造。
    """
    from django.conf import settings

    trusted_proxies = getattr(settings, "TRUSTED_PROXIES", None)
    if trusted_proxies:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")
