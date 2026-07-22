from django.views.generic import TemplateView

from apps.accounts.mixins import DataAdminRequiredMixin


class UploadView(DataAdminRequiredMixin, TemplateView):
    template_name = "imports/upload.html"


class PreviewView(DataAdminRequiredMixin, TemplateView):
    template_name = "imports/preview.html"


class HistoryView(DataAdminRequiredMixin, TemplateView):
    template_name = "imports/history.html"
