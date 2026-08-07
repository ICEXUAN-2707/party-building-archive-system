"""Root URL configuration."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path("admin/", admin.site.urls),
    # 新增 namespace="accounts"
    path("accounts/", include("apps.accounts.urls", namespace="accounts")),
    # students 同步加上命名空间（之前CI用到students:xxx路由）
    path("students/", include("apps.students.urls", namespace="students")),
    path("imports/", include("apps.imports.urls")),
]

handler403 = "config.views.permission_denied"
handler404 = "config.views.page_not_found"
handler500 = "config.views.server_error"

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
