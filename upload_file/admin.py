# Register your models here.
from django.contrib import admin
from .models import PianificazioneImport, Prodotto, PaesePianificazione, CountryGroup


@admin.register(PianificazioneImport)
class PianificazioneImportAdmin(admin.ModelAdmin):
    list_display = ('source_file_name', 'tranche_name', 'status', 'total_products', 'total_countries', 'imported_at', 'imported_by')
    list_filter = ('status', 'source_file_type', 'imported_at')
    search_fields = ('source_file_name', 'tranche_name')
    readonly_fields = ('imported_at', 'total_products', 'total_countries')


@admin.register(CountryGroup)
class CountryGroupAdmin(admin.ModelAdmin):
    list_display = ('pianificazione', 'column_index', 'header_text_short', 'get_countries_display')
    list_filter = ('pianificazione',)
    
    def header_text_short(self, obj):
        return obj.header_text[:50] + "..." if len(obj.header_text) > 50 else obj.header_text
    header_text_short.short_description = "Header"


@admin.register(Prodotto)
class ProdottoAdmin(admin.ModelAdmin):
    list_display = ('codice_forn', 'commerce', 'made_in', 'pianificazione', 'row_number')
    list_filter = ('pianificazione', 'commerce')
    search_fields = ('codice_forn', 'commerce', 'made_in')


@admin.register(PaesePianificazione)
class PaesePianificazioneAdmin(admin.ModelAdmin):
    list_display = ('prodotto', 'codice_paese', 'data_disponibilita', 'data_tipo')
    list_filter = ('codice_paese', 'data_tipo', 'data_disponibilita')
    search_fields = ('prodotto__codice_forn', 'codice_paese')