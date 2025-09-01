from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime
import json


class PianificazioneImport(models.Model):
    """
    Represents a planning import from Excel file
    """
    STATUS_CHOICES = [
        ('pending', 'Processing'),
        ('processed', 'Processed'),
        ('error', 'Error'),
    ]
    
    # Import metadata
    source_file_name = models.CharField(max_length=255, verbose_name="Source file name")
    imported_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Imported by")
    imported_at = models.DateTimeField(default=timezone.now, verbose_name="Import date")
    
    # Status and statistics
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_products = models.PositiveIntegerField(default=0, verbose_name="Total products")
    total_countries = models.PositiveIntegerField(default=0, verbose_name="Total countries")
    error_message = models.TextField(blank=True, null=True, verbose_name="Error message")
    
    # Generated files
    csv_file_path = models.CharField(max_length=500, blank=True, verbose_name="CSV file path")
    processed_file_path = models.CharField(max_length=500, blank=True, verbose_name="Processed file path")
    
    class Meta:
        verbose_name = "Planning Import"
        verbose_name_plural = "Planning Imports"
        ordering = ['-imported_at']
    
    def __str__(self):
        return f"{self.source_file_name} ({self.status})"
    
    def get_all_products(self):
        """Get all products for this planning"""
        return self.prodotti.all().order_by('row_number')


class Prodotto(models.Model):
    """
    Represents a single product in the planning
    """
    pianificazione = models.ForeignKey(PianificazioneImport, on_delete=models.CASCADE, related_name='prodotti')
    
    # Identificatori prodotto
    chiave_articolo = models.CharField(max_length=100, verbose_name="Chiave Articolo", default='')
    concatena_magazzino = models.CharField(max_length=100, verbose_name="Concatena Magazzino", default='')
    serie = models.CharField(max_length=100, verbose_name="Serie", default='')
    merceologia = models.CharField(max_length=100, verbose_name="Merceologia", default='')
    n_tranche = models.CharField(max_length=50, verbose_name="N. Tranche", default='')
    stagione = models.CharField(max_length=50, verbose_name="Stagione", default='')
    sku = models.CharField(max_length=100, verbose_name="SKU", default='')
    articolo = models.CharField(max_length=100, verbose_name="Articolo", default='')
    colore = models.CharField(max_length=50, verbose_name="Colore", default='')
    taglia = models.CharField(max_length=20, verbose_name="Taglia", default='')
    descrizione = models.TextField(verbose_name="Descrizione", default='')
    
    # Date principali
    data_inizio_consegna = models.CharField(max_length=50, blank=True, verbose_name="Data Inizio Consegna")
    data_spedizione_reale = models.CharField(max_length=50, blank=True, verbose_name="Data Spedizione Reale")
    data_consegna_fornitore = models.CharField(max_length=50, blank=True, verbose_name="Data Consegna Fornitore")
    
    # Informazioni fornitore
    impianti_per = models.CharField(max_length=200, blank=True, verbose_name="Impianti Per")
    note_ufficio = models.CharField(max_length=500, blank=True, verbose_name="Note Ufficio")
    fornitore = models.CharField(max_length=200, blank=True, verbose_name="Fornitore")
    codice_forn = models.CharField(max_length=50, blank=True, verbose_name="Codice Forn")
    made_in = models.CharField(max_length=100, blank=True, verbose_name="Made In")
    
    # Stock e disponibilità
    impianti_russia = models.CharField(max_length=200, blank=True, verbose_name="Impianti Russia")
    ocli_mondo_russia = models.CharField(max_length=200, blank=True, verbose_name="OCLI Mondo+Russia")
    anticipi_milano = models.CharField(max_length=200, blank=True, verbose_name="Anticipi Milano")
    impianto_russia_startup = models.CharField(max_length=200, blank=True, verbose_name="Impianto Russia Startup")
    stock_l = models.CharField(max_length=50, blank=True, verbose_name="Stock L")
    stock_cq = models.CharField(max_length=50, blank=True, verbose_name="Stock CQ")
    stock_b = models.CharField(max_length=50, blank=True, verbose_name="Stock B")
    ocli = models.CharField(max_length=50, blank=True, verbose_name="OCLI")
    esistenza = models.CharField(max_length=50, blank=True, verbose_name="Esistenza")
    stock_l_cq_ocli = models.CharField(max_length=50, blank=True, verbose_name="Stock L+CQ-OCLI")
    x_per_pv_foto = models.CharField(max_length=50, blank=True, verbose_name="X per PV Foto")
    stock_cq_2 = models.CharField(max_length=50, blank=True, verbose_name="Stock CQ 2")
    
    # Categorie e visibilità
    categorie = models.CharField(max_length=200, blank=True, verbose_name="Categorie")
    note_categorie = models.CharField(max_length=500, blank=True, verbose_name="Note Categorie")
    ecommerce_visibility = models.CharField(max_length=200, blank=True, verbose_name="E-commerce Visibility")
    
    # Informazioni paesi (JSON)
    paesi_disponibili = models.JSONField(default=list, verbose_name="Paesi Disponibili")
    paesi_aap = models.JSONField(default=list, verbose_name="Paesi AAP")
    paesi_con_date = models.JSONField(default=list, verbose_name="Paesi con Date")
    date_paesi = models.JSONField(default=dict, verbose_name="Date Paesi")
    
    # Metadati
    row_number = models.PositiveIntegerField(verbose_name="Numero riga nel file")
    
    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['row_number']
    
    def __str__(self):
        return f"{self.chiave_articolo} - {self.descrizione[:50]}"
    
    def get_countries_with_dates(self):
        """Get countries with their specific dates"""
        return self.date_paesi
    
    def get_countries_aap(self):
        """Get countries with AAP availability"""
        return self.paesi_aap
    
    def get_all_available_countries(self):
        """Get all available countries"""
        return self.paesi_disponibili
    
    def get_country_date(self, country_code):
        """Get date for a specific country"""
        return self.date_paesi.get(country_code.upper())
    
    def is_country_aap(self, country_code):
        """Check if a country has AAP availability"""
        return country_code.upper() in [c.upper() for c in self.paesi_aap]
    
    def is_country_available(self, country_code):
        """Check if a country is available"""
        return country_code.upper() in [c.upper() for c in self.paesi_disponibili]


class CountryGroup(models.Model):
    """
    Represents a country group as it appears in Excel file header
    """
    pianificazione = models.ForeignKey(PianificazioneImport, on_delete=models.CASCADE, related_name='country_groups')
    
    # Group information
    header_text = models.CharField(max_length=500, verbose_name="Header Text", help_text="Original header text (e.g: AL-BG-BY-CY-EE-GE...)")
    column_index = models.PositiveIntegerField(verbose_name="Column Index")
    
    # Countries in group
    countries = models.JSONField(default=list, verbose_name="Countries List", help_text="List of country codes in group")
    
    class Meta:
        verbose_name = "Country Group"
        verbose_name_plural = "Country Groups"


class PaesePianificazione(models.Model):
    """
    Represents planning for a single country of a product
    """
    TIPO_DATA_CHOICES = [
        ('as_available', 'As Available (AAP)'),
        ('data_specifica', 'Specific Date'),
        ('to_be_determined', 'To Be Determined (TBD)'),
        ('non_specificato', 'Not Specified'),
        ('altro', 'Other'),
    ]
    
    # Relations
    prodotto = models.ForeignKey(
        Prodotto, 
        on_delete=models.CASCADE, 
        related_name='paesi_pianificazione',
        verbose_name="Product"
    )
    
    # Country information
    codice_paese = models.CharField(max_length=3, verbose_name="Country Code")
    data_disponibilita = models.DateField(null=True, blank=True, verbose_name="Availability Date")
    data_tipo = models.CharField(
        max_length=20, 
        choices=TIPO_DATA_CHOICES, 
        default='non_specificato',
        verbose_name="Date Type"
    )
    
    # Source metadata
    source_column = models.CharField(max_length=200, blank=True, verbose_name="Source Column")
    source_group = models.CharField(max_length=200, blank=True, verbose_name="Source Group")
    availability_value = models.CharField(max_length=100, blank=True, verbose_name="Availability Value")
    is_available = models.BooleanField(default=False, verbose_name="Is Available")
    
    # Metadati
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created at")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated at")
    
    class Meta:
        verbose_name = "Country Planning"
        verbose_name_plural = "Country Planning"
        unique_together = ['prodotto', 'codice_paese']
        ordering = ['codice_paese']
        indexes = [
            models.Index(fields=['codice_paese', 'data_disponibilita']),
            models.Index(fields=['prodotto', 'is_available']),
            models.Index(fields=['data_tipo']),
        ]
    
    def __str__(self):
        return f"{self.prodotto.sku} - {self.codice_paese} ({self.get_data_tipo_display()})"
    
    @property
    def disponibilita_formattata(self):
        """Returns availability in readable format"""
        if self.data_tipo == 'as_available':
            return 'As Available'
        elif self.data_tipo == 'data_specifica' and self.data_disponibilita:
            return self.data_disponibilita.strftime('%d/%m/%Y')
        elif self.data_tipo == 'to_be_determined':
            return 'To Be Determined'
        else:
            return self.availability_value or 'Not specified'


# Data validation utility
class PianificazioneValidator:
    """
    Utility class for validating planning data
    """
    
    VALID_COUNTRY_CODES = {
        'AL', 'AM', 'AT', 'AZ', 'BA', 'BE', 'BG', 'BH', 'BR', 'BY', 'CH', 'CN', 'CO', 'CY', 'CZ', 
        'DE', 'DK', 'EE', 'ES', 'FL', 'FR', 'GB', 'GE', 'GR', 'HK', 'HR', 'HU', 'IE', 'IL', 
        'IT', 'JO', 'JP', 'KW', 'KZ', 'LB', 'LT', 'LU', 'LV', 'MA', 'MD', 'MK', 'MO', 'MT', 
        'MX', 'NL', 'PL', 'PT', 'QA', 'RO', 'RS', 'RU', 'SA', 'SE', 'SI', 'SK', 'TN', 'TR', 
        'TW', 'UA', 'UK', 'US', 'UZ', 'XK'
    }
    
    @classmethod
    def validate_country_code(cls, code):
        """Validate a country code"""
        if not code or not isinstance(code, str):
            return False
        
        code = code.strip().upper()
        return code in cls.VALID_COUNTRY_CODES
    
    @classmethod
    def parse_country_header(cls, header_text):
        """Parse header of a country group"""
        if not header_text or not isinstance(header_text, str):
            return []
        
        # Split by dashes and clean
        countries = [c.strip().upper() for c in header_text.split('-') if c.strip()]
        
        # Filter only valid country codes
        valid_countries = [c for c in countries if cls.validate_country_code(c)]
        
        return valid_countries
    
    @classmethod
    def validate_date_string(cls, date_str):
        """Validate a date string"""
        if not date_str:
            return False
        
        try:
            from datetime import datetime
            # Try various formats
            formats = ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d %H:%M:%S']
            
            for fmt in formats:
                try:
                    datetime.strptime(str(date_str).strip(), fmt)
                    return True
                except ValueError:
                    continue
            
            # Check if it's 'AAP' or similar
            if str(date_str).strip().upper() in ['AAP', 'ASAP', 'TBD']:
                return True
                
            return False
        except Exception:
            return False
