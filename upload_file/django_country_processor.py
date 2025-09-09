"""
Django Country Processor - Integration with Django database
Uses the new simple_country_processor and integrates it with Django models
"""

import pandas as pd
import os
from typing import Optional, Dict, List, Any
import logging
from django.db import transaction, models, IntegrityError
from django.conf import settings
from .models import PianificazioneImport, Prodotto, PaesePianificazione
from .simple_country_processor import (
    load_and_clean_excel_data,
    create_country_columns,
    get_countries_list,
    analyze_final_data,
)

logger = logging.getLogger(__name__)


class DjangoCountryProcessor:
    """
    Processor to integrate the new country processor with Django
    """

    def __init__(self):
        self.all_countries = get_countries_list()

    def process_excel_to_database(
        self, excel_file_path: str, import_record: PianificazioneImport
    ) -> Dict:
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

            # Validate import_record
            if (
                not isinstance(import_record, PianificazioneImport)
                or not import_record.pk
            ):
                raise ValueError("Invalid or unsaved `import_record` provided.")

            # Step 1: Load and clean Excel data
            df = load_and_clean_excel_data(excel_file_path)
            if df.empty:
                raise ValueError(
                    "Unable to load data from Excel file: The DataFrame is empty after cleaning."
                )

            # Step 2: Create country columns
            df_with_countries = create_country_columns(df)

            # Step 2.5: Apply E-commerce Visibility rules (NEW!)
            df_with_visibility = self._apply_visibility_rules(df_with_countries)

            # Step 3: Save CSV locally (optional)
            csv_path = self._save_processed_csv(df_with_visibility, import_record)

            # Step 4: Save to Django database
            stats = self._save_to_database(df_with_visibility, import_record)

            # Step 5: Update import record with CSV path
            import_record.status = "processed"
            import_record.total_products = stats["products_created"]
            import_record.total_countries = len(self.all_countries)
            import_record.csv_file_path = csv_path  # Save CSV path for reference
            import_record.save()

            logger.info(f"Processing completed for import {import_record.id}")
            logger.info(f"Products created: {stats['products_created']}")
            logger.info(f"Country records created: {stats['country_records_created']}")

            return stats

        except Exception as e:
            logger.error(f"Error in process_excel_to_database: {e}", exc_info=True)
            import_record.status = "error"
            import_record.error_message = str(e)
            import_record.save()
            raise e

    @transaction.atomic
    def _save_to_database(
        self, df: pd.DataFrame, import_record: PianificazioneImport
    ) -> Dict:
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
            country_columns = [col for col in df.columns if col.startswith("country_")]
            core_columns = [col for col in df.columns if not col.startswith("country_")]

            logger.info(f"Saving {len(df)} products to database...")

            # Validate DataFrame
            if df.empty:
                raise ValueError("Input DataFrame for database saving is empty.")

            # Definizione del mapping dei campi CORRETTA
            field_mapping = {
                "chiave_articolo": [
                    "chiave articolo colore x Uff. PIANIF",
                    "Chiave Articolo",
                    "chiave_articolo",
                ],
                "concatena_magazzino": [
                    "concatena 1 per MAGAZZINO",
                    "Concatena Magazzino",
                    "concatena_magazzino"
                ],
                "serie": ["Serie", "serie"],
                "merceologia": ["Merceologia", "merceologia"],
                "n_tranche": ["N. Tranche", "n_tranche", "tranche"],
                "stagione": ["Stag.", "Stagione", "stagione"],  # CORRETTO!
                "sku": ["SKU", "sku"],
                "articolo": ["Articolo", "articolo"],
                "colore": ["Colore", "colore"],
                "taglia": ["Taglia", "taglia"],
                "descrizione": [
                    "Descrizione articolo",  # CORRETTO!
                    "Descrizione",
                    "descrizione"
                ],
                "data_inizio_consegna": [
                    "DATA INIZIO CONSEGNA AI P.V. (ORIGINARIA)",  # CORRETTO!
                    "Data Inizio Consegna",
                    "data_inizio_consegna",
                ],
                "data_spedizione_reale": [
                    "DATA SPEDIZIONE REALE STANDARD (PIM)",  # CORRETTO!
                    "Data Spedizione Reale",
                    "data_spedizione_reale",
                ],
                "data_consegna_fornitore": [
                    "DATA CONSEGNA FORNITORE PRIMO 60%",  # CORRETTO!
                    "Data Consegna Fornitore",
                    "data_consegna_fornitore",
                ],
                "impianti_per": [
                    "IMPIANTI PER",  # CORRETTO!
                    "Impianti Per",
                    "impianti_per"
                ],
                "note_ufficio": [
                    "NOTE UFFICIO COMMERCIALE",  # CORRETTO!
                    "Note Ufficio",
                    "note_ufficio"
                ],
                "categorie": ["CATEGORIE", "Categorie", "categorie"],  # CORRETTO!
                "fornitore": ["FORNITORE", "Fornitore", "fornitore"],
                "codice_forn": ["CODICE FORN", "Codice Forn", "codice_forn"],
                "made_in": ["MADE IN", "Made In", "made_in"],
                "ecommerce_visibility": [
                    "E-COMMERCE VISIBILITY (COUNTRIES)",
                    "E-commerce Visibility",
                    "ecommerce_visibility",
                    "E-COMMERCE VISIBILITY",
                    "ECOMMERCE VISIBILITY"
                ],
            }

            # Crea un DataFrame per i dati dei prodotti
            prodotto_data = pd.DataFrame(index=df.index)
            for field_name, possible_columns in field_mapping.items():
                # Trova la colonna corrispondente
                matching_col = next(
                    (col for col in possible_columns if col in core_columns), None
                )
                if matching_col:
                    prodotto_data[field_name] = (
                        df[matching_col].astype(str).replace("nan", "")
                    )
                else:
                    prodotto_data[field_name] = ""

            # Aggiungi row_number e pianificazione
            prodotto_data["row_number"] = range(1, len(df) + 1)
            prodotto_data["pianificazione"] = import_record

            # Crea lista di oggetti Prodotto per bulk_create
            prodotto_objects = []
            for _, row in prodotto_data.iterrows():
                try:
                    prodotto_objects.append(Prodotto(**row))
                except Exception as e:
                    logger.warning(
                        f"Error creating Prodotto object for row {row['row_number']}: {str(e)}"
                    )
                    continue

            if not prodotto_objects:
                raise ValueError(
                    "No valid Prodotto objects could be created from the DataFrame."
                )

            # Bulk create dei prodotti
            try:
                # Use ignore_conflicts to skip products that might already exist (e.g., by SKU)
                Prodotto.objects.bulk_create(prodotto_objects, ignore_conflicts=True)
                # The number of created products might be less than len(prodotto_objects) if there were conflicts.
                # We will count the actual products in the DB for this import.
            except IntegrityError as e:
                logger.error(
                    f"Database IntegrityError during Prodotto bulk_create: {str(e)}"
                )
                # This might happen if unique constraints are violated and ignore_conflicts is not sufficient.
                raise e

            # Ottieni i prodotti appena creati per associarli ai record PaesePianificazione
            prodotti = Prodotto.objects.filter(pianificazione=import_record).order_by(
                "row_number"
            )
            products_created = prodotti.count()

            # Create a map of row_number to product object for safe lookup
            prodotto_map = {p.row_number: p for p in prodotti}

            if products_created != len(prodotto_objects):
                logger.warning(
                    f"Mismatch in product count: attempted to create {len(prodotto_objects)}, but {products_created} now exist for this import. This is likely due to `ignore_conflicts=True`."
                )

            # Processa i dati dei paesi
            paese_records = []
            all_available_countries = []
            all_aap_countries = []
            all_countries_with_dates = []

            for country_col in country_columns:
                country_code = country_col.replace("country_", "")
                country_values = df[country_col].astype(str).str.strip()

                # Crea maschere per i diversi tipi di disponibilità
                mask_notna = country_values != "nan"  # Non nulli
                mask_aap = country_values.str.upper().isin(["AAP", "ASAP"])
                mask_tbd = country_values.str.upper() == "TBD"

                # Processa le date
                parsed_dates = country_values.apply(self._parse_date)
                mask_date_np = parsed_dates.notna().to_numpy()  # Convert to NumPy array

                # Crea record per i paesi
                for idx, (value, is_notna, is_aap, is_tbd, parsed_date) in enumerate(
                    zip(country_values, mask_notna, mask_aap, mask_tbd, parsed_dates)
                ):
                    if is_notna and value:
                        date_type = "non_specificato"
                        data_disponibilita = None

                        if is_aap:
                            date_type = "as_available"
                            all_aap_countries.append((idx, country_code))
                        elif is_tbd:
                            date_type = "to_be_determined"
                        elif mask_date_np[idx]:  # Use the NumPy array for indexing
                            date_type = "data_specifica"
                            data_disponibilita = parsed_date
                            all_countries_with_dates.append((idx, country_code, value))

                        all_available_countries.append((idx, country_code))

                        # Safely get the product using the map
                        prodotto_obj = prodotto_map.get(
                            idx + 1
                        )  # row_number is 1-based
                        if not prodotto_obj:
                            logger.warning(
                                f"Skipping country record for row {idx + 1} as no matching product was found in the database."
                            )
                            continue

                        try:
                            paese_records.append(
                                PaesePianificazione(
                                    prodotto=prodotto_obj,
                                    codice_paese=country_code,
                                    data_disponibilita=data_disponibilita,
                                    data_tipo=date_type,
                                    availability_value=value,
                                    is_available=True,
                                    source_column=country_col,
                                )
                            )
                        except IndexError:
                            logger.error(
                                f"IndexError: No product found for index {idx}. This should not happen with the new map-based lookup."
                            )
                            continue

            # Bulk create dei record PaesePianificazione
            try:
                PaesePianificazione.objects.bulk_create(
                    paese_records, ignore_conflicts=True
                )
                country_records_created = len(paese_records)
            except IntegrityError as e:
                logger.error(
                    f"Database IntegrityError during PaesePianificazione bulk_create: {str(e)}"
                )
                raise e

            # Aggiorna i campi JSON dei prodotti
            for idx, prodotto in enumerate(prodotti):
                try:
                    available_countries = [
                        c for i, c in all_available_countries if i == idx
                    ]
                    aap_countries = [c for i, c in all_aap_countries if i == idx]
                    countries_with_dates = {
                        c: v for i, c, v in all_countries_with_dates if i == idx
                    }

                    prodotto.paesi_disponibili = available_countries
                    prodotto.paesi_aap = aap_countries
                    prodotto.paesi_con_date = list(countries_with_dates.keys())
                    prodotto.date_paesi = countries_with_dates
                    prodotto.save()
                except Exception as e:
                    logger.warning(
                        f"Error updating JSON fields for product {prodotto.id}: {str(e)}"
                    )
                    continue

            logger.info(
                f"SUCCESS: Saved {products_created} products and {country_records_created} country records"
            )

            return {
                "products_created": products_created,
                "country_records_created": country_records_created,
                "countries_found": set(
                    rec.codice_paese
                    for rec in PaesePianificazione.objects.filter(
                        prodotto__pianificazione=import_record
                    )
                ),
            }

        except Exception as e:
            logger.error(f"Errore nel salvataggio database: {str(e)}", exc_info=True)
            raise

    def _find_column_value(
        self, row: pd.Series, possible_columns: List[str], available_columns: List[str]
    ):
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
                if (
                    col_name.lower() in available_col.lower()
                    or available_col.lower() in col_name.lower()
                ):
                    return row[available_col]

        return None

    def _parse_date(self, date_str: Any) -> Optional[object]:
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
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%d-%m-%Y",
                "%Y-%m-%d %H:%M:%S",
                "%d/%m/%Y %H:%M:%S",
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
            unique_countries = (
                PaesePianificazione.objects.filter(
                    prodotto__pianificazione=import_record
                )
                .values_list("codice_paese", flat=True)
                .distinct()
            )

            # Statistiche per tipo di data
            data_types = (
                PaesePianificazione.objects.filter(
                    prodotto__pianificazione=import_record
                )
                .values("data_tipo")
                .annotate(count=models.Count("id"))
            )

            return {
                "total_products": total_products,
                "total_country_records": total_country_records,
                "unique_countries": len(unique_countries),
                "countries_list": list(unique_countries),
                "data_types_breakdown": {
                    item["data_tipo"]: item["count"] for item in data_types
                },
            }

        except Exception as e:
            logger.error(f"Error calculating statistics: {e}", exc_info=True)
            return {}

    def _save_processed_csv(
        self, df: pd.DataFrame, import_record: PianificazioneImport
    ) -> str:
        """
        Salva il DataFrame processato come CSV in locale

        Args:
            df (pd.DataFrame): DataFrame con i dati processati
            import_record (PianificazioneImport): Record di import

        Returns:
            str: Path del file CSV salvato
        """
        try:
            # Crea il nome del file con timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = import_record.source_file_name.replace('.xlsx', '').replace('.xls', '')
            csv_filename = f"{base_name}_processed_{timestamp}.csv"

            # Path nella cartella media/temp_uploads
            csv_path = os.path.join(settings.MEDIA_ROOT, "temp_uploads", csv_filename)

            # Assicurati che la directory esista
            os.makedirs(os.path.dirname(csv_path), exist_ok=True)

            # Salva il CSV
            df.to_csv(csv_path, index=False, encoding='utf-8-sig', sep=',')

            logger.info(f"✅ CSV processato salvato: {csv_path}")
            logger.info(f"📊 Dati salvati: {len(df)} righe, {len(df.columns)} colonne")

            # Ritorna il path relativo per salvarlo nel database
            relative_path = os.path.relpath(csv_path, settings.MEDIA_ROOT)
            return relative_path

        except Exception as e:
            logger.error(f"❌ Errore nel salvataggio CSV: {str(e)}")
            return ""

    def _apply_visibility_rules(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Applica le regole E-commerce Visibility per popolare automaticamente i paesi
        
        Args:
            df (pd.DataFrame): DataFrame con i dati processati
            
        Returns:
            pd.DataFrame: DataFrame con paesi popolati secondo le regole di visibilità
        """
        try:
            from .visibility_rules import EcommerceVisibilityProcessor, apply_visibility_rules_to_products
            
            logger.info("🔄 Applying E-commerce Visibility rules to products...")
            
            # Crea il processore delle regole
            processor = EcommerceVisibilityProcessor()
            
            # Applica le regole al DataFrame
            df_with_rules = apply_visibility_rules_to_products(df, processor)
            
            logger.info("✅ E-commerce Visibility rules applied successfully")
            return df_with_rules
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to apply visibility rules: {str(e)}")
            logger.warning("Continuing without visibility rules application...")
            return df
