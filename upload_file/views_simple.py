"""
Views semplificata per Tranche Automation
Solo 3 pagine: Login -> Upload -> Visualizzazione Dati
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
# from django.core.paginator import Paginator
from django.db import models
from django.conf import settings
import os
import logging

from .models import PianificazioneImport  # , Prodotto
from .forms import FileUploadForm
from .django_country_processor import DjangoCountryProcessor

logger = logging.getLogger(__name__)


@login_required
def home(request):
    """
    Pagina principale di upload semplificata
    """
    if request.method == 'POST':
        return upload_file(request)
    
    form = FileUploadForm()
    
    context = {
        'upload_form': form,
    }
    
    return render(request, 'upload_simple_clean.html', context)


@login_required
def upload_file(request):
    """
    Gestisce l'upload e processing dei file Excel
    """
    if request.method != 'POST':
        return redirect('home')
    
    form = FileUploadForm(request.POST, request.FILES)
    
    if not form.is_valid():
        logger.warning(f"Form non valido per utente {request.user.username}: {form.errors}")
        messages.error(request, 'File non valido. Assicurati di caricare un file Excel (.xlsx)')
        return redirect('home')
    
    try:
        uploaded_file = form.cleaned_data['file']
        
        # Il file è già validato dal form Django
        logger.info(f"Processing file: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
        # Crea record di import
        import_record = PianificazioneImport.objects.create(
            source_file_name=uploaded_file.name,
            imported_by=request.user,
            status='pending'
        )
        
        # Salva il file temporaneamente
        temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_uploads')
        os.makedirs(temp_dir, exist_ok=True)
        
        temp_file_path = os.path.join(temp_dir, f"upload_{import_record.id}_{uploaded_file.name}")
        
        with open(temp_file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Processa il file con il nuovo processore
        try:
            processor = DjangoCountryProcessor()
            stats = processor.process_excel_to_database(temp_file_path, import_record)
            
            # Pulizia file temporaneo
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            messages.success(
                request, 
                f'File processato con successo! '
                f'Prodotti: {stats["products_created"]}, '
                f'Record paesi: {stats["country_records_created"]}'
            )
            
            logger.info(f"Upload completato con successo! Redirect a data_view per import {import_record.id}")
            return redirect('data_view', import_id=import_record.id)
            
        except Exception as e:
            logger.error(f"Errore nel processing del file: {str(e)}")
            
            # Pulizia in caso di errore
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)
            
            import_record.status = 'error'
            import_record.error_message = str(e)
            import_record.save()
            
            messages.error(request, f'Errore nel processing del file: {str(e)}')
            return redirect('home')
    
    except Exception as e:
        logger.error(f"Errore generale nell'upload: {str(e)}")
        messages.error(request, f'Errore nell\'upload: {str(e)}')
        return redirect('home')


@login_required
def data_view(request, import_id):
    """
    Visualizzazione dati completa senza paginazione
    """
    pianificazione = get_object_or_404(PianificazioneImport, id=import_id)
    prodotti = pianificazione.get_all_products().prefetch_related('paesi_pianificazione')
    
    # Solo filtro di ricerca testuale (senza filtro paese per evitare errori SQLite)
    search = request.GET.get('search', '')
    
    if search:
        prodotti = prodotti.filter(
            models.Q(chiave_articolo__icontains=search) |
            models.Q(descrizione__icontains=search) |
            models.Q(sku__icontains=search) |
            models.Q(articolo__icontains=search) |
            models.Q(fornitore__icontains=search) |
            models.Q(colore__icontains=search)
        )
    
    # Lista di tutti i paesi per le colonne
    country_list = [
        'AL', 'AM', 'AT', 'AZ', 'BA', 'BE', 'BG', 'BH', 'BR', 'BY', 'CH', 'CN', 'CO', 'CY', 'CZ',
        'DE', 'DK', 'EE', 'ES', 'FL', 'FR', 'GB', 'GE', 'GR', 'HK', 'HR', 'HU', 'IE', 'IL',
        'IT', 'JO', 'JP', 'KW', 'KZ', 'LB', 'LT', 'LU', 'LV', 'MA', 'MD', 'MK', 'MO', 'MT',
        'MX', 'NL', 'PL', 'PT', 'QA', 'RO', 'RS', 'RU', 'SA', 'SE', 'SI', 'SK', 'TN', 'TR',
        'TW', 'UA', 'UK', 'US', 'UZ', 'XK'
    ]
    
    context = {
        'pianificazione': pianificazione,
        'prodotti': prodotti,
        'search': search,
        'total_products': prodotti.count(),
        'country_list': country_list,
    }
    
    return render(request, 'data_table_correct.html', context)
