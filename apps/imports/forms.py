from pathlib import PurePath

from django import forms


MAX_EXCEL_UPLOAD_SIZE = 10 * 1024 * 1024


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(label="Excel文件")

    def clean_excel_file(self):
        uploaded_file = self.cleaned_data["excel_file"]
        filename = str(getattr(uploaded_file, "name", ""))
        suffix = PurePath(filename.replace("\\", "/")).suffix.lower()

        if suffix != ".xlsx":
            raise forms.ValidationError("只允许上传.xlsx格式的Excel文件。")
        if uploaded_file.size == 0:
            raise forms.ValidationError("不能上传空文件。")
        if uploaded_file.size > MAX_EXCEL_UPLOAD_SIZE:
            raise forms.ValidationError("Excel文件不能超过10 MiB。")

        return uploaded_file
