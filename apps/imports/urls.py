from django.urls import path
from django.views.generic import TemplateView

app_name = "imports"

urlpatterns = [
    path("upload/", TemplateView.as_view(template_name="imports/upload.html"), name="upload"),
    path("preview/", TemplateView.as_view(template_name="imports/preview.html"), name="preview"),
    path("history/", TemplateView.as_view(template_name="imports/history.html"), name="history"),
]
