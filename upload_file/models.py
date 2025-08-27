from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import datetime
# import json


class PianificazioneImport(models.Model):
    """
    Represents a product planning import from Excel file
    """
    SOURCE_FILE_CHOICES = [
        ('excel', 'Excel (.xlsx/.xls)'),
        ('csv', 'CSV'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Processing'),
        ('processed', 'Processed'),
        ('error', 'Error'),
        ('exported', 'Exported'),
    ]
    
    # Import metadata
    source_file_name = models.CharField(max_length=255, verbose_name="Source file name")
    source_file_type = models.CharField(max_length=10, choices=SOURCE_FILE_CHOICES, default='excel')
    imported_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Imported by")
    imported_at = models.DateTimeField(default=timezone.now, verbose_name="Import date")
    
    # Status and statistics
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_products = models.PositiveIntegerField(default=0, verbose_name="Total products")
    total_countries = models.PositiveIntegerField(default=0, verbose_name="Total countries")
    error_message = models.TextField(blank=True, null=True, verbose_name="Error message")
    
    # Additional JSON metadata
    raw_headers = models.JSONField(default=list, verbose_name="Original headers", help_text="Original Excel file headers")
    country_mappings = models.JSONField(default=dict, verbose_name="Country mappings", help_text="Column -> countries mapping")
    
    class Meta:
        verbose_name = "Planning Import"
        verbose_name_plural = "Planning Imports"
        ordering = ['-imported_at']
    
    def __str__(self):
        return f"{self.source_file_name} ({self.status})"
    
    def get_all_products(self):
        """Get all products for this planning"""
        return self.prodotti.all().order_by('row_number')
    
    def get_products_data(self):
        """Get table data for all products"""
        products = self.get_all_products()
        
        # Build headers (reconstruct from raw_headers)
        headers = ['#'] + self.raw_headers
        
        # Build data rows
        data = []
        for idx, product in enumerate(products, 1):
            row = [str(idx)] + product.raw_data
            data.append([str(cell) for cell in row])
        
        return {
            'headers': headers,
            'data': data
        }


class Prodotto(models.Model):
    """
    Represents a single product in the planning
    """
    pianificazione = models.ForeignKey(PianificazioneImport, on_delete=models.CASCADE, related_name='prodotti')
    
    # Product identifiers
    codice_forn = models.CharField(max_length=50, verbose_name="Supplier Code")
    made_in = models.CharField(max_length=100, verbose_name="Made In")
    impianti_russia_doganale = models.CharField(max_length=100, blank=True, verbose_name="Russia Customs Plants")
    categorie = models.CharField(max_length=100, blank=True, verbose_name="Categories")
    commerce = models.CharField(max_length=100, verbose_name="Commerce")
    
    # Additional product fields
    sku = models.CharField(max_length=50, blank=True, verbose_name="SKU")
    season = models.CharField(max_length=20, blank=True, verbose_name="Season")
    article = models.CharField(max_length=100, blank=True, verbose_name="Article")
    color = models.CharField(max_length=50, blank=True, verbose_name="Color")
    size = models.CharField(max_length=20, blank=True, verbose_name="Size")
    description = models.TextField(blank=True, verbose_name="Description")
    
    # Metadata
    row_number = models.PositiveIntegerField(verbose_name="Row number in file")
    raw_data = models.JSONField(default=list, verbose_name="Original row data", help_text="All original row data")
    
    class Meta:
        verbose_name = "Product"
        verbose_name_plural = "Products"
        ordering = ['row_number']
    
    def __str__(self):
        return f"{self.codice_forn} - {self.commerce}"
    
    def clean(self):
        """Custom product validation"""
        if not self.codice_forn:
            raise ValidationError("Supplier Code is required")
        
        if not self.commerce:
            raise ValidationError("Commerce is required")


class PaesePianificazione(models.Model):
    """
    Represents the planning of a product for a specific country
    """
    prodotto = models.ForeignKey(Prodotto, on_delete=models.CASCADE, related_name='pianificazioni_paesi')
    
    # Country information
    codice_paese = models.CharField(max_length=3, verbose_name="Country Code", help_text="ISO country code (e.g.: IT, FR, DE)")
    nome_paese = models.CharField(max_length=100, blank=True, verbose_name="Country Name")
    
    # Planning dates
    data_disponibilita = models.DateField(verbose_name="Availability Date")
    data_tipo = models.CharField(max_length=20, choices=[
        ('immediate', 'Immediate (ASAP)'),
        ('scheduled', 'Scheduled'),
        ('tbd', 'To be determined'),
    ], default='scheduled', verbose_name="Date Type")
    
    # Source references
    source_column = models.PositiveIntegerField(verbose_name="Source column", help_text="Column number in Excel file")
    source_group = models.CharField(max_length=500, verbose_name="Source group", help_text="Original country group header")
    
    class Meta:
        verbose_name = "Country Planning"
        verbose_name_plural = "Country Plannings"
        unique_together = ('prodotto', 'codice_paese', 'data_disponibilita')
        ordering = ['codice_paese', 'data_disponibilita']
    
    def __str__(self):
        return f"{self.prodotto.codice_forn} - {self.codice_paese} ({self.data_disponibilita})"
    
    def clean(self):
        """Custom country planning validation with enhanced country validation"""
        if len(self.codice_paese) < 2 or len(self.codice_paese) > 3:
            raise ValidationError("Country code must be 2-3 characters")
        
        if not self.codice_paese.isalpha():
            raise ValidationError("Country code must contain only letters")
            
        # Validate against the standardized country list
        from .country_utils import CountryManager
        if not CountryManager.is_valid_country(self.codice_paese):
            raise ValidationError(f"Invalid country code: {self.codice_paese}")
    
    def get_formatted_date_for_xml(self):
        """
        Get a formatted date suitable for XML export
        """
        # from .country_utils import DateNormalizer
        if self.data_tipo == 'immediate':
            return 'ASAP'
        elif self.data_tipo == 'tbd':
            return 'TBD'
        else:
            return self.data_disponibilita.strftime('%Y-%m-%d')
    
    @classmethod
    def create_from_tranche(cls, prodotto, country_code, tranche, **kwargs):
        """
        Create a country planning record from a tranche number/name
        """
        from .country_utils import TrancheDateConverter, DateNormalizer
        
        # Convert tranche to date
        iso_date_str = TrancheDateConverter.convert_tranche_to_iso_date(str(tranche))
        availability_date = datetime.strptime(iso_date_str, '%Y-%m-%d').date()
        
        # Determine date type
        date_type = DateNormalizer.determine_date_type(str(tranche))
        
        return cls.objects.create(
            prodotto=prodotto,
            codice_paese=country_code,
            data_disponibilita=availability_date,
            data_tipo=date_type,
            **kwargs
        )


class CountryGroup(models.Model):
    """
    Represents a country group as it appears in the Excel file header
    """
    pianificazione = models.ForeignKey(PianificazioneImport, on_delete=models.CASCADE, related_name='country_groups')
    
    # Group information
    header_text = models.CharField(max_length=500, verbose_name="Header Text", help_text="Original header text (e.g.: AL-BG-BY-CY-EE-GE...)")
    column_index = models.PositiveIntegerField(verbose_name="Column Index")
    
    # Countries in the group
    countries = models.JSONField(default=list, verbose_name="Country List", help_text="List of country codes in the group")
    
    class Meta:
        verbose_name = "Country Group"
        verbose_name_plural = "Country Groups"
        unique_together = ('pianificazione', 'column_index')
        ordering = ['column_index']
    
    def __str__(self):
        return f"Col {self.column_index}: {self.header_text[:50]}..."
    
    def get_countries_display(self):
        """Returns a readable representation of countries"""
        return ", ".join(self.countries)


# Data validation utility
class PianificazioneValidator:
    """
    Utility class for validating planning data
    """
    
    VALID_COUNTRY_CODES = {
        'AL', 'AD', 'AM', 'AT', 'AZ', 'BA', 'BE', 'BG', 'BY', 'CH', 'CY', 'CZ', 
        'DE', 'DK', 'EE', 'ES', 'FI', 'FR', 'GB', 'GE', 'GR', 'HR', 'HU', 'IE', 
        'IS', 'IT', 'LI', 'LT', 'LU', 'LV', 'MC', 'MD', 'ME', 'MK', 'MT', 'NL', 
        'NO', 'PL', 'PT', 'RO', 'RS', 'RU', 'SE', 'SI', 'SK', 'SM', 'TR', 'UA', 
        'UK', 'US', 'CA', 'AU', 'NZ', 'JP', 'CN', 'HK', 'SG', 'AE', 'SA', 'QA',
        'KW', 'BH', 'OM', 'JO', 'LB', 'IL', 'EG', 'MA', 'TN', 'ZA', 'BR', 'MX',
        'AR', 'CL', 'CO', 'PE', 'UY', 'EC', 'BO', 'PY', 'VE', 'GY', 'SR', 'GF',
        'XK'  # Kosovo
    }
    
    @classmethod
    def validate_country_code(cls, code):
        """Validates a country code"""
        if not code or not isinstance(code, str):
            return False
        
        code = code.strip().upper()
        return code in cls.VALID_COUNTRY_CODES
    
    @classmethod
    def parse_country_header(cls, header_text):
        """Parses the header of a country group"""
        if not header_text or not isinstance(header_text, str):
            return []
        
        # Split by hyphens and clean
        countries = [c.strip().upper() for c in header_text.split('-') if c.strip()]
        
        # Filter only valid country codes
        valid_countries = [c for c in countries if cls.validate_country_code(c)]
        
        return valid_countries
    
    @classmethod
    def validate_date_string(cls, date_str):
        """Validates a date string"""
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
