"""
Refactored views for Tranche Automation
Focused on API endpoints and user interface, with business logic delegated to specialized modules
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db import transaction, models
from django.conf import settings
import os
import json
import logging

from .models import PianificazioneImport, Prodotto, CountryGroup, PaesePianificazione
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
        logger.info(f"📁 Processing file: {uploaded_file.name} ({uploaded_file.size} bytes)")
        
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
            
            logger.info(f"✅ Upload completato con successo! Redirect a planning_details per import {import_record.id}")
            return redirect('planning_details', import_id=import_record.id)
            
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





# View planning_list rimossa - non necessaria per il flusso semplificato


# Funzioni legacy rimosse - ora usiamo DjangoCountryProcessor


@login_required
def planning_details(request, import_id):
    """
    Mostra i dettagli di una pianificazione specifica
    """
    pianificazione = get_object_or_404(PianificazioneImport, id=import_id)
    prodotti = pianificazione.get_all_products()
    
    # Filtri
    search = request.GET.get('search', '')
    country_filter = request.GET.get('country', '')
    
    if search:
        prodotti = prodotti.filter(
            models.Q(chiave_articolo__icontains=search) |
            models.Q(descrizione__icontains=search) |
            models.Q(sku__icontains=search)
        )
    
    if country_filter:
        prodotti = prodotti.filter(paesi_disponibili__contains=[country_filter.upper()])
    
    # Paginazione
    paginator = Paginator(prodotti, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Statistiche
    total_countries = len(set([p for prod in prodotti for p in prod.paesi_disponibili]))
    products_with_dates = sum(1 for p in prodotti if p.paesi_con_date)
    products_aap = sum(1 for p in prodotti if p.paesi_aap)
    
    context = {
        'pianificazione': pianificazione,
        'page_obj': page_obj,
        'search': search,
        'country_filter': country_filter,
        'stats': {
            'total_products': prodotti.count(),
            'total_countries': total_countries,
            'products_with_dates': products_with_dates,
            'products_aap': products_aap
        }
    }
    
    return render(request, 'data_view.html', context)


@login_required
def product_detail(request, import_id, product_id):
    """
    Mostra i dettagli di un prodotto specifico
    """
    pianificazione = get_object_or_404(PianificazioneImport, id=import_id)
    prodotto = get_object_or_404(Prodotto, id=product_id, pianificazione=pianificazione)
    
    # Organizza i dati dei paesi
    countries_data = {
        'with_dates': [],
        'aap': [],
        'all_available': []
    }
    
    # Paesi con date specifiche
    for country, date in prodotto.date_paesi.items():
        countries_data['with_dates'].append({
            'code': country,
            'date': date
        })
    
    # Paesi AAP
    for country in prodotto.paesi_aap:
        countries_data['aap'].append({
            'code': country,
            'date': 'AAP'
        })
    
    # Tutti i paesi disponibili
    for country in prodotto.paesi_disponibili:
        if country not in [c['code'] for c in countries_data['with_dates'] + countries_data['aap']]:
            countries_data['all_available'].append({
                'code': country,
                'date': 'Disponibile'
            })
    
    context = {
        'pianificazione': pianificazione,
        'prodotto': prodotto,
        'countries_data': countries_data
    }
    
    return render(request, 'upload_file/product_detail.html', context)


@login_required
def download_processed_file(request, import_id):
    """
    Scarica il file processato
    """
    pianificazione = get_object_or_404(PianificazioneImport, id=import_id)
    
    if not pianificazione.processed_file_path or not os.path.exists(pianificazione.processed_file_path):
        messages.error(request, 'File processato non trovato.')
        return redirect('planning_details', import_id=import_id)
    
    # Prepara il file per il download
    with open(pianificazione.processed_file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{pianificazione.source_file_name}_processed.csv"'
        return response


@login_required
def api_products(request, import_id):
    """
    API per ottenere i prodotti di una pianificazione
    """
    pianificazione = get_object_or_404(PianificazioneImport, id=import_id)
    prodotti = pianificazione.get_all_products()
    
    # Filtri
    search = request.GET.get('search', '')
    if search:
        prodotti = prodotti.filter(
            models.Q(chiave_articolo__icontains=search) |
            models.Q(descrizione__icontains=search)
        )
    
    # Converti in JSON
    data = []
    for prodotto in prodotti:
        data.append({
            'id': prodotto.id,
            'chiave_articolo': prodotto.chiave_articolo,
            'sku': prodotto.sku,
            'descrizione': prodotto.descrizione,
            'paesi_disponibili': prodotto.paesi_disponibili,
            'paesi_con_date': len(prodotto.paesi_con_date),
            'paesi_aap': len(prodotto.paesi_aap)
        })
    
    return JsonResponse({'products': data})


@login_required
def delete_planning(request, import_id):
    """
    Elimina una pianificazione
    """
    pianificazione = get_object_or_404(PianificazioneImport, id=import_id)
    
    if request.method == 'POST':
        try:
            # Elimina i file associati
            if pianificazione.csv_file_path and os.path.exists(pianificazione.csv_file_path):
                os.remove(pianificazione.csv_file_path)
            
            if pianificazione.processed_file_path and os.path.exists(pianificazione.processed_file_path):
                os.remove(pianificazione.processed_file_path)
            
            # Elimina il record
            pianificazione.delete()
            
            messages.success(request, 'Pianificazione eliminata con successo.')
            return redirect('home')
            
        except Exception as e:
            messages.error(request, f'Errore nell\'eliminazione: {str(e)}')
            return redirect('planning_details', import_id=import_id)
    
    context = {
        'pianificazione': pianificazione
    }
    
    return render(request, 'upload_file/delete_planning.html', context)