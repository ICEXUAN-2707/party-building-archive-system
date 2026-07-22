from django.urls import path

from .views import HistoryView, PreviewView, UploadView

app_name = "imports"

urlpatterns = [
    path("upload/", UploadView.as_view(), name="upload"),
    path("preview/", PreviewView.as_view(), name="preview"),
    path("history/", HistoryView.as_view(), name="history"),
]
