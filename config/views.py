"""Error page handlers."""

from django.http import HttpRequest, HttpResponse
from django.db import connection
from django.shortcuts import render


def permission_denied(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "403.html", status=403)


def page_not_found(request: HttpRequest, exception: Exception) -> HttpResponse:
    return render(request, "404.html", status=404)


def server_error(request: HttpRequest) -> HttpResponse:
    return render(request, "500.html", status=500)


def readiness(request: HttpRequest) -> HttpResponse:
    """Return a deliberately small readiness signal for the reverse proxy."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            if cursor.fetchone() != (1,):
                raise RuntimeError("unexpected database probe result")
    except Exception:
        return HttpResponse("unavailable\n", status=503, content_type="text/plain")
    return HttpResponse("ok\n", content_type="text/plain")
