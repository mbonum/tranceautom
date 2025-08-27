#!/usr/bin/env python3
"""
Correct Country Planning Processor - VERSIONE DEFINITIVA
Risolve tutti i problemi di gestione delle date e dei paesi raggruppati
"""

import re
import logging
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
from .models import Prodotto, PaesePianificazione

logger = logging.getLogger(__name__)


class CorrectCountryPlanningProcessor:
    """
    Processore corretto per l'estrazione dei dati per singolo country
    VERSIONE DEFINITIVA - Gestione corretta delle date e paesi raggruppati
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
        logger.info("Inizializzando CorrectCountryPlanningProcessor")
        self.country_to_column_mapping = {}
        self.headers_processed = False
        
    def process_csv_file(self, csv_file_path: str) -> pd.DataFrame:
        """
        Processa il file CSV e restituisce un DataFrame corretto
        VERSIONE MIGLIORATA - Con pre-processing
        """
        logger.info(f"Processamento file CSV: {csv_file_path}")
        
        try:
            # 1. Pre-processing del CSV
            df = self._preprocess_csv(csv_file_path)
            
            # 2. Identifica l'header con i gruppi di paesi
            header_row_idx = self._find_header_row_with_countries(df)
            logger.info(f"Header identificato alla riga {header_row_idx}")
            
            # 3. Estrai l'header e i dati
            headers = df.iloc[header_row_idx].tolist()
            data_df = df.iloc[header_row_idx + 1:].reset_index(drop=True)
            
            # 4. Assicurati che il DataFrame dati abbia tutte le colonne dell'header
            while len(data_df.columns) < len(headers):
                data_df[f'col_{len(data_df.columns)}'] = ''
            
            # 5. Rinomina le colonne con l'header
            data_df.columns = headers
            
            logger.info(f"DataFrame processato: {len(data_df)} righe, {len(data_df.columns)} colonne")
            
            return data_df
            
        except Exception as e:
            logger.error(f"Errore nel processamento del CSV: {str(e)}")
            raise
    
    def _preprocess_csv(self, csv_file_path: str) -> pd.DataFrame:
        """
        Pre-processing del CSV per migliorare la qualità
        """
        # Leggi il CSV originale
        df = pd.read_csv(csv_file_path, header=None)
        logger.info(f"CSV originale: {len(df)} righe, {len(df.columns)} colonne")
        
        # Rimuovi righe completamente vuote
        df = df.dropna(how='all')
        
        # Rimuovi righe con solo spazi
        df = df[df.apply(lambda row: 
            not all(str(cell).strip() == '' for cell in row if pd.notna(cell)), axis=1)]
        
        logger.info(f"CSV pre-processato: {len(df)} righe, {len(df.columns)} colonne")
        return df
    
    def _find_header_row_with_countries(self, df: pd.DataFrame) -> int:
        """
        Trova la riga che contiene l'header con gruppi di paesi
        """
        for idx, row in df.iterrows():
            row_str = ' '.join([str(cell) for cell in row if pd.notna(cell)])
            if self._contains_country_groups(row_str):
                return idx
        
        # Se non trova gruppi di paesi, usa la prima riga
        logger.warning("Nessun header con gruppi di paesi trovato, uso la prima riga")
        return 0
    
    def _contains_country_groups(self, text: str) -> bool:
        """
        Verifica se il testo contiene gruppi di paesi
        """
        # Pattern per gruppi di paesi (es: AL-BG-BY-CY-EE)
        import re
        country_group_pattern = r'[A-Z]{2}(-[A-Z]{2}){2,}'
        return bool(re.search(country_group_pattern, text))
    
    def _find_header_row(self, df: pd.DataFrame) -> Optional[int]:
        """
        Trova la riga che contiene l'header (prima riga con colonne paese)
        """
        for idx, row in df.iterrows():
            row_str = ' '.join([str(cell) for cell in row if pd.notna(cell)])
            if self._contains_country_codes(row_str):
                return idx
        return None
    
    def _contains_country_codes(self, text: str) -> bool:
        """
        Verifica se il testo contiene codici paese
        """
        text_upper = text.upper()
        for country in self.ALL_COUNTRIES:
            if country in text_upper:
                return True
        return False
    
    def identify_country_columns(self, headers: List[str], df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Identifica le colonne che contengono paesi e mappa ogni paese alla sua colonna
        VERSIONE MIGLIORATA - Cerca nell'header e nelle righe successive
        """
        logger.info(f"Identificazione colonne paese da {len(headers)} headers...")
        
        country_columns = {}
        
        # PRIMA: Cerca nell'header (riga 0) per i gruppi di paesi
        logger.info("   Cercando nell'header (riga 0)...")
        for col_idx, header_value in enumerate(headers):
            if pd.notna(header_value) and isinstance(header_value, str):
                header_str = str(header_value).strip()
                countries_in_header = self._extract_countries_from_header(header_str)
                
                if countries_in_header:
                    country_columns[header_str] = {
                        'column_index': col_idx,
                        'countries': countries_in_header,
                        'header_name': header_str,
                        'row_found': 0
                    }
                    
                    # Mappa ogni paese alla sua colonna
                    for country in countries_in_header:
                        self.country_to_column_mapping[country] = {
                            'column_index': col_idx,
                            'header_name': header_str,
                            'all_countries_in_group': countries_in_header,
                            'row_found': 0
                        }
                    
                    logger.info(f"   Colonna {col_idx} (header): '{header_str}' -> {len(countries_in_header)} paesi")
        
        # SECONDA: Cerca nelle prime 50 righe di dati per trovare altri codici paese
        logger.info("   Cercando nelle righe di dati...")
        for row_idx in range(min(50, len(df))):
            row = df.iloc[row_idx]
            for col_idx, cell_value in enumerate(row):
                if pd.isna(cell_value) or str(cell_value).strip() == '':
                    continue
                    
                cell_str = str(cell_value).strip()
                
                # Estrai i paesi da questa cella
                countries_in_cell = self._extract_countries_from_header(cell_str)
                
                if countries_in_cell:
                    # Usa l'header della colonna come nome
                    header_name = headers[col_idx] if col_idx < len(headers) else f'Colonna_{col_idx}'
                    
                    # Mappa ogni paese alla sua colonna (solo se non già mappato)
                    for country in countries_in_cell:
                        if country not in self.country_to_column_mapping:
                            self.country_to_column_mapping[country] = {
                                'column_index': col_idx,
                                'header_name': header_name,
                                'all_countries_in_group': countries_in_cell,
                                'row_found': row_idx
                            }
                    
                    # Aggiorna country_columns solo se non già presente
                    if cell_str not in country_columns:
                        country_columns[cell_str] = {
                            'column_index': col_idx,
                            'countries': countries_in_cell,
                            'header_name': header_name,
                            'row_found': row_idx
                        }
                        logger.info(f"   Colonna {col_idx} (riga {row_idx}): '{cell_str}' -> {len(countries_in_cell)} paesi")
        
        logger.info(f"   Trovate {len(country_columns)} colonne paese")
        logger.info(f"   Mappati {len(self.country_to_column_mapping)} paesi singoli")
        
        self.headers_processed = True
        return country_columns
    
    def _extract_countries_from_header(self, header: str) -> List[str]:
        """
        Estrae i codici paese da un header
        VERSIONE MIGLIORATA
        """
        countries = []
        
        # Split per separatori comuni
        parts = re.split(r'[-_\s,;|()]+', header.upper())
        
        for part in parts:
            part = part.strip()
            # Verifica se è un codice paese valido (2-3 caratteri alfabetici)
            if len(part) >= 2 and len(part) <= 3 and part.isalpha():
                if part in self.ALL_COUNTRIES:
                    countries.append(part)
                else:
                    logger.debug(f"Codice paese sconosciuto in header: {part}")
                    
        return countries
    
    def create_country_plannings(self, prodotto: Prodotto, 
                               row_data: List[Any],
                               headers: List[str],
                               df: pd.DataFrame = None) -> List[Dict[str, Any]]:
        """
        Crea record di pianificazione paese per un prodotto
        VERSIONE CORRETTA - Gestione corretta delle date
        """
        logger.info(f"INIZIO correct country processing per {prodotto.codice_forn}")
        logger.info(f"   Row data length: {len(row_data)}")

        countries_data = []
        
        try:
            # Identifica le colonne paese se non già fatto
            if not self.headers_processed:
                self.identify_country_columns(headers, df)
            
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
                        logger.debug(f"   {country}: {processed_value['date']} ({processed_value['date_type']})")
                else:
                    logger.warning(f"   {country}: Colonna {col_idx} non disponibile")
                    
            logger.info(f"SUCCESS: Creati {len(countries_data)} country plannings per {prodotto.codice_forn}")
            
        except Exception as e:
            logger.error(f"ERRORE creating country plannings per {prodotto.codice_forn}: {str(e)}", exc_info=True)
            
        return countries_data
    
    def _process_cell_value(self, cell_value: Any) -> Dict[str, Any]:
        """
        Processa il valore di una cella e restituisce data e tipo
        VERSIONE CORRETTA - Gestione corretta delle date
        """
        if cell_value is None or pd.isna(cell_value) or str(cell_value).strip() == '':
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
        VERSIONE MIGLIORATA - Gestisce tutti i formati dal CSV
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
        VERSIONE CORRETTA - Gestione corretta delle date
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
                    source_column=data['source_column'],
                    source_group=data['source_header']
                )
                
                # Salva nel database
                paese_planning.save()
                saved_objects.append(paese_planning)
                
                logger.debug(f"   Salvato: {data['country_code']} -> {availability_date} ({data['date_type']})")
                
            except Exception as e:
                logger.error(f"   Errore salvataggio {data['country_code']}: {str(e)}")
        
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
