#!/usr/bin/env python3
"""
Processore per estrazione paesi integrato con Django
Utilizza EnhancedCountryExtractor per isolare paesi dal CSV
"""

import pandas as pd
import numpy as np
import re
import json
from datetime import datetime, date
from typing import Dict, List, Set, Tuple, Optional, Any
import logging
from django.conf import settings

# Import dei modelli Django
from .models import Prodotto, PaesePianificazione

logger = logging.getLogger(__name__)

class DjangoCountryProcessor:
    """
    Processore per estrazione paesi integrato con Django
    """
    
    def __init__(self):
        self.all_countries = self._get_all_countries()
        self.country_columns_info = {}
        
    def _get_all_countries(self) -> List[str]:
        """
        Tutti i codici paese supportati
        """
        return [
            'AL', 'AM', 'AT', 'AZ', 'BA', 'BE', 'BG', 'BH', 'BR', 'BY', 'CH', 'CN', 'CO', 'CY', 'CZ', 
            'DE', 'DK', 'EE', 'ES', 'FL', 'FR', 'GB', 'GE', 'GR', 'HK', 'HR', 'HU', 'IE', 'IL', 
            'IT', 'JO', 'JP', 'KW', 'KZ', 'LB', 'LT', 'LU', 'LV', 'MA', 'MD', 'MK', 'MO', 'MT', 
            'MX', 'NL', 'PL', 'PT', 'QA', 'RO', 'RS', 'RU', 'SA', 'SE', 'SI', 'SK', 'TN', 'TR', 
            'TW', 'UA', 'UK', 'US', 'UZ', 'XK'
        ]
    
    def process_csv_to_database(self, csv_file_path: str, import_record_id: int) -> Dict[str, Any]:
        """
        Processa il CSV e salva i dati nel database Django
        
        Args:
            csv_file_path: Percorso del file CSV
            import_record_id: ID del record di importazione
            
        Returns:
            Dizionario con statistiche del processing
        """
        try:
            logger.info(f"🚀 Avvio processing Django per: {csv_file_path}")
            
            # Carica il CSV
            df = pd.read_csv(csv_file_path)
            logger.info(f"   📊 CSV caricato: {df.shape[0]} righe, {df.shape[1]} colonne")
            
            # Identifica le colonne dei paesi
            self._identify_country_columns(df.columns.tolist())
            
            # Statistiche
            stats = {
                'total_rows_processed': 0,
                'products_created': 0,
                'country_records_created': 0,
                'errors': [],
                'countries_found': set(),
                'availability_types': {}
            }
            
            # Processa ogni riga
            for idx, row in df.iterrows():
                if idx == 0:  # Salta l'header se presente nelle righe
                    continue
                    
                # Salta righe vuote
                if row.isna().all():
                    continue
                
                try:
                    # Estrai informazioni del prodotto
                    product_info = self._extract_product_info(row, df.columns.tolist())
                    
                    # Crea il prodotto nel database
                    prodotto = self._create_or_update_product(product_info, import_record_id, idx)
                    
                    if prodotto:
                        stats['products_created'] += 1
                        
                        # Crea i record per i paesi
                        country_stats = self._create_country_records(prodotto, row)
                        
                        stats['country_records_created'] += country_stats['records_created']
                        stats['countries_found'].update(country_stats['countries'])
                        
                        # Aggiorna statistiche di disponibilità
                        for avail_type, count in country_stats['availability_types'].items():
                            stats['availability_types'][avail_type] = stats['availability_types'].get(avail_type, 0) + count
                    
                    stats['total_rows_processed'] += 1
                    
                    if (idx + 1) % 50 == 0:
                        logger.info(f"   ⏳ Elaborate {idx + 1} righe...")
                        
                except Exception as e:
                    error_msg = f"Errore riga {idx}: {str(e)}"
                    logger.warning(error_msg)
                    stats['errors'].append(error_msg)
            
            # Converti set in lista per JSON
            stats['countries_found'] = list(stats['countries_found'])
            
            logger.info(f"✅ Processing completato!")
            logger.info(f"   📈 Righe processate: {stats['total_rows_processed']}")
            logger.info(f"   📦 Prodotti creati: {stats['products_created']}")
            logger.info(f"   🌍 Record paesi creati: {stats['country_records_created']}")
            logger.info(f"   🌍 Paesi unici: {len(stats['countries_found'])}")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Errore durante il processing: {e}")
            raise
    
    def _identify_country_columns(self, headers: List[str]) -> None:
        """
        Identifica le colonne che contengono gruppi di paesi
        """
        self.country_columns_info = {}
        
        # Pattern per identificare gruppi di paesi (formato: XX-YY-ZZ)
        country_group_pattern = r'^[A-Z]{2}(-[A-Z]{2})+$'
        
        for idx, header in enumerate(headers):
            if header and re.match(country_group_pattern, str(header).strip()):
                # Estrai i paesi da questo gruppo
                countries = str(header).strip().split('-')
                
                # Filtra solo paesi validi
                valid_countries = [c for c in countries if c in self.all_countries]
                
                if valid_countries:
                    self.country_columns_info[idx] = {
                        'header': header,
                        'column_index': idx,
                        'countries': valid_countries,
                        'country_count': len(valid_countries)
                    }
                    
                    logger.info(f"   🌍 Colonna {idx}: {header} → {len(valid_countries)} paesi")
    
    def _extract_product_info(self, row: pd.Series, headers: List[str]) -> Dict[str, Any]:
        """
        Estrae le informazioni del prodotto dalla riga
        """
        return {
            'chiave_articolo': self._safe_get_value(row, headers, 'chiave articolo colore x Uff. PIANIF', ''),
            'concatena_magazzino': self._safe_get_value(row, headers, 'concatena 1 per MAGAZZINO', ''),
            'serie': self._safe_get_value(row, headers, 'Serie', ''),
            'merceologia': self._safe_get_value(row, headers, 'Merceologia', ''),
            'n_tranche': self._safe_get_value(row, headers, 'N. Tranche', ''),
            'stagione': self._safe_get_value(row, headers, 'Stag.', ''),
            'sku': self._safe_get_value(row, headers, 'SKU', ''),
            'articolo': self._safe_get_value(row, headers, 'Articolo', ''),
            'colore': self._safe_get_value(row, headers, 'Colore', ''),
            'taglia': self._safe_get_value(row, headers, 'Taglia', ''),
            'descrizione_articolo': self._safe_get_value(row, headers, 'Descrizione articolo', ''),
            'data_inizio_consegna': self._safe_get_value(row, headers, 'DATA INIZIO CONSEGNA AI P.V. (ORIGINARIA)', ''),
            'data_spedizione_reale': self._safe_get_value(row, headers, 'DATA SPEDIZIONE REALE STANDARD (PIM)', ''),
            'impianti_per': self._safe_get_value(row, headers, 'IMPIANTI PER', ''),
            'note_ufficio_commerciale': self._safe_get_value(row, headers, 'NOTE UFFICIO COMMERCIALE', ''),
            'data_consegna_fornitore': self._safe_get_value(row, headers, 'DATA CONSEGNA FORNITORE PRIMO 60%', ''),
            'fornitore': self._safe_get_value(row, headers, 'FORNITORE', ''),
            'codice_forn': self._safe_get_value(row, headers, 'CODICE FORN', ''),
            'made_in': self._safe_get_value(row, headers, 'MADE IN', ''),
            'impianti_russia': self._safe_get_value(row, headers, 'IMPIANTI RUSSIA PER DOGANALE', ''),
            'ocli_mondo_russia': self._safe_get_value(row, headers, 'OCLI (MONDO+RUSSIA)', ''),
            'categorie': self._safe_get_value(row, headers, 'CATEGORIE', ''),
            'note_categorie': self._safe_get_value(row, headers, 'NOTE CATEGORIE', ''),
            'ecommerce_visibility': self._safe_get_value(row, headers, 'E-COMMERCE VISIBILITY (COUNTRIES)', '')
        }
    
    def _safe_get_value(self, row: pd.Series, headers: List[str], column_name: str, default: Any = None) -> Any:
        """
        Estrae un valore dalla riga in modo sicuro
        """
        try:
            if column_name in headers:
                idx = headers.index(column_name)
                if idx < len(row):
                    value = row.iloc[idx]
                    return value if pd.notna(value) else default
            return default
        except Exception:
            return default
    
    def _create_or_update_product(self, product_info: Dict[str, Any], import_record_id: int, row_number: int) -> Optional[Prodotto]:
        """
        Crea o aggiorna un prodotto nel database
        """
        try:
            # Crea il prodotto (o lo aggiorna se esiste)
            prodotto, created = Prodotto.objects.get_or_create(
                sku=product_info['sku'],
                defaults={
                    'chiave_articolo': product_info['chiave_articolo'],
                    'concatena_magazzino': product_info['concatena_magazzino'],
                    'serie': product_info['serie'],
                    'merceologia': product_info['merceologia'],
                    'n_tranche': product_info['n_tranche'],
                    'stagione': product_info['stagione'],
                    'articolo': product_info['articolo'],
                    'colore': product_info['colore'],
                    'taglia': product_info['taglia'],
                    'descrizione': product_info['descrizione'],
                    'data_inizio_consegna': self._parse_date_field(product_info['data_inizio_consegna']),
                    'data_spedizione_reale': self._parse_date_field(product_info['data_spedizione_reale']),
                    'impianti_per': product_info['impianti_per'],
                    'note_ufficio_commerciale': product_info['note_ufficio_commerciale'],
                    'data_consegna_fornitore': self._parse_date_field(product_info['data_consegna_fornitore']),
                    'fornitore': product_info['fornitore'],
                    'codice_forn': product_info['codice_forn'],
                    'made_in': product_info['made_in'],
                    'impianti_russia': product_info['impianti_russia'],
                    'ocli_mondo_russia': product_info['ocli_mondo_russia'],
                    'categorie': product_info['categorie'],
                    'note_categorie': product_info['note_categorie'],
                    'ecommerce_visibility': product_info['ecommerce_visibility'],
                    'row_number': row_number,
                    'paesi_disponibili': [],
                    'paesi_aap': [],
                    'paesi_con_date': [],
                    'date_paesi': {}
                }
            )
            
            return prodotto
            
        except Exception as e:
            logger.error(f"Errore creazione prodotto {product_info.get('sku', 'N/A')}: {e}")
            return None
    
    def _create_country_records(self, prodotto: Prodotto, row: pd.Series) -> Dict[str, Any]:
        """
        Crea i record per i paesi associati al prodotto
        """
        stats = {
            'records_created': 0,
            'countries': set(),
            'availability_types': {}
        }
        
        # Lista per aggregare i dati sui paesi
        paesi_disponibili = []
        paesi_aap = []
        paesi_con_date = []
        date_paesi = {}
        
        for col_idx, col_info in self.country_columns_info.items():
            # Ottieni il valore della cella per questo gruppo di paesi
            if col_idx < len(row):
                cell_value = row.iloc[col_idx]
                
                # Classifica il tipo di disponibilità
                availability_type = self._classify_availability(cell_value)
                availability_date = self._parse_availability_date(cell_value)
                
                # Processa ogni paese nel gruppo
                for country_code in col_info['countries']:
                    try:
                        # Crea o aggiorna il record paese
                        paese_planning, created = PaesePianificazione.objects.get_or_create(
                            prodotto=prodotto,
                            codice_paese=country_code,
                            defaults={
                                'data_disponibilita': availability_date,
                                'data_tipo': availability_type,
                                'source_column': col_info['header'],
                                'source_group': col_info['header'],
                                'availability_value': str(cell_value) if pd.notna(cell_value) else '',
                                'is_available': self._is_country_available(cell_value)
                            }
                        )
                        
                        if created:
                            stats['records_created'] += 1
                        
                        # Aggrega dati per il prodotto
                        paesi_disponibili.append(country_code)
                        stats['countries'].add(country_code)
                        
                        if availability_type == 'as_available':
                            paesi_aap.append(country_code)
                        elif availability_type == 'data_specifica' and availability_date:
                            paesi_con_date.append(country_code)
                            date_paesi[country_code] = availability_date
                        
                        # Statistiche disponibilità
                        stats['availability_types'][availability_type] = stats['availability_types'].get(availability_type, 0) + 1
                        
                    except Exception as e:
                        logger.warning(f"Errore creazione paese {country_code} per prodotto {prodotto.sku}: {e}")
        
        # Aggiorna i campi JSON del prodotto
        try:
            prodotto.paesi_disponibili = list(set(paesi_disponibili))
            prodotto.paesi_aap = list(set(paesi_aap))
            prodotto.paesi_con_date = list(set(paesi_con_date))
            prodotto.date_paesi = date_paesi
            prodotto.save()
        except Exception as e:
            logger.warning(f"Errore aggiornamento dati JSON prodotto {prodotto.sku}: {e}")
        
        return stats
    
    def _classify_availability(self, value: Any) -> str:
        """
        Classifica il tipo di disponibilità
        """
        if pd.isna(value) or str(value).strip() == '':
            return 'non_specificato'
        
        value_str = str(value).strip().upper()
        
        if value_str == 'AAP':
            return 'as_available'
        elif value_str in ['TBD', 'TBC']:
            return 'to_be_determined'
        elif self._is_valid_date(value_str):
            return 'data_specifica'
        else:
            return 'altro'
    
    def _parse_availability_date(self, value: Any) -> Optional[date]:
        """
        Estrae la data di disponibilità se presente
        """
        if pd.isna(value):
            return None
            
        value_str = str(value).strip()
        
        if self._is_valid_date(value_str):
            try:
                # Prova diversi formati di data
                formats = ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
                
                for fmt in formats:
                    try:
                        parsed_date = datetime.strptime(value_str, fmt)
                        return parsed_date.date()
                    except ValueError:
                        continue
                        
            except Exception:
                pass
        
        return None
    
    def _parse_date_field(self, value: Any) -> Optional[date]:
        """
        Parse generico per campi data
        """
        return self._parse_availability_date(value)
    
    def _is_valid_date(self, value_str: str) -> bool:
        """
        Verifica se una stringa rappresenta una data valida
        """
        try:
            # Pattern base per date
            date_patterns = [
                r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
                r'\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
                r'\d{1,2}/\d{1,2}/\d{4}',  # D/M/YYYY
            ]
            
            for pattern in date_patterns:
                if re.search(pattern, value_str):
                    return True
            
            return False
        except Exception:
            return False
    
    def _is_country_available(self, value: Any) -> bool:
        """
        Determina se il paese è disponibile per questo prodotto
        """
        if pd.isna(value):
            return False
            
        value_str = str(value).strip().upper()
        
        # I paesi sono disponibili se hanno:
        # - AAP (As Available)
        # - Una data specifica
        # - TBD/TBC (To Be Determined/Confirmed)
        
        return value_str in ['AAP', 'TBD', 'TBC'] or self._is_valid_date(value_str)
