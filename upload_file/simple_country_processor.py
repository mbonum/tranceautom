#!/usr/bin/env python3
"""
Simple Country Planning Processor - VERSIONE COMPLETAMENTE RISCITTA
Gestione corretta delle date reali dal CSV
"""

import re
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, date
from .models import Prodotto, PaesePianificazione

logger = logging.getLogger(__name__)


class SimpleCountryPlanningProcessor:
    """
    Processore semplificato per l'estrazione dei dati per singolo country
    VERSIONE COMPLETAMENTE RISCITTA - Gestione corretta delle date
    """
    
    # Lista completa dei paesi supportati
    ALL_COUNTRIES = [
        'AL', 'AM', 'AT', 'AZ', 'BA', 'BE', 'BG', 'BH', 'BR', 'BY', 'CH', 'CN', 'CO', 'CY', 'CZ', 
        'DE', 'DK', 'EE', 'ES', 'FL', 'FR', 'GB', 'GE', 'GR', 'HK', 'HR', 'HU', 'IE', 'IL', 
        'IT', 'JO', 'JP', 'KW', 'KZ', 'LB', 'LT', 'LU', 'LV', 'MA', 'MD', 'MK', 'MO', 'MT', 
        'MX', 'NL', 'PL', 'PT', 'QA', 'RO', 'RS', 'RU', 'SA', 'SE', 'SI', 'SK', 'TN', 'TR', 
        'TW', 'UA', 'UK', 'US', 'UZ', 'XK'
    ]
    
    def __init__(self):
        logger.info(f"Inizializzando SimpleCountryPlanningProcessor")
        self.country_to_column_mapping = {}
        
    def identify_country_columns(self, headers: List[str]) -> Dict[str, Dict]:
        """
        Identifica le colonne che contengono paesi e mappa ogni paese alla sua colonna
        """
        logger.info(f"🔍 Identificazione colonne paese da {len(headers)} headers...")
        
        country_columns = {}
        
        for col_idx, header in enumerate(headers):
            if not header or header != header:  # Check for NaN
                continue
                
            header_str = str(header).strip()
            
            # Estrai i paesi da questo header
            countries_in_header = self._extract_countries_from_header(header_str)
            
            if countries_in_header:
                country_columns[header_str] = {
                    'column_index': col_idx,
                    'countries': countries_in_header,
                    'header_name': header_str
                }
                
                # Mappa ogni paese alla sua colonna
                for country in countries_in_header:
                    self.country_to_column_mapping[country] = {
                        'column_index': col_idx,
                        'header_name': header_str,
                        'all_countries_in_group': countries_in_header
                    }
                
                logger.info(f"   OK Colonna {col_idx}: '{header_str}' -> {len(countries_in_header)} paesi")
        
        logger.info(f"   Trovate {len(country_columns)} colonne paese")
        logger.info(f"   Mappati {len(self.country_to_column_mapping)} paesi singoli")
        
        return country_columns
    
    def _extract_countries_from_header(self, header: str) -> List[str]:
        """
        Estrae i codici paese da un header
        Esempi:
        - "AL-BG-BY-CY-EE" -> ["AL", "BG", "BY", "CY", "EE"]
        - "AE AM AZ BA BH" -> ["AE", "AM", "AZ", "BA", "BH"]
        """
        countries = []
        
        # Split per separatori comuni
        parts = re.split(r'[-_\s,;|]+', header.upper())
        
        for part in parts:
            part = part.strip()
            # Verifica se è un codice paese valido (2-3 caratteri alfabetici)
            if len(part) >= 2 and len(part) <= 3 and part.isalpha():
                if part in self.ALL_COUNTRIES:
                    countries.append(part)
                else:
                    logger.warning(f"Codice paese sconosciuto in header: {part}")
                    
        return countries
    
    def create_country_plannings(self, prodotto: Prodotto, 
                               row_data: List[Any],
                               headers: List[str]) -> List[Dict[str, Any]]:
        """
        Crea record di pianificazione paese per un prodotto
        VERSIONE COMPLETAMENTE RISCITTA - Gestione corretta delle date
        """
        logger.info(f"INIZIO simple country processing per {prodotto.codice_forn}")
        logger.info(f"   Row data length: {len(row_data)}")

        countries_data = []
        
        try:
            # Processa solo i paesi che sono effettivamente presenti nelle colonne
            processed_countries = 0
            
            for country in self.country_to_column_mapping.keys():
                # Trova la colonna per questo paese
                col_info = self.country_to_column_mapping[country]
                col_idx = col_info['column_index']
                
                # Estrai il valore dalla cella
                if col_idx < len(row_data):
                    cell_value = row_data[col_idx]
                    
                    # Processa il valore della cella
                    processed_value = self._process_cell_value(cell_value)
                    
                    # Crea il record per questo paese
                    planning_data = {
                        'prodotto': prodotto,
                        'country_code': country,
                        'availability_date': processed_value['date'],
                        'date_type': processed_value['date_type'],
                        'source_column': col_idx,
                        'source_header': col_info['header_name'],
                        'country_group': ','.join(col_info['all_countries_in_group']),
                        'raw_value': str(cell_value) if cell_value is not None else ''
                    }
                    
                    countries_data.append(planning_data)
                    processed_countries += 1
                    
                    # Log solo per i primi 10 paesi per evitare spam
                    if processed_countries <= 10:
                        logger.debug(f"   OK {country}: {processed_value['date']} ({processed_value['date_type']})")
                else:
                    logger.warning(f"   ERR {country}: Colonna {col_idx} non disponibile")
                    
            logger.info(f"SUCCESS: Creati {len(countries_data)} country plannings per {prodotto.codice_forn}")
            
        except Exception as e:
            logger.error(f"ERRORE creating country plannings per {prodotto.codice_forn}: {str(e)}", exc_info=True)
            
        return countries_data
    
    def _process_cell_value(self, cell_value: Any) -> Dict[str, Any]:
        """
        Processa il valore di una cella e restituisce data e tipo
        VERSIONE COMPLETAMENTE RISCITTA
        """
        if cell_value is None or str(cell_value).strip() == '':
            return {
                'date': None,
                'date_type': 'empty'
            }
        
        cell_str = str(cell_value).strip()
        
        # 1. Gestisci valori speciali
        if cell_str.upper() in ['AAP', 'ASAP']:
            return {
                'date': None,
                'date_type': 'immediate'
            }
        
        if cell_str.upper() in ['TBD', 'TBC']:
            return {
                'date': None,
                'date_type': 'tbd'
            }
        
        # 2. Prova a parsare come data
        parsed_date = self._parse_date(cell_str)
        if parsed_date:
            return {
                'date': parsed_date,
                'date_type': 'scheduled'
            }
        
        # 3. Se non è una data valida, tratta come valore speciale
        return {
            'date': None,
            'date_type': 'unknown'
        }
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        Prova a parsare una stringa come data
        Gestisce tutti i formati possibili dal CSV
        """
        if not date_str or date_str.strip() == '':
            return None
        
        # Rimuovi spazi extra
        date_str = date_str.strip()
        
        # Lista di formati di data da provare
        date_formats = [
            '%Y-%m-%d %H:%M:%S',  # 2025-06-12 00:00:00
            '%Y-%m-%d',           # 2025-06-12
            '%d/%m/%Y',           # 12/06/2025
            '%m/%d/%Y',           # 06/12/2025
            '%d-%m-%Y',           # 12-06-2025
            '%m-%d-%Y',           # 06-12-2025
            '%Y/%m/%d',           # 2025/06/12
            '%d %B %Y',           # 12 June 2025
            '%d %b %Y',           # 12 Jun 2025
            '%B %d, %Y',          # June 12, 2025
            '%b %d, %Y',          # Jun 12, 2025
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                return parsed_date.date()
            except ValueError:
                continue
        
        # Se nessun formato funziona, prova con regex per date ISO
        iso_pattern = r'(\d{4})-(\d{1,2})-(\d{1,2})'
        match = re.match(iso_pattern, date_str)
        if match:
            try:
                year, month, day = map(int, match.groups())
                return date(year, month, day)
            except ValueError:
                pass
        
        return None
    
    def save_to_database(self, countries_data: List[Dict[str, Any]]) -> List[PaesePianificazione]:
        """
        Salva i dati nel database Django
        VERSIONE COMPLETAMENTE RISCITTA - Gestione corretta delle date
        """
        logger.info(f"Salvataggio {len(countries_data)} record nel database...")
        
        saved_objects = []
        
        for data in countries_data:
            try:
                # Gestisci la data in base al tipo
                availability_date = self._get_availability_date(data['availability_date'], data['date_type'])
                
                # Crea l'oggetto PaesePianificazione
                paese_planning = PaesePianificazione(
                    prodotto=data['prodotto'],
                    codice_paese=data['country_code'],
                    data_disponibilita=availability_date,
                    data_tipo=data['date_type'],
                    source_column=data['source_column'],  # Già corretto: è col_idx (numero)
                    source_group=data['source_header']
                )
                
                # Salva nel database
                paese_planning.save()
                saved_objects.append(paese_planning)
                
                logger.debug(f"   OK Salvato: {data['country_code']} -> {availability_date} ({data['date_type']})")
                
            except Exception as e:
                logger.error(f"   ERR Errore salvataggio {data['country_code']}: {str(e)}")
        
        logger.info(f"   Salvati {len(saved_objects)} record nel database")
        return saved_objects
    
    def _get_availability_date(self, parsed_date: Optional[date], date_type: str) -> date:
        """
        Determina la data di disponibilità in base al tipo
        """
        if date_type == 'scheduled' and parsed_date:
            return parsed_date
        elif date_type == 'immediate':
            # Per ASAP, usa una data molto vicina
            return datetime.now().date()
        elif date_type == 'tbd':
            # Per TBD, usa una data lontana nel futuro
            return date(2030, 12, 31)
        else:
            # Per altri casi (empty, unknown, not_found), usa una data di default
            return date(2030, 12, 31)
