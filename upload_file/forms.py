from django import forms


class FileUploadForm(forms.Form):
    """
    Form per l'upload di file Excel di pianificazione
    """
    file = forms.FileField(
        label='Seleziona file Excel',
        help_text='Carica un file Excel (.xlsx, .xls) contenente la pianificazione prodotti',
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.xlsx,.xls',
            'required': True
        })
    )
    
    def clean_file(self):
        """
        Validazione del file caricato
        """
        uploaded_file = self.cleaned_data.get('file')
        
        if not uploaded_file:
            raise forms.ValidationError('Nessun file selezionato.')
        
        # Verifica estensione
        if not uploaded_file.name.endswith(('.xlsx', '.xls')):
            raise forms.ValidationError('Solo file Excel (.xlsx, .xls) sono supportati.')
        
        # Verifica dimensione (max 50MB)
        if uploaded_file.size > 50 * 1024 * 1024:
            raise forms.ValidationError('Il file è troppo grande. Dimensione massima: 50MB.')
        
        return uploaded_file
