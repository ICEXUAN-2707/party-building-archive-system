from django.urls import path

from apps.imports import views

app_name = "imports"

urlpatterns = [
    path("upload/", views.upload, name="upload"),
    path("<int:batch_id>/preview/", views.preview, name="preview"),
    path("<int:batch_id>/confirm/", views.confirm, name="confirm"),
    path("<int:batch_id>/rollback/", views.rollback, name="rollback"),
    path("history/", views.history, name="history"),
    path("history/<int:batch_id>/", views.batch_detail, name="batch_detail"),
    path("<int:batch_id>/file/", views.download_file, name="download_file"),
]
