from django import forms


class FileUploadForm(forms.Form):
    """
    Form for Excel planning file upload
    """
    file = forms.FileField(
        label='Select Excel file',
        help_text='Upload an Excel file (.xlsx, .xls) containing product planning',    
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls',
            'required': True
        })
    )
    
    def clean_file(self):
        """
        Validation of uploaded file
        """
        uploaded_file = self.cleaned_data.get('file')
        
        if not uploaded_file:
            raise forms.ValidationError('No file selected.')
        
        # Check extension
        if not uploaded_file.name.endswith(('.xlsx', '.xls')):
            raise forms.ValidationError('Only Excel files (.xlsx, .xls) are supported.')
        
        # Check file size (max 50MB)
        if uploaded_file.size > 50 * 1024 * 1024:
            raise forms.ValidationError('File is too large. Maximum size: 50MB.')
        
        return uploaded_file
