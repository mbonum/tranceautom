"""
API Views for Modern Product Management
Handles AJAX requests for editing and saving products
"""

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.db import transaction
from datetime import datetime
import json
import logging

from .models import Prodotto, PaesePianificazione

logger = logging.getLogger(__name__)


@login_required
@require_http_methods(["POST"])
def save_products(request):
    """
    API endpoint to save multiple products with their modifications
    """
    try:
        data = json.loads(request.body)
        products_data = data.get('products', [])
        
        if not products_data:
            return JsonResponse({'error': 'No products data provided'}, status=400)
        
        saved_products = []
        errors = []
        
        with transaction.atomic():
            for product_data in products_data:
                try:
                    product_id = product_data.get('id')
                    if not product_id:
                        errors.append({'error': 'Product ID missing'})
                        continue
                    
                    product = get_object_or_404(Prodotto, id=product_id)
                    
                    # Update basic product fields
                    updated_fields = []
                    for field_name, value in product_data.items():
                        if field_name in ['id', 'countries']:
                            continue
                        
                        if hasattr(product, field_name):
                            old_value = getattr(product, field_name)
                            if old_value != value:
                                setattr(product, field_name, value)
                                updated_fields.append(field_name)
                    
                    # Save product if any field was updated
                    if updated_fields:
                        product.save(update_fields=updated_fields)
                        logger.info(f"Updated product {product_id} fields: {updated_fields}")
                    
                    # Update country planning if provided
                    if 'countries' in product_data:
                        update_country_planning(product, product_data['countries'])
                    
                    saved_products.append({
                        'id': product_id,
                        'updated_fields': updated_fields,
                        'success': True
                    })
                    
                except Exception as e:
                    logger.error(f"Error updating product {product_data.get('id', 'unknown')}: {str(e)}")
                    errors.append({
                        'id': product_data.get('id'),
                        'error': str(e)
                    })
        
        response_data = {
            'saved_products': saved_products,
            'total_saved': len(saved_products),
            'errors': errors
        }
        
        if errors:
            response_data['status'] = 'partial_success'
        else:
            response_data['status'] = 'success'
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error in save_products: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def update_country_planning(product, countries_data):
    """
    Update country planning for a product
    """
    for country_data in countries_data:
        country_code = country_data.get('code', '').upper()
        country_type = country_data.get('type', 'not_available')
        country_date = country_data.get('date')
        
        if not country_code:
            continue
        
        try:
            # Get or create country planning record
            paese, created = PaesePianificazione.objects.get_or_create(
                prodotto=product,
                codice_paese=country_code,
                defaults={
                    'data_tipo': 'non_specificato',
                    'is_available': False
                }
            )
            
            # Update based on type
            if country_type == 'not_available':
                paese.is_available = False
                paese.data_tipo = 'non_specificato'
                paese.data_disponibilita = None
                paese.availability_value = ''
                
            elif country_type == 'available':
                paese.is_available = True
                paese.data_tipo = 'non_specificato'
                paese.data_disponibilita = None
                paese.availability_value = 'Available'
                
            elif country_type == 'as_available':
                paese.is_available = True
                paese.data_tipo = 'as_available'
                paese.data_disponibilita = None
                paese.availability_value = 'AAP'
                
            elif country_type == 'data_specifica' and country_date:
                paese.is_available = True
                paese.data_tipo = 'data_specifica'
                
                # Parse date
                try:
                    if isinstance(country_date, str):
                        paese.data_disponibilita = datetime.strptime(country_date, '%Y-%m-%d').date()
                    else:
                        paese.data_disponibilita = country_date
                except ValueError:
                    logger.warning(f"Invalid date format for country {country_code}: {country_date}")
                    continue
                
                paese.availability_value = paese.data_disponibilita.strftime('%Y-%m-%d')
            
            paese.save()
            
            logger.info(f"Updated country planning for {product.id}-{country_code}: {country_type}")
            
        except Exception as e:
            logger.error(f"Error updating country {country_code} for product {product.id}: {str(e)}")


@login_required
@require_http_methods(["GET"])
def get_product_details(request, product_id):
    """
    API endpoint to get detailed product information
    """
    try:
        product = get_object_or_404(Prodotto, id=product_id)
        
        # Get country planning
        countries = []
        for paese in product.paesi_pianificazione.all():
            countries.append({
                'code': paese.codice_paese,
                'type': paese.data_tipo,
                'date': paese.data_disponibilita.isoformat() if paese.data_disponibilita else None,
                'is_available': paese.is_available,
                'value': paese.availability_value
            })
        
        product_data = {
            'id': product.id,
            'chiave_articolo': product.chiave_articolo,
            'sku': product.sku,
            'articolo': product.articolo,
            'colore': product.colore,
            'taglia': product.taglia,
            'descrizione': product.descrizione,
            'serie': product.serie,
            'merceologia': product.merceologia,
            'n_tranche': product.n_tranche,
            'stagione': product.stagione,
            'categorie': product.categorie,
            'fornitore': product.fornitore,
            'codice_forn': product.codice_forn,
            'made_in': product.made_in,
            'impianti_per': product.impianti_per,
            'note_ufficio': product.note_ufficio,
            'data_inizio_consegna': product.data_inizio_consegna,
            'data_spedizione_reale': product.data_spedizione_reale,
            'data_consegna_fornitore': product.data_consegna_fornitore,
            'ecommerce_visibility': product.ecommerce_visibility,
            'countries': countries
        }
        
        return JsonResponse({
            'status': 'success',
            'product': product_data
        })
        
    except Exception as e:
        logger.error(f"Error getting product details for {product_id}: {str(e)}")
        return JsonResponse({'error': 'Product not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def bulk_update_products(request):
    """
    API endpoint for bulk updating multiple products
    """
    try:
        data = json.loads(request.body)
        product_ids = data.get('product_ids', [])
        updates = data.get('updates', {})
        
        if not product_ids or not updates:
            return JsonResponse({'error': 'Product IDs and updates required'}, status=400)
        
        updated_count = 0
        errors = []
        
        with transaction.atomic():
            products = Prodotto.objects.filter(id__in=product_ids)
            
            for product in products:
                try:
                    updated_fields = []
                    
                    for field_name, value in updates.items():
                        if hasattr(product, field_name) and value is not None and value != '':
                            setattr(product, field_name, value)
                            updated_fields.append(field_name)
                    
                    if updated_fields:
                        product.save(update_fields=updated_fields)
                        updated_count += 1
                        
                except Exception as e:
                    errors.append({
                        'id': product.id,
                        'error': str(e)
                    })
        
        return JsonResponse({
            'status': 'success',
            'updated_count': updated_count,
            'total_requested': len(product_ids),
            'errors': errors
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error in bulk update: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def validate_product_data(request):
    """
    API endpoint to validate product data before saving
    """
    try:
        data = json.loads(request.body)
        
        validation_errors = []
        warnings = []
        
        # Validate required fields
        required_fields = ['chiave_articolo', 'sku']
        for field in required_fields:
            if not data.get(field):
                validation_errors.append(f"{field} is required")
        
        # Validate date formats
        date_fields = ['data_inizio_consegna', 'data_spedizione_reale', 'data_consegna_fornitore']
        for field in date_fields:
            if data.get(field):
                try:
                    datetime.strptime(data[field], '%Y-%m-%d')
                except ValueError:
                    validation_errors.append(f"Invalid date format for {field}")
        
        # Check for duplicates
        chiave_articolo = data.get('chiave_articolo')
        if chiave_articolo:
            existing = Prodotto.objects.filter(
                chiave_articolo=chiave_articolo
            ).exclude(id=data.get('id'))
            
            if existing.exists():
                warnings.append(f"Another product with key '{chiave_articolo}' already exists")
        
        return JsonResponse({
            'is_valid': len(validation_errors) == 0,
            'errors': validation_errors,
            'warnings': warnings
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON data'}, status=400)
    except Exception as e:
        logger.error(f"Error in validation: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@login_required
@require_http_methods(["POST"])
def apply_visibility_rules_to_product(request, product_id):
    """
    API endpoint to apply E-commerce Visibility rules to a specific product
    """
    try:
        product = get_object_or_404(Prodotto, id=product_id)
        
        if not product.ecommerce_visibility:
            return JsonResponse({
                'status': 'error',
                'message': 'No E-commerce Visibility rule set for this product'
            }, status=400)
        
        # Import required modules
        from .visibility_rules import EcommerceVisibilityProcessor
        
        # Create processor and apply rules
        processor = EcommerceVisibilityProcessor()
        allowed_countries = processor.process_visibility_rule(
            product.ecommerce_visibility,
            {
                'taglia': product.taglia,
                'coppa': getattr(product, 'coppa', ''),  # If you have cup field
            }
        )
        
        logger.info(f"Applying visibility rule '{product.ecommerce_visibility}' to product {product_id}")
        logger.info(f"Allowed countries: {sorted(allowed_countries)}")
        
        # Clear existing country planning for this product
        from .models import PaesePianificazione
        PaesePianificazione.objects.filter(prodotto=product).delete()
        
        # Create new country planning records
        new_records = []
        for country_code in allowed_countries:
            new_records.append(PaesePianificazione(
                prodotto=product,
                codice_paese=country_code,
                data_tipo='as_available',  # Default to AAP
                is_available=True,
                availability_value='AAP',
                source_column='ecommerce_visibility_rule'
            ))
        
        # Bulk create new records
        if new_records:
            PaesePianificazione.objects.bulk_create(new_records, ignore_conflicts=True)
        
        # Update product JSON fields
        product.paesi_disponibili = list(allowed_countries)
        product.paesi_aap = list(allowed_countries)
        product.paesi_con_date = []
        product.date_paesi = {}
        product.save()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Visibility rules applied successfully. {len(allowed_countries)} countries configured.',
            'countries_applied': sorted(allowed_countries),
            'rule_applied': product.ecommerce_visibility
        })
        
    except Exception as e:
        logger.error(f"Error applying visibility rules to product {product_id}: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f'Failed to apply visibility rules: {str(e)}'
        }, status=500)
