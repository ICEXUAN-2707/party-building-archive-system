from django import forms


class StudentLoginForm(forms.Form):
    name = forms.CharField(
        label="姓名",
        max_length=64,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入姓名"}),
    )
    student_number = forms.CharField(
        label="学号",
        max_length=32,
        required=True,
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "请输入学号"}),
    )

    def clean_name(self) -> str:
        return self.cleaned_data["name"].strip()

    def clean_student_number(self) -> str:
        return self.cleaned_data["student_number"].strip()
