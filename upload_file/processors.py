"""
Data processors for Tranche Automation
Handles the processing and validation of product data and country planning
"""

import logging
import pandas as pd
from datetime import datetime, date
from typing import Dict, List, Optional, Any, Tuple
from django.db import transaction
from django.core.exceptions import ValidationError

from .models import Prodotto, PaesePianificazione, PianificazioneImport
from .visibility_rules import VisibilityRules, parse_visibility_rule
from .parsers import VisibilityColumnParser, CountryDateExtractor, DateNormalizer
from .country_utils import CountryManager, CountryDateExtractor as UtilsCountryDateExtractor, TrancheDateConverter
from .correct_country_processor import CorrectCountryPlanningProcessor

logger = logging.getLogger(__name__)


class ProductDataProcessor:
    """
    Processes product data from Excel rows and creates Product instances
    """
    
    def __init__(self, planning_import: PianificazioneImport):
        logger.info(f"Inizializzando ProductDataProcessor per planning: {planning_import.id}")
        self.planning_import = planning_import
        self.visibility_parser = VisibilityColumnParser()
        
    def process_product_row(self, row_data: List[Any], headers: List[str], 
                          row_number: int) -> Optional[Prodotto]:
        print(f"DEBUG: INIZIO processamento riga {row_number}")
        logger.info(f"INIZIO processamento riga {row_number}")
        
        try:
            # Extract basic product data
            print(f"DEBUG: Inizio estrazione dati prodotto per riga {row_number}")
            product_data = self._extract_product_data(row_data, headers)
            print(f"DEBUG: Dati estratti: {product_data}")
            
            # Validate product data
            print(f"DEBUG: Inizio validazione dati per riga {row_number}")
            validation_result = self._validate_product_data(product_data, row_number)
            if not validation_result['is_valid']:
                print(f"DEBUG: Validazione fallita per riga {row_number}: {validation_result['errors']}")
                return None
            print(f"DEBUG: Validazione superata per riga {row_number}")
                
            # Apply business rules
            processed_data = self._apply_business_rules(product_data)
            print(f"DEBUG: Business rules applicate: {processed_data}")
            
            # Create Prodotto instance
            print(f"DEBUG: TENTATIVO creazione Prodotto per riga {row_number}")
            
            prodotto = Prodotto.objects.create(
                pianificazione=self.planning_import,
                codice_forn=processed_data['codice_forn'],
                commerce=processed_data['commerce'],
                made_in=processed_data['made_in'],
                categorie=processed_data['categorie'],
                impianti_russia_doganale=processed_data.get('impianti_russia_doganale', ''),
                row_number=row_number
            )
            
            print(f"DEBUG: SUCCESSO! Prodotto creato: ID={prodotto.id}, codice={prodotto.codice_forn}")
            return prodotto
            
        except Exception as e:
            print(f"DEBUG: ERRORE CRITICO riga {row_number}: {str(e)}")
            print(f"DEBUG: Tipo errore: {type(e).__name__}")
            logger.error(f"Error processing product row {row_number}: {str(e)}", exc_info=True)
            return None
    
    def _extract_product_data(self, row_data: List[Any], headers: List[str]) -> Dict[str, str]:
        """
        Extract product data from row based on headers and position
        Simplified and aligned with working views.py logic
        """
        print(f"DEBUG: Headers disponibili nel file Excel:")
        for i, header in enumerate(headers):
            print(f"   {i}: '{header}'")
        
        # Inizializza i campi di base
        data = {
            'codice_forn': '',
            'commerce': '',
            'made_in': '',
            'categorie': '',
            'impianti_russia_doganale': ''
        }
        
        mappings_found = []
        
        # Estrai usando posizioni predefinite come nelle views funzionanti
        # Basato sul modello delle vecchie views che funzionavano
        product_fields = {
            0: 'codice_forn',        # ChiaveArticoloColore 
            1: 'commerce',           # ConcatenatedId o Commerce
            2: 'categorie',          # Merceologia
            3: 'made_in',            # Potrebbe essere altro campo
            4: 'impianti_russia_doganale'  # Potrebbe essere altro campo
        }
        
        # Estrai i dati dalle prime colonne principali
        for col_idx, field_name in product_fields.items():
            if col_idx < len(row_data) and row_data[col_idx] is not None:
                value = str(row_data[col_idx]).strip()
                if value and value.upper() not in ['NAN', 'NONE', '']:
                    data[field_name] = value
                    mappings_found.append(f"{field_name} <- posizione {col_idx} = '{value}'")
        
        # Se il primo campo è vuoto, prova a trovare il primo campo non vuoto
        if not data['codice_forn']:
            for i, cell in enumerate(row_data[:10]):  # Controlla le prime 10 colonne
                if cell is not None:
                    value = str(cell).strip()
                    if value and value.upper() not in ['NAN', 'NONE', '', 'TOTALE', 'COMPLESSIVO']:
                        data['codice_forn'] = value
                        mappings_found.append(f"codice_forn <- posizione {i} = '{value}' (primo non vuoto)")
                        break
        
        # Assicurati che commerce abbia un valore
        if not data['commerce'] and data['codice_forn']:
            data['commerce'] = data['codice_forn']  # Usa il codice prodotto come commerce
            mappings_found.append(f"commerce <- usa codice_forn = '{data['commerce']}'")
        
        print(f"DEBUG: Mappings trovati: {mappings_found}")
        return data
    
    def _validate_product_data(self, product_data: Dict[str, str], row_number: int) -> Dict[str, Any]:
        """
        Validate product data before creation
        """
        logger.debug(f"Validazione dati per riga {row_number}")
        errors = []
        warnings = []
        
        # Controlla se la riga contiene solo dati di totale/sommario
        codice = product_data['codice_forn'].upper()
        if any(word in codice for word in ['TOTALE', 'COMPLESSIVO', 'TOTAL', 'SUM']):
            errors.append(f"Row {row_number}: Skipping summary/total row: '{product_data['codice_forn']}'")
        
        # Il codice prodotto è obbligatorio
        if not product_data['codice_forn'] or len(product_data['codice_forn'].strip()) == 0:
            errors.append(f"Row {row_number}: Product code is required")
        
        # Commerce non è più obbligatorio, mettiamo un default se manca
        if not product_data['commerce']:
            product_data['commerce'] = product_data['codice_forn'] or f"Product_{row_number}"
            warnings.append(f"Row {row_number}: Using default commerce value")
        
        # Log warnings
        for warning in warnings:
            print(f"WARNING: {warning}")
            logger.warning(f"   {warning}")
        
        # Format validation
        if product_data['codice_forn'] and len(product_data['codice_forn']) > 100:
            errors.append(f"Row {row_number}: Product code too long (max 100 characters)")
        
        result = {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
        
        if result['is_valid']:
            print(f"DEBUG: Validazione OK per riga {row_number}")
            logger.debug(f"   Validazione OK per riga {row_number}")
        else:
            print(f"DEBUG: Validazione FALLITA per riga {row_number}: {errors}")
            logger.error(f"   Validazione FALLITA per riga {row_number}: {errors}")
            
        return result
    
    def _apply_business_rules(self, product_data: Dict[str, str]) -> Dict[str, str]:
        """
        Apply business rules to product data
        """
        logger.debug(f"Applicazione business rules")
        logger.debug(f"   Input: {product_data}")
        
        # Clean and normalize data
        result = product_data.copy()
        
        # Normalize product code
        result['codice_forn'] = result['codice_forn'].upper().strip()
        
        # Normalize commerce field
        result['commerce'] = result['commerce'].strip()
        
        # Normalize made_in field
        result['made_in'] = result['made_in'].strip()
        
        # Normalize categories
        result['categorie'] = result['categorie'].strip()
        
        # Normalize impianti_russia_doganale
        result['impianti_russia_doganale'] = result.get('impianti_russia_doganale', '').strip()
        
        logger.debug(f"   Output: {result}")
        return result


class SimpleCountryProcessor:
    """
    Wrapper per utilizzare il CorrectCountryPlanningProcessor
    """
    
    def __init__(self, planning_import: PianificazioneImport):
        self.planning_import = planning_import
        self.correct_processor = CorrectCountryPlanningProcessor()
        
    def process_product_countries(self, prodotto: Prodotto, row_data: List[Any], headers: List[str], df: pd.DataFrame = None) -> List[PaesePianificazione]:
        """
        Processa i paesi per un prodotto usando il processor corretto
        """
        logger.info(f"INIZIO correct country processing per {prodotto.codice_forn}")
        
        try:
            # Crea i dati di pianificazione paese
            countries_data = self.correct_processor.create_country_plannings(
                prodotto, row_data, headers, df
            )
            
            # Salva nel database
            saved_objects = self.correct_processor.save_to_database(countries_data)
            
            logger.info(f"SUCCESS: Processati {len(saved_objects)} paesi per {prodotto.codice_forn}")
            return saved_objects
            
        except Exception as e:
            logger.error(f"ERRORE processing countries per {prodotto.codice_forn}: {str(e)}", exc_info=True)
            return []


class CountryPlanningProcessor:
    """
    Processes country planning data and creates PaesePianificazione instances
    """
    
    def __init__(self):
        logger.info(f"Inizializzando CountryPlanningProcessor")
        self.visibility_parser = VisibilityColumnParser()
        
    def create_country_plannings(self, prodotto: Prodotto, 
                               country_mappings: Dict[int, Dict],
                               visibility_columns: List[int],
                               row_data: List[Any],
                               headers: List[str]) -> List[Dict[str, Any]]:
        """
        Create country planning records for a product
        NUOVA LOGICA: Prima legge visibility rules, poi applica le date
        """
        print(f"🌍 DEBUG: INIZIO country processing per {prodotto.codice_forn}")
        print(f"   Country mappings: {len(country_mappings)}")
        print(f"   Visibility columns: {len(visibility_columns)}")
        print(f"   Row data length: {len(row_data)}")

        countries_data = []
        
        try:
            # STEP 1: Determina i paesi ammessi dalle VISIBILITY RULES
            allowed_countries = self._get_allowed_countries_from_visibility(
                visibility_columns, row_data, headers
            )
            print(f"   ✅ Paesi ammessi da visibility rules: {len(allowed_countries)} paesi")
            
            # STEP 2: Estrae le DATE dalle colonne paese
            country_dates = self._extract_dates_from_country_columns(
                country_mappings, row_data
            )
            print(f"   ✅ Date estratte da colonne: {len(country_dates)} mappings")
            for country, date_info in list(country_dates.items())[:5]:
                print(f"      {country}: {date_info['date']} ({date_info['source']})")
            
            # STEP 3: Combina paesi ammessi + date disponibili
            final_mapping = self._combine_countries_and_dates(allowed_countries, country_dates)
            print(f"   ✅ Mapping finale: {len(final_mapping)} paesi con date")
            
            # STEP 4: Crea i record nel database
            for country_code, date_info in final_mapping.items():
                planning_data = self._create_single_country_planning(
                    prodotto, country_code, date_info
                )
                if planning_data:
                    countries_data.append(planning_data)
                    print(f"   📝 Creato planning: {country_code} -> {date_info['date']}")
                    
            print(f"🎉 SUCCESS: Creati {len(countries_data)} country plannings per {prodotto.codice_forn}")
            
        except Exception as e:
            logger.error(f"ERRORE creating country plannings per {prodotto.codice_forn}: {str(e)}", exc_info=True)
            
        return countries_data
    
    def _get_allowed_countries_from_visibility(self, visibility_columns: List[int], 
                                            row_data: List[Any], headers: List[str]) -> List[str]:
        """
        NUOVA FUNZIONE: Estrae SOLO la lista dei paesi ammessi dalle visibility rules
        """
        print(f"      🔍 Analisi visibility rules...")
        allowed_countries = set()
        
        for col_idx in visibility_columns:
            if col_idx < len(row_data):
                cell_value = row_data[col_idx]
                if cell_value and str(cell_value).strip():
                    rule_text = str(cell_value).strip()
                    print(f"      📋 Visibility rule: '{rule_text}'")
                    
                    try:
                        # Usa visibility_rules.py per parsare la regola
                        visibility_data = parse_visibility_rule(rule_text)
                        countries_from_rule = visibility_data['allowed_countries']
                        allowed_countries.update(countries_from_rule)
                        print(f"      ✅ Regola '{rule_text}' -> {len(countries_from_rule)} paesi")
                        
                    except Exception as e:
                        print(f"      ❌ Errore parsing visibility rule '{rule_text}': {e}")
        
        # Se non troviamo regole visibility, usa tutti i paesi come fallback
        if not allowed_countries:
            print(f"      ⚠️ FALLBACK: Nessuna visibility rule trovata, usando tutti i paesi")
            from .visibility_rules import VisibilityRules
            allowed_countries = set(VisibilityRules.ALL_COUNTRIES)
            
        print(f"      ✅ Totale paesi ammessi: {len(allowed_countries)}")
        return list(allowed_countries)
    
    def _extract_dates_from_country_columns(self, country_mappings: Dict[int, Dict], 
                                           row_data: List[Any]) -> Dict[str, Dict]:
        """
        Enhanced date extraction using country_utils logic
        """
        print(f"      🗓️ Analisi colonne date con nuova logica...")
        country_dates = {}
        
        # Use the enhanced country date extractor from country_utils
        headers = [mapping.get('group_header', '') for mapping in country_mappings.values()]
        
        # Convert country_mappings format to match what the utility expects
        utils_country_columns = {}
        for col_idx, mapping in country_mappings.items():
            header_name = mapping.get('group_header', f'Column_{col_idx}')
            utils_country_columns[header_name] = {
                'column_index': col_idx,
                'countries': mapping.get('countries', []),
                'countries_with_dates': mapping.get('countries_with_dates', {}),
                'group_header': header_name
            }
        
        # Extract dates using the enhanced utility
        raw_country_dates = UtilsCountryDateExtractor.extract_country_dates_from_row(
            row_data, utils_country_columns, headers
        )
        
        # Convert to the format expected by the processor
        for country_code, date_str in raw_country_dates.items():
            if country_code in CountryManager.get_all_countries():
                normalized_date = self._normalize_date_value(date_str)
                date_type = self._determine_date_type(normalized_date)
                
                # Find source column from mappings
                source_column = 0
                source_header = 'unknown'
                for col_idx, mapping in country_mappings.items():
                    if country_code in mapping.get('countries', []):
                        source_column = col_idx
                        source_header = mapping.get('group_header', f'Column_{col_idx}')
                        break
                
                country_dates[country_code] = {
                    'date': normalized_date,
                    'date_type': date_type,
                    'source': 'enhanced_extraction',
                    'source_column': source_column,
                    'source_header': source_header,
                    'raw_value': date_str
                }
                print(f"          -> {country_code}: {normalized_date} (enhanced)")
                        
        print(f"      ✅ Date estratte per {len(country_dates)} paesi con nuova logica")
        return country_dates
    

    
    def _combine_countries_and_dates(self, allowed_countries: List[str], 
                                   country_dates: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        NUOVA FUNZIONE: Combina paesi ammessi con date disponibili
        
        LOGICA:
        1. Se un paese è ammesso E ha una data specifica -> usa quella data
        2. Se un paese è ammesso ma NON ha data specifica -> usa 'TBD'
        3. Se un paese NON è ammesso -> non includerlo nel risultato finale
        """
        print(f"      🔗 Combinazione paesi e date...")
        final_mapping = {}
        
        for country in allowed_countries:
            if country in country_dates:
                # Paese ammesso CON data specifica
                final_mapping[country] = country_dates[country].copy()
                print(f"        ✅ {country}: {country_dates[country]['date']} (da colonna)")
            else:
                # Paese ammesso SENZA data specifica -> TBD
                final_mapping[country] = {
                    'date': 'TBD',
                    'date_type': 'tbd',
                    'source': 'visibility_only',
                    'source_column': 0,  # Usa 0 invece di -1 per evitare constraint error
                    'source_header': 'visibility_rule',
                    'raw_value': 'TBD'
                }
                print(f"        ⚠️ {country}: TBD (ammesso ma senza data)")
        
        print(f"      ✅ Mapping finale: {len(final_mapping)} paesi")
        return final_mapping
        
    def _normalize_date_value(self, raw_date: str) -> str:
        """
        Normalizza un valore di data dal file Excel usando le utilities
        """
        from .country_utils import DateNormalizer
        return DateNormalizer.normalize_date_value(raw_date)
    
    def _determine_date_type(self, normalized_date: str) -> str:
        """
        Determina il tipo di data usando le utilities
        """
        from .country_utils import DateNormalizer
        return DateNormalizer.determine_date_type(normalized_date)
    
    def _merge_and_resolve_countries(self, visibility_countries: Dict[str, Dict], 
                                   column_countries: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Merge country data from different sources and resolve conflicts
        
        Priority: Column data > Visibility data
        """
        result = {}
        
        # Start with visibility countries
        result.update(visibility_countries)
        
        # Override with column data (higher priority)
        for country, info in column_countries.items():
            if country in result:
                # Column data takes precedence
                logger.debug(f"Overriding {country}: {result[country]['date']} -> {info['date']}")
            result[country] = info
            
        return result
    
    def _create_single_country_planning(self, prodotto: Prodotto, 
                                      country_code: str, date_info: Dict) -> Optional[Dict]:
        """
        Create a single country planning record
        """
        try:
            # Parse the date
            availability_date = self._parse_availability_date(date_info['date'])
            
            # Create or update planning record
            planning, created = PaesePianificazione.objects.get_or_create(
                prodotto=prodotto,
                codice_paese=country_code,
                data_disponibilita=availability_date,
                defaults={
                    'data_tipo': date_info['date_type'],
                    'source_column': date_info.get('source_column', 0),  # 0 invece di -1
                    'source_group': date_info.get('source_header', date_info.get('source_text', 'unknown'))
                }
            )
            
            if not created:
                # Update existing record
                planning.data_tipo = date_info['date_type']
                planning.source_column = date_info.get('source_column', 0)  # 0 invece di -1
                planning.source_group = date_info.get('source_header', date_info.get('source_text', 'unknown'))
                planning.save()
                
            return {
                'country': country_code,
                'date': date_info['date'],
                'planning_id': planning.id,
                'created': created
            }
            
        except Exception as e:
            logger.error(f"Error creating country planning for {country_code}: {str(e)}")
            return None
    
    def _parse_availability_date(self, date_str: str) -> date:
        """
        Parse availability date string to date object using enhanced logic
        """
        if date_str in ['AAP', 'ASAP', 'TBD']:
            # Use far future date for special values
            return datetime(2030, 12, 31).date()
        
        # Try to use tranche conversion if it looks like a tranche number
        try:
            tranche_num = int(date_str)
            if 1 <= tranche_num <= 50:  # Reasonable tranche range
                iso_date = TrancheDateConverter.convert_tranche_to_iso_date(date_str)
                return datetime.strptime(iso_date, '%Y-%m-%d').date()
        except ValueError:
            pass  # Not a tranche number, continue with date parsing
            
        try:
            # Try parsing standard format
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            try:
                # Try pandas parsing as fallback
                import pandas as pd
                parsed = pd.to_datetime(date_str)
                return parsed.date()
            except Exception:
                # Last resort: far future date
                logger.warning(f"Could not parse date '{date_str}', using default")
                return datetime(2030, 12, 31).date()


class VisibilityRuleProcessor:
    """
    Specialized processor for handling visibility rules and their application
    """
    
    @staticmethod
    def apply_visibility_rules(countries_from_columns: List[str], 
                             visibility_rule: str) -> List[str]:
        """
        Apply visibility rules to determine final country list
        
        Args:
            countries_from_columns: Countries extracted from data columns
            visibility_rule: Visibility rule text
            
        Returns:
            Final list of allowed countries
        """
        try:
            if not visibility_rule:
                return countries_from_columns
                
            visibility_data = parse_visibility_rule(visibility_rule)
            allowed_countries = visibility_data['allowed_countries']
            
            # Intersection: only countries that are both in columns AND allowed by rule
            if countries_from_columns:
                final_countries = [c for c in countries_from_columns if c in allowed_countries]
            else:
                # If no countries in columns, use all allowed countries
                final_countries = allowed_countries
                
            return final_countries
            
        except Exception as e:
            logger.error(f"Error applying visibility rule '{visibility_rule}': {str(e)}")
            return countries_from_columns


class ValidationProcessor:
    """
    Validates data integrity and business rules before final processing
    """
    
    @staticmethod
    def validate_import_data(planning_import: PianificazioneImport) -> Dict[str, Any]:
        """
        Validate imported data for consistency and completeness
        """
        errors = []
        warnings = []
        
        # Check products
        products = Prodotto.objects.filter(pianificazione=planning_import)
        product_count = products.count()
        
        if product_count == 0:
            errors.append("No products found in import")
            
        # Check country plannings
        total_plannings = 0
        products_without_countries = 0
        
        for product in products:
            planning_count = product.pianificazioni_paesi.count()
            total_plannings += planning_count
            
            if planning_count == 0:
                products_without_countries += 1
                
        if products_without_countries > 0:
            warnings.append(f"{products_without_countries} products have no country planning")
            
        # Check for invalid dates
        invalid_dates = PaesePianificazione.objects.filter(
            prodotto__pianificazione=planning_import,
            data_disponibilita__lt=date.today()
        ).count()
        
        if invalid_dates > 0:
            warnings.append(f"{invalid_dates} country plannings have past dates")
            
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'products': product_count,
                'total_plannings': total_plannings,
                'products_without_countries': products_without_countries,
                'invalid_dates': invalid_dates
            }
        }
