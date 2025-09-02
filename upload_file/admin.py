# Register your models here.
from django.contrib import admin
from .models import PianificazioneImport, Prodotto, CountryGroup


@admin.register(PianificazioneImport)
class PianificazioneImportAdmin(admin.ModelAdmin):
    list_display = ['source_file_name', 'imported_by', 'imported_at', 'status', 'total_products', 'total_countries']
    list_filter = ['status', 'imported_at', 'imported_by']
    search_fields = ['source_file_name', 'imported_by__username']
    readonly_fields = ['imported_at', 'csv_file_path', 'processed_file_path']
    ordering = ['-imported_at']


@admin.register(Prodotto)
class ProdottoAdmin(admin.ModelAdmin):
    list_display = ['chiave_articolo', 'sku', 'descrizione', 'pianificazione', 'row_number']
    list_filter = ['pianificazione', 'made_in', 'categorie']
    search_fields = ['chiave_articolo', 'sku', 'descrizione', 'articolo']
    readonly_fields = ['row_number']
    ordering = ['pianificazione', 'row_number']


@admin.register(CountryGroup)
class CountryGroupAdmin(admin.ModelAdmin):
    list_display = ['pianificazione', 'column_index', 'header_text', 'countries_count']
    list_filter = ['pianificazione']
    search_fields = ['header_text', 'pianificazione__source_file_name']
    ordering = ['pianificazione', 'column_index']
    
    def countries_count(self, obj):
        return len(obj.countries)
    countries_count.short_description = 'Numero Paesi'