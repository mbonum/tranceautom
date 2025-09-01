"""
Django Country Processor - Integration with Django database
Uses the new simple_country_processor and integrates it with Django models
"""

import pandas as pd
import os
from typing import Optional, Dict, List
import logging
from django.db import transaction, models
from django.conf import settings
from .models import PianificazioneImport, Prodotto, PaesePianificazione
from .simple_country_processor import (
    load_and_clean_excel_data,
    create_country_columns,
    get_countries_list,
    analyze_final_data
)

logger = logging.getLogger(__name__)


class DjangoCountryProcessor:
    """
    Processor to integrate the new country processor with Django
    """
    
    def __init__(self):
        self.all_countries = get_countries_list()
    
    def process_excel_to_database(self, excel_file_path: str, import_record: PianificazioneImport) -> Dict:
        """
        Process an Excel file and save everything to Django database
        
        Args:
            excel_file_path (str): Path to Excel file
            import_record (PianificazioneImport): Import record to populate
            
        Returns:
            Dict: Processing statistics
        """
        try:
            logger.info(f"🔄 Starting Excel processing for import {import_record.id}")
            
            # Step 1: Load and clean Excel data
            df = load_and_clean_excel_data(excel_file_path)
            if df.empty:
                raise Exception("Unable to load data from Excel file")
            
            # Step 2: Create country columns
            df_with_countries = create_country_columns(df)
            
            # Step 3: Save to Django database
            stats = self._save_to_database(df_with_countries, import_record)
            
            # Step 4: Update import record
            import_record.status = 'processed'
            import_record.total_products = stats['products_created']
            import_record.total_countries = len(self.all_countries)
            import_record.save()
            
            logger.info(f"Processing completed for import {import_record.id}")
            logger.info(f"Products created: {stats['products_created']}")
            logger.info(f"Country records created: {stats['country_records_created']}")
            
            return stats
            
        except Exception as e:
            logger.error(f"Error in processing: {str(e)}")
            import_record.status = 'error'
            import_record.error_message = str(e)
            import_record.save()
            raise
    
    @transaction.atomic
    def _save_to_database(self, df: pd.DataFrame, import_record: PianificazioneImport) -> Dict:
        """
        Salva i dati processati nel database Django
        
        Args:
            df (pd.DataFrame): DataFrame con i dati processati
            import_record (PianificazioneImport): Record di import
            
        Returns:
            Dict: Statistiche del salvataggio
        """
        try:
            products_created = 0
            country_records_created = 0
            country_columns = [col for col in df.columns if col.startswith('country_')]
            core_columns = [col for col in df.columns if not col.startswith('country_')]
            
            logger.info(f"Saving {len(df)} products to database...")
            
            for idx, row in df.iterrows():
                # Create main product
                prodotto_data = {}
                
                # Map standard fields
                field_mapping = {
                    'chiave_articolo': ['Chiave Articolo', 'chiave_articolo', 'chiave articolo'],
                    'concatena_magazzino': ['Concatena Magazzino', 'concatena_magazzino'],
                    'serie': ['Serie', 'serie'],
                    'merceologia': ['Merceologia', 'merceologia'],
                    'n_tranche': ['N. Tranche', 'n_tranche', 'tranche'],
                    'stagione': ['Stagione', 'stagione'],
                    'sku': ['SKU', 'sku'],
                    'articolo': ['Articolo', 'articolo'],
                    'colore': ['Colore', 'colore'],
                    'taglia': ['Taglia', 'taglia'],
                    'descrizione': ['Descrizione', 'descrizione'],
                    'data_inizio_consegna': ['Data Inizio Consegna', 'data_inizio_consegna'],
                    'data_spedizione_reale': ['Data Spedizione Reale', 'data_spedizione_reale'],
                    'data_consegna_fornitore': ['Data Consegna Fornitore', 'data_consegna_fornitore'],
                    'fornitore': ['Fornitore', 'fornitore'],
                    'codice_forn': ['Codice Forn', 'codice_forn'],
                    'made_in': ['Made In', 'made_in'],
                }
                
                # Estrai i dati per ogni campo
                for field_name, possible_columns in field_mapping.items():
                    value = self._find_column_value(row, possible_columns, core_columns)
                    prodotto_data[field_name] = str(value) if pd.notna(value) else ''
                
                # Crea il prodotto
                prodotto = Prodotto.objects.create(
                    pianificazione=import_record,
                    row_number=idx + 1,
                    **prodotto_data
                )
                products_created += 1
                
                # Processa i paesi per questo prodotto
                available_countries = []
                aap_countries = []
                countries_with_dates = {}
                
                for country_col in country_columns:
                    country_code = country_col.replace('country_', '')
                    country_value = row[country_col]
                    
                    if pd.notna(country_value) and str(country_value).strip():
                        available_countries.append(country_code)
                        
                        # Determina il tipo di disponibilità
                        date_type = 'non_specificato'
                        data_disponibilita = None
                        availability_value = str(country_value).strip()
                        
                        if availability_value.upper() in ['AAP', 'ASAP']:
                            date_type = 'as_available'
                            aap_countries.append(country_code)
                        elif availability_value.upper() in ['TBD']:
                            date_type = 'to_be_determined'
                        else:
                            # Prova a parsare come data
                            parsed_date = self._parse_date(availability_value)
                            if parsed_date:
                                date_type = 'data_specifica'
                                data_disponibilita = parsed_date
                                countries_with_dates[country_code] = availability_value
                        
                        # Crea il record paese
                        PaesePianificazione.objects.create(
                            prodotto=prodotto,
                            codice_paese=country_code,
                            data_disponibilita=data_disponibilita,
                            data_tipo=date_type,
                            availability_value=availability_value,
                            is_available=True,
                            source_column=country_col
                        )
                        country_records_created += 1
                
                # Aggiorna i campi JSON del prodotto per compatibilità
                prodotto.paesi_disponibili = available_countries
                prodotto.paesi_aap = aap_countries
                prodotto.paesi_con_date = list(countries_with_dates.keys())
                prodotto.date_paesi = countries_with_dates
                prodotto.save()
            
            logger.info(f"✅ Saved {products_created} products and {country_records_created} country records")
            
            return {
                'products_created': products_created,
                'country_records_created': country_records_created,
                'countries_found': set([rec.codice_paese for rec in 
                                       PaesePianificazione.objects.filter(prodotto__pianificazione=import_record)])
            }
            
        except Exception as e:
            logger.error(f"Errore nel salvataggio database: {str(e)}")
            raise
    
    def _find_column_value(self, row: pd.Series, possible_columns: List[str], available_columns: List[str]):
        """
        Trova il valore in una delle possibili colonne
        
        Args:
            row: Riga del DataFrame
            possible_columns: Lista di nomi possibili per la colonna
            available_columns: Colonne disponibili nel DataFrame
            
        Returns:
            Valore trovato o None
        """
        for col_name in possible_columns:
            # Cerca match esatto
            if col_name in available_columns:
                return row[col_name]
            
            # Cerca match case-insensitive
            for available_col in available_columns:
                if col_name.lower() == available_col.lower():
                    return row[available_col]
                
                # Cerca match parziale
                if col_name.lower() in available_col.lower() or available_col.lower() in col_name.lower():
                    return row[available_col]
        
        return None
    
    def _parse_date(self, date_str: str) -> Optional[object]:
        """
        Prova a parsare una stringa come data
        
        Args:
            date_str: Stringa da parsare
            
        Returns:
            Oggetto date o None
        """
        if not date_str or pd.isna(date_str):
            return None
        
        try:
            from datetime import datetime
            
            # Prova vari formati di data
            formats = [
                '%Y-%m-%d',
                '%d/%m/%Y', 
                '%d-%m-%Y',
                '%Y-%m-%d %H:%M:%S',
                '%d/%m/%Y %H:%M:%S'
            ]
            
            date_str = str(date_str).strip()
            
            for fmt in formats:
                try:
                    parsed = datetime.strptime(date_str, fmt)
                    return parsed.date()
                except ValueError:
                    continue
            
            # Se non riesce a parsare, ritorna None
            return None
            
        except Exception:
            return None
    
    def get_import_statistics(self, import_record: PianificazioneImport) -> Dict:
        """
        Ottiene statistiche per un import
        
        Args:
            import_record: Record di import
            
        Returns:
            Dict: Statistiche
        """
        try:
            total_products = import_record.prodotti.count()
            total_country_records = PaesePianificazione.objects.filter(
                prodotto__pianificazione=import_record
            ).count()
            
            # Conta paesi unici
            unique_countries = PaesePianificazione.objects.filter(
                prodotto__pianificazione=import_record
            ).values_list('codice_paese', flat=True).distinct()
            
            # Statistiche per tipo di data
            data_types = PaesePianificazione.objects.filter(
                prodotto__pianificazione=import_record
            ).values('data_tipo').annotate(
                count=models.Count('id')
            )
            
            return {
                'total_products': total_products,
                'total_country_records': total_country_records,
                'unique_countries': len(unique_countries),
                'countries_list': list(unique_countries),
                'data_types_breakdown': {item['data_tipo']: item['count'] for item in data_types}
            }
            
        except Exception as e:
            logger.error(f"Errore nel calcolo statistiche: {str(e)}")
            return {}
