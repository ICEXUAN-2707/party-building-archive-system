"""生产 SQLite 连接初始化。

WAL 是数据库级持久设置；busy_timeout 仍需对每条新连接设置。
"""

from django.conf import settings
from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created, dispatch_uid="party_archive_sqlite_pragmas")
def configure_sqlite_connection(sender, connection, **kwargs) -> None:
    if not settings.PRODUCTION or connection.vendor != "sqlite":
        return

    timeout_ms = int(settings.DATABASES[connection.alias]["OPTIONS"]["timeout"] * 1000)
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute(f"PRAGMA busy_timeout={timeout_ms}")
        cursor.execute("PRAGMA synchronous=NORMAL")
