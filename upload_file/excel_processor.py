#!/usr/bin/env python3
"""
Processore principale per file Excel di pianificazione
Converte Excel in CSV, pulisce i dati e estrae informazioni sui paesi
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime, date
from typing import Dict, List, Set, Tuple, Optional, Any
import logging
import os

# Configurazione logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExcelProcessor:
    """
    Processore principale per file Excel di pianificazione
    """
    
    def __init__(self):
        self.all_countries = self._get_all_countries()
        self.country_columns = {}
        self.header_row = 0
        
    def _get_all_countries(self) -> List[str]:
        """
        Ritorna tutti i possibili paesi dall'e-commerce
        """
        return [
            'AL', 'AM', 'AT', 'AZ', 'BA', 'BE', 'BG', 'BH', 'BR', 'BY', 'CH', 'CN', 'CO', 'CY', 'CZ', 
            'DE', 'DK', 'EE', 'ES', 'FL', 'FR', 'GB', 'GE', 'GR', 'HK', 'HR', 'HU', 'IE', 'IL', 
            'IT', 'JO', 'JP', 'KW', 'KZ', 'LB', 'LT', 'LU', 'LV', 'MA', 'MD', 'MK', 'MO', 'MT', 
            'MX', 'NL', 'PL', 'PT', 'QA', 'RO', 'RS', 'RU', 'SA', 'SE', 'SI', 'SK', 'TN', 'TR', 
            'TW', 'UA', 'UK', 'US', 'UZ', 'XK'
        ]
    
    def excel_to_csv(self, excel_file_path: str, output_csv_path: str) -> str:
        """
        Converte file Excel in CSV in modo robusto
        """
        try:
            logger.info(f"Conversione Excel in CSV: {excel_file_path}")

            if not os.path.exists(excel_file_path):
                raise FileNotFoundError(f"File non trovato: {excel_file_path}")

            # Controlla l'estensione del file
            supported_extensions = ('.xlsx', '.xls', '.xlsm', '.xlsb', '.odf', '.ods', '.odt')
            if not excel_file_path.lower().endswith(supported_extensions):
                raise ValueError(f"Formato file non supportato: {excel_file_path}")

            # Leggi il file Excel
            excel_data = pd.read_excel(excel_file_path, header=None, sheet_name=None)

            # Se ci sono più fogli, uniscili o scegli il primo
            if isinstance(excel_data, dict):
                logger.info(f"Trovati {len(excel_data)} fogli. Verrà utilizzato il primo foglio.")
                # Unisci tutti i fogli in un unico DataFrame
                all_sheets = []
                for sheet_name, df in excel_data.items():
                    all_sheets.append(df)
                excel_data = pd.concat(all_sheets, ignore_index=True)
            
            # Salva come CSV
            excel_data.to_csv(output_csv_path, index=False, header=False)
            
            logger.info(f"CSV salvato: {output_csv_path}")
            return output_csv_path
            
        except FileNotFoundError as e:
            logger.error(f"Errore: file non trovato - {e}")
            raise
        except ValueError as e:
            logger.error(f"Errore: formato file non valido - {e}")
            raise
        except Exception as e:
            logger.error(f"Errore imprevisto nella conversione Excel: {e}", exc_info=True)
            raise
    
    def clean_csv_data(self, csv_file_path: str) -> Tuple[pd.DataFrame, str]:
        """
        Pulisce i dati CSV e trova l'header
        Ritorna il DataFrame pulito e il tipo di file rilevato
        """
        try:
            logger.info(f"Pulizia dati CSV: {csv_file_path}")
            
            # Carica il CSV
            df = pd.read_csv(csv_file_path, header=None)
            logger.info(f"   Dimensioni originali: {df.shape}")
            
            # Rileva il tipo di file
            file_type = self._detect_file_type(df)
            logger.info(f"   Tipo file rilevato: {file_type}")
            
            # Trova l'header
            self.header_row = self._find_header_row(df)
            if self.header_row == -1:
                raise ValueError("Header non trovato nel file CSV")
            
            # Rimuovi righe vuote prima dell'header
            df = df.iloc[self.header_row:].reset_index(drop=True)
            
            # Imposta l'header
            df.columns = df.iloc[0]
            df = df.iloc[1:].reset_index(drop=True)
            
            # Rimuovi righe completamente vuote
            df = df.dropna(how='all')
            
            # Rimuovi colonne completamente vuote
            df = df.dropna(axis=1, how='all')
            
            logger.info(f"   Dimensioni pulite: {df.shape}")
            logger.info(f"   Header trovato alla riga: {self.header_row}")
            
            return df, file_type
            
        except Exception as e:
            logger.error(f"Errore nella pulizia CSV: {e}")
            raise
    
    def _detect_file_type(self, df: pd.DataFrame) -> str:
        """
        Rileva il tipo di file: 'detail' per file dettagliato, 'pivot' per tabella pivot
        """
        # Cerca indicatori di file dettagliato
        for idx in range(min(10, len(df))):
            row_str = ' '.join(str(x) for x in df.iloc[idx].values if pd.notna(x)).lower()
            if 'chiave articolo colore' in row_str:
                return 'detail'
        
        # Cerca indicatori di tabella pivot
        for idx in range(min(10, len(df))):
            row_str = ' '.join(str(x) for x in df.iloc[idx].values if pd.notna(x)).lower()
            if 'categorie' in row_str and 'tranche' in row_str:
                return 'pivot'
        
        # Default: assume dettagliato
        return 'detail'
    
    def _find_header_row(self, df: pd.DataFrame) -> int:
        """
        Trova la riga header
        """
        # Per file dettagliato
        for idx in range(min(10, len(df))):
            row_str = ' '.join(str(x) for x in df.iloc[idx].values if pd.notna(x)).lower()
            if 'chiave articolo colore' in row_str:
                logger.info(f"   Header trovato alla riga {idx}")
                return idx
        
        # Per tabella pivot
        for idx in range(min(10, len(df))):
            row_str = ' '.join(str(x) for x in df.iloc[idx].values if pd.notna(x)).lower()
            if 'categorie' in row_str:
                logger.info(f"   Header tabella pivot trovato alla riga {idx}")
                return idx
        
        logger.error("   Header non trovato")
        return -1

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
    
    def identify_country_columns(self, df: pd.DataFrame) -> Dict[str, Dict]:
        """
        Identifica le colonne che contengono informazioni sui paesi
        """
        logger.info("Identificazione colonne paese...")
        
        headers = df.columns.tolist()
        country_columns = {}
        
        country_pattern = re.compile(r'((?:[A-Z]{2}[/-\\s]?)+)')

        for idx, header in enumerate(headers):
            if pd.isna(header):
                continue
                
            header_str = str(header).strip()
            
            match = country_pattern.search(header_str)
            if match:
                countries_str = match.group(1)
                countries_in_header = re.findall(r'[A-Z]{2}', countries_str)
                
                # Filtra solo i paesi validi
                valid_countries = [c for c in countries_in_header if c in self.all_countries]
                
                if valid_countries:
                    country_columns[header_str] = {
                        'column_index': idx,
                        'countries': valid_countries,
                        'column_name': header_str
                    }
                    logger.info(f"   Colonna {idx}: '{header_str}' -> {valid_countries}")
        
        self.country_columns = country_columns
        logger.info(f"   Trovate {len(country_columns)} colonne paese")
        return country_columns
    
    def extract_product_data(self, df: pd.DataFrame, file_type: str = 'detail') -> List[Dict]:
        """
        Estrae i dati dei prodotti con le informazioni sui paesi
        """
        logger.info("Estrazione dati prodotti...")
        
        if file_type == 'pivot':
            return self._extract_pivot_data(df)
        else:
            return self._extract_detail_data(df)
    
    def _extract_detail_data(self, df: pd.DataFrame) -> List[Dict]:
        """
        Estrae dati da file dettagliato
        """
        products_data = []
        
        for idx, row in df.iterrows():
            try:
                # Estrai dati base del prodotto
                product_data = self._extract_base_product_data(row)
                
                # Estrai informazioni sui paesi
                country_data = self._extract_country_data(row)
                
                # Combina i dati
                product_data.update(country_data)
                
                products_data.append(product_data)
                
            except Exception as e:
                logger.warning(f"   Errore nell'estrazione riga {idx}: {e}")
                continue
        
        logger.info(f"   Estratti {len(products_data)} prodotti")
        return products_data
    
    def _extract_pivot_data(self, df: pd.DataFrame) -> List[Dict]:
        """
        Estrae dati da tabella pivot
        """
        products_data = []
        
        # Trova le colonne delle tranche (numeriche)
        tranche_columns = []
        for col in df.columns:
            if pd.notna(col) and str(col).replace('.', '').isdigit():
                tranche_columns.append(col)
        
        logger.info(f"   Trovate {len(tranche_columns)} colonne tranche: {tranche_columns}")
        
        for idx, row in df.iterrows():
            try:
                categoria = str(row.iloc[0]) if pd.notna(row.iloc[0]) else ''
                
                # Salta righe di totale o vuote
                if not categoria or 'totale' in categoria.lower() or categoria.startswith('CONT -'):
                    continue
                
                # Per ogni tranche con dati
                for tranche_col in tranche_columns:
                    if tranche_col in row.index and pd.notna(row[tranche_col]) and row[tranche_col] != 0:
                        product_data = {
                            'chiave_articolo': f"{categoria}_{tranche_col}",
                            'concatena_magazzino': '',
                            'serie': '',
                            'merceologia': categoria,
                            'n_tranche': str(tranche_col),
                            'stagione': '',
                            'sku': f"{categoria}_{tranche_col}",
                            'articolo': categoria,
                            'colore': '',
                            'taglia': '',
                            'descrizione': categoria,
                            'data_inizio_consegna': None,
                            'data_spedizione_reale': None,
                            'impianti_per': '',
                            'note_ufficio': '',
                            'data_consegna_fornitore': None,
                            'fornitore': '',
                            'codice_forn': '',
                            'made_in': '',
                            'impianti_russia': '',
                            'ocli_mondo_russia': '',
                            'anticipi_milano': '',
                            'impianto_russia_startup': '',
                            'stock_l': '',
                            'stock_cq': '',
                            'stock_b': '',
                            'ocli': '',
                            'esistenza': '',
                            'stock_l_cq_ocli': '',
                            'x_per_pv_foto': '',
                            'stock_cq_2': '',
                            'categorie': categoria,
                            'note_categorie': '',
                            'ecommerce_visibility': '',
                            'quantita': str(row[tranche_col]),
                            'paesi_disponibili': self.all_countries,  # Tutti i paesi per default
                            'date_paesi': {},
                            'paesi_aap': self.all_countries,  # Assume AAP per tutti
                            'paesi_con_date': []
                        }
                        
                        products_data.append(product_data)
                
            except Exception as e:
                logger.warning(f"   Errore nell'estrazione riga {idx}: {e}")
                continue
        
        logger.info(f"   Estratti {len(products_data)} prodotti dal pivot")
        return products_data
    
    def _extract_base_product_data(self, row: pd.Series) -> Dict:
        """
        Estrae i dati base del prodotto
        """
        headers = row.index.tolist()
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
            'descrizione': self._safe_get_value(row, headers, 'Descrizione articolo', ''),
            'data_inizio_consegna': self._parse_date(self._safe_get_value(row, headers, 'DATA INIZIO CONSEGNA AI P.V. (ORIGINARIA)')),
            'data_spedizione_reale': self._parse_date(self._safe_get_value(row, headers, 'DATA SPEDIZIONE REALE STANDARD (PIM)')),
            'impianti_per': self._safe_get_value(row, headers, 'IMPIANTI PER', ''),
            'note_ufficio': self._safe_get_value(row, headers, 'NOTE UFFICIO COMMERCIALE', ''),
            'data_consegna_fornitore': self._parse_date(self._safe_get_value(row, headers, 'DATA CONSEGNA FORNITORE PRIMO 60%')),
            'fornitore': self._safe_get_value(row, headers, 'FORNITORE', ''),
            'codice_forn': self._safe_get_value(row, headers, 'CODICE FORN', ''),
            'made_in': self._safe_get_value(row, headers, 'MADE IN', ''),
            'impianti_russia': self._safe_get_value(row, headers, 'IMPIANTI RUSSIA PER DOGANALE', ''),
            'ocli_mondo_russia': self._safe_get_value(row, headers, 'OCLI (MONDO+RUSSIA)', ''),
            'anticipi_milano': self._safe_get_value(row, headers, 'ANTICIPI MILANO', ''),
            'impianto_russia_startup': self._safe_get_value(row, headers, 'IMPIANTO PER RUSSIA (START UP ORDERS)', ''),
            'stock_l': self._safe_get_value(row, headers, 'STOCK L', ''),
            'stock_cq': self._safe_get_value(row, headers, 'STOCK CQ', ''),
            'stock_b': self._safe_get_value(row, headers, 'STOCK B', ''),
            'ocli': self._safe_get_value(row, headers, 'OCLI', ''),
            'esistenza': self._safe_get_value(row, headers, 'ESISTENZA', ''),
            'stock_l_cq_ocli': self._safe_get_value(row, headers, 'Stock L+Stock CQ - Ocli', ''),
            'x_per_pv_foto': self._safe_get_value(row, headers, '""X"" PER PV FOTO', ''),
            'stock_cq_2': self._safe_get_value(row, headers, 'STOCK CQ', ''),
            'categorie': self._safe_get_value(row, headers, 'CATEGORIE', ''),
            'note_categorie': self._safe_get_value(row, headers, 'NOTE CATEGORIE', ''),
            'ecommerce_visibility': self._safe_get_value(row, headers, 'E-COMMERCE VISIBILITY (COUNTRIES)', ''),
        }
    
    def _extract_country_data(self, row: pd.Series) -> Dict:
        """
        Estrae le informazioni sui paesi
        """
        country_data = {
            'paesi_disponibili': [],
            'date_paesi': {},
            'paesi_aap': [],
            'paesi_con_date': []
        }
        
        for header_name, col_info in self.country_columns.items():
            col_idx = col_info['column_index']
            countries = col_info['countries']
            
            if col_idx < len(row):
                cell_value = row.iloc[col_idx]
                
                # Aggiungi paesi alla lista generale
                country_data['paesi_disponibili'].extend(countries)
                
                # Gestisci il valore della cella
                if pd.isna(cell_value) or str(cell_value).strip() == '':
                    continue
                
                cell_str = str(cell_value).strip()
                
                if cell_str.upper() == 'AAP':
                    # Paesi con disponibilità "As Available"
                    country_data['paesi_aap'].extend(countries)
                elif self._is_valid_date(cell_str):
                    # Paesi con data specifica
                    parsed_date = self._parse_date(cell_str)
                    if parsed_date:
                        for country in countries:
                            country_data['date_paesi'][country] = parsed_date
                            country_data['paesi_con_date'].append(country)
        
        # Rimuovi duplicati
        country_data['paesi_disponibili'] = list(set(country_data['paesi_disponibili']))
        country_data['paesi_aap'] = list(set(country_data['paesi_aap']))
        country_data['paesi_con_date'] = list(set(country_data['paesi_con_date']))
        
        return country_data
    
    def _parse_date(self, value) -> Optional[str]:
        """
        Converte un valore in data
        """
        if pd.isna(value) or str(value).strip() == '':
            return None
        
        try:
            # Prova a parsare come datetime
            if isinstance(value, str):
                # Rimuovi spazi extra
                value = value.strip()
                
                # Gestisci formati comuni
                if 'AAP' in value.upper():
                    return 'AAP'
                
                # Prova diversi formati di data
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        parsed = datetime.strptime(value, fmt)
                        return parsed.strftime('%Y-%m-%d')
                    except ValueError:
                        continue
                
                # Se non riesce a parsare, ritorna il valore originale
                return value
            else:
                # Se è già un datetime
                if hasattr(value, 'strftime'):
                    return value.strftime('%Y-%m-%d')
                else:
                    return str(value)
                    
        except Exception:
            return str(value)
    
    def _is_valid_date(self, value: str) -> bool:
        """
        Verifica se una stringa è una data valida
        """
        if not value or value.upper() == 'AAP':
            return False
        
        try:
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                try:
                    datetime.strptime(value, fmt)
                    return True
                except ValueError:
                    continue
            return False
        except Exception:
            return False
    
    def save_processed_data(self, products_data: List[Dict], output_file: str):
        """
        Salva i dati processati in CSV
        """
        try:
            logger.info(f"Salvataggio dati processati: {output_file}")
            
            # Converti in DataFrame
            df = pd.DataFrame(products_data)
            
            # Salva come CSV
            df.to_csv(output_file, index=False)
            
            logger.info(f"Dati salvati: {len(products_data)} prodotti")
            
        except Exception as e:
            logger.error(f"Errore nel salvataggio: {e}")
            raise
    
    def process_excel_file(self, excel_file_path: str, output_dir: str = None) -> Dict:
        """
        Processo completo: Excel -> CSV -> Dati puliti -> Risultato
        """
        try:
            logger.info(f"Avvio processamento file: {excel_file_path}")
            
            # Crea directory di output se non esiste
            if output_dir is None:
                output_dir = os.path.dirname(excel_file_path)
            
            os.makedirs(output_dir, exist_ok=True)
            
            # Nomi file di output
            base_name = os.path.splitext(os.path.basename(excel_file_path))[0]
            csv_file = os.path.join(output_dir, f"{base_name}.csv")
            processed_file = os.path.join(output_dir, f"{base_name}_processed.csv")
            
            # 1. Converti Excel in CSV
            self.excel_to_csv(excel_file_path, csv_file)
            
            # 2. Pulisci i dati CSV
            df, file_type = self.clean_csv_data(csv_file)
            
            # 3. Identifica colonne paese (solo per file dettagliato)
            if file_type == 'detail':
                self.identify_country_columns(df)
            
            # 4. Estrai dati prodotti
            products_data = self.extract_product_data(df, file_type)
            
            # 5. Salva risultati
            self.save_processed_data(products_data, processed_file)
            
            # Statistiche
            stats = {
                'file_originale': excel_file_path,
                'file_csv': csv_file,
                'file_processato': processed_file,
                'totale_prodotti': len(products_data),
                'colonne_paese_trovate': len(self.country_columns),
                'paesi_totali': len(set([p for prod in products_data for p in prod.get('paesi_disponibili', [])])),
                'prodotti_con_date': len([p for p in products_data if p.get('paesi_con_date')]),
                'prodotti_aap': len([p for p in products_data if p.get('paesi_aap')])
            }
            
            logger.info(f"Processamento completato!")
            logger.info(f"   Statistiche: {stats}")
            
            return {
                'success': True,
                'stats': stats,
                'files': {
                    'csv': csv_file,
                    'processed': processed_file
                },
                'data': products_data
            }
            
        except Exception as e:
            logger.error(f"Errore nel processamento: {e}")
            return {
                'success': False,
                'error': str(e)
            }
