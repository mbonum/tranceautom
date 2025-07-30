from django import forms


class ExcelUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="Excel File",
        widget=forms.FileInput(attrs={"accept": ".xlsx,.xls", "class": "form-control"}),
    )

    def clean_excel_file(self):
        file = self.cleaned_data["excel_file"]
        if file:
            if not file.name.lower().endswith((".xlsx", ".xls")):
                raise forms.ValidationError(
                    "Please upload an Excel file (.xlsx or .xls)"
                )
        return file
