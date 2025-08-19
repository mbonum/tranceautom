from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.shortcuts import render, redirect, reverse
import csv
import logging

# import io
import json
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
import pandas as pd
from django.http import HttpResponse
from datetime import datetime, date
from .visibility_rules import VisibilityRules, parse_visibility_rule

logger = logging.getLogger(__name__)


def validate_csv(file):
    """Validate CSV file structure and content"""
    try:
        file.seek(0)
        # Try to detect delimiter
        sample = file.read(1024).decode("utf-8")
        file.seek(0)

        sniffer = csv.Sniffer()
        delimiter = sniffer.sniff(sample).delimiter

        # Read CSV with pandas
        df = pd.read_csv(file, delimiter=delimiter)

        # Basic validation checks
        if df.empty:
            return False, "CSV file is empty."

        if len(df.columns) == 0:
            return False, "CSV file has no columns."

        # Check for unnamed columns (usually indicates malformed CSV)
        unnamed_cols = [col for col in df.columns if "Unnamed" in str(col)]
        if len(unnamed_cols) > len(df.columns) / 2:
            return False, "CSV file appears to be malformed (too many unnamed columns)."

        return True, df

    except UnicodeDecodeError:
        return False, "CSV file encoding is not supported. Please use UTF-8 encoding."
    except pd.errors.EmptyDataError:
        return False, "CSV file is empty or corrupted."
    except pd.errors.ParserError as e:
        return False, f"CSV parsing error: {str(e)}"
    except Exception as e:
        return False, f"Error validating CSV: {str(e)}"


def user_login(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                # messages.success(request, f"Welcome back, {user.username}!")

                # Redirect to next page if specified, otherwise to home
                next_page = request.GET.get("next", "home")
                return redirect(next_page)
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Please provide both username and password.")

    return render(request, "registration/login.html")


def user_logout(request):
    """User logout view"""
    # username = request.user.username if request.user.is_authenticated else None
    logout(request)
    # if username:
    # messages.success(request, f"Goodbye, {username}! You have been logged out.")
    return redirect("login")


def user_register(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get("username")
            messages.success(
                request, f"Account created for {username}! You can now log in."
            )
            return redirect("login")
        else:
            # Add form errors to messages
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = UserCreationForm()

    return render(request, "registration/register.html", {"form": form})


# Update your existing home view to require login
@login_required
def home(request):
    context = {
        "error": None,
        "preview": False,
        "filename": request.session.get("original_filename"),
        "tranches": list(request.session.get("tranches_data", {}).keys()),
        "selected_tranche": None,
        "table_data": [],
        "table_headers": [],
    }

    if request.method == "POST" and "file" in request.FILES:
        # Clear session on new upload ma NON usare flush() che cancella l'autenticazione
        request.session.pop('tranches_data', None)
        request.session.pop('original_filename', None)
        
        try:
            uploaded_file = request.FILES["file"]
            if not (
                uploaded_file.name.lower().endswith(".xlsx")
                or uploaded_file.name.endswith(".xls")
            ):
                context["error"] = "Solo file Excel (.xlsx, .xls) sono permessi."
            else:
                # Handle Excel file - PARSING ORIGINALE SEMPLIFICATO
                uploaded_file.seek(0)
                xls = pd.ExcelFile(uploaded_file)
                
                print(f"=== ANALISI FILE EXCEL ===")
                print(f"Fogli disponibili: {xls.sheet_names}")
                
                # Trova il foglio giusto - più flessibile
                sheet_to_find = "PIANIFICAZIONE"
                actual_sheet_name = None
                
                # Prima prova nome esatto
                for sheet_name in xls.sheet_names:
                    if sheet_name.upper() == sheet_to_find.upper():
                        actual_sheet_name = sheet_name
                        break
                
                # Se non trova, prova nomi simili
                if not actual_sheet_name:
                    for sheet_name in xls.sheet_names:
                        if "pianificaz" in sheet_name.lower():
                            actual_sheet_name = sheet_name
                            break
                
                # Se ancora non trova, usa il primo foglio
                if not actual_sheet_name:
                    actual_sheet_name = xls.sheet_names[0]
                
                print(f"Foglio selezionato: {actual_sheet_name}")

                if not actual_sheet_name:
                    context["error"] = (
                        f"Il file Excel non contiene un foglio chiamato '{sheet_to_find}' o simile."
                    )
                else:
                    # Leggi il foglio
                    df_raw = pd.read_excel(
                        xls, sheet_name=actual_sheet_name, header=None
                    )
                    print(f"Dimensioni foglio: {df_raw.shape}")
                    
                    # Trova la riga header - LOGICA ORIGINALE
                    header_keyword = "chiave articolo colore"
                    header_row_index = -1
                    
                    print(f"=== RICERCA HEADER ROW ===")
                    for i, row in df_raw.iterrows():
                        row_str = " ".join(
                            str(x) for x in row.values if pd.notna(x)
                        ).lower()
                        print(f"Row {i}: {row_str[:80]}...")
                        
                        if header_keyword in row_str:
                            header_row_index = i
                            print(f"TROVATA HEADER ROW {i}")
                            break

                    if header_row_index == -1:
                        context["error"] = (
                            f"Non riesco a trovare la riga header contenente '{header_keyword}' nel foglio '{actual_sheet_name}'."
                        )
                    else:
                        # PARSING ORIGINALE FUNZIONANTE
                        new_header = df_raw.iloc[header_row_index]
                        print(f"Header trovato: {new_header.tolist()[:10]}...")
                        
                        df_data = df_raw[header_row_index + 1 :].copy()
                        df_data.columns = new_header
                        df_data.dropna(axis=1, how="all", inplace=True)

                        # Identifica righe vuote per separare le tranche - LOGICA ORIGINALE
                        print(f"=== SEPARAZIONE TRANCHE ===")
                        print(f"Dati dopo header: {df_data.shape}")
                        
                        # Usa le prime 5 colonne per identificare righe vuote
                        main_columns = df_data.columns[:5]
                        is_empty_row = df_data[main_columns].isnull().all(axis=1)
                        df_data["tranche_group"] = is_empty_row.cumsum()
                        df_data_no_empty = df_data.dropna(how="all").copy()

                        if df_data_no_empty.empty:
                            context["error"] = "Nessun dato trovato dopo l'header."
                        else:
                            # Raggruppa per tranche - LOGICA ORIGINALE
                            tranches_dfs = [
                                group.drop("tranche_group", axis=1)
                                for _, group in df_data_no_empty.groupby(
                                    "tranche_group"
                                )
                            ]
                            
                            print(f"Trovate {len(tranches_dfs)} tranche potenziali")
                            
                            tranches_data = {}
                            for i, tranche_df in enumerate(tranches_dfs):
                                df = tranche_df.copy()
                                if not df.empty:
                                    # Rimuovi righe con prima colonna vuota
                                    df.dropna(subset=[df.columns[0]], inplace=True)

                                if not df.empty:
                                    # Add original row number (1-based) as the first column
                                    df.insert(0, "#", range(1, len(df) + 1))
                                    df.reset_index(drop=True, inplace=True)
                                    df.fillna("", inplace=True)

                                    table_headers = df.columns.tolist()
                                    table_data = df.astype(str).values.tolist()
                                    tranche_name = f"Tranche {i + 1}"
                                    
                                    print(f"Tranche {i + 1}: {len(df)} righe, {len(table_headers)} colonne")
                                    
                                    tranches_data[tranche_name] = {
                                        "headers": table_headers,
                                        "data": table_data,
                                    }
                            
                            if not tranches_data:
                                context["error"] = "No valid tranche found."
                            else:
                                request.session["tranches_data"] = tranches_data
                                request.session["original_filename"] = (
                                    uploaded_file.name
                                )
                                first_tranche_name = list(tranches_data.keys())[0]
                                
                                print(f"=== SUCCESS ===")
                                print(f"Saved {len(tranches_data)} tranches in session")
                                print(f"Redirecting to first tranche: {first_tranche_name}")
                                
                                return redirect(
                                    f"{reverse('home')}?tranche={first_tranche_name}"
                                )
        except Exception as e:
            context["error"] = f"Error during file processing: {str(e)}"
            logger.error(f"Error processing file: {str(e)}", exc_info=True)
            import traceback
            traceback.print_exc()

    # Handle selected tranche display - ORIGINAL LOGIC
    tranches_data = request.session.get("tranches_data")
    if tranches_data:
        context["preview"] = True
        selected_tranche_name = request.GET.get("tranche")

        if not selected_tranche_name and context["tranches"]:
            first_tranche = list(context["tranches"])[0]
            return redirect(f"{request.path}?tranche={first_tranche}")

        if selected_tranche_name in tranches_data:
            context["selected_tranche"] = selected_tranche_name
            tranche_content = tranches_data[selected_tranche_name]
            context["table_headers"] = tranche_content["headers"]
            context["table_data"] = tranche_content["data"]
            
            print(f"=== VISUALIZZAZIONE TRANCHE {selected_tranche_name} ===")
            print(f"Headers: {len(context['table_headers'])}")
            print(f"Data rows: {len(context['table_data'])}")
            
        elif selected_tranche_name:
            context["error"] = f"Tranche '{selected_tranche_name}' non trovata."

    return render(request, "home.html", context)


def generate_xml_content(edited_data, original_filename, username, tranche_name):
    """Generate XML content from edited data with precise country mapping and visibility rules"""

    def escape_xml(text):
        """Escape XML special characters"""
        if text is None:
            return ""
        return (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    def parse_country_columns(header_row):
        """Parse header row to identify country group columns"""
        country_mappings = {}
        
        print(f"=== ANALISI COLONNE PAESE ===")
        print(f"Header row length: {len(header_row)}")
        print(f"Header row sample: {header_row[:15] if len(header_row) > 15 else header_row}")
        
        for col_index, header in enumerate(header_row):
            if header and isinstance(header, str):
                print(f"  Col {col_index}: '{header}' (len={len(header)})")
                
                # Check if this column contains country codes (pattern: XX-XX-XX...)
                if '-' in header and len(header) > 2:  # Abbassato da 5 a 2
                    # Split by hyphen to get individual country codes
                    countries = [country.strip().upper() for country in header.split('-') if country.strip()]
                    
                    print(f"    Splitting '{header}' -> {countries}")
                    
                    # Validate that these look like country codes (2-3 chars, uppercase)
                    valid_countries = []
                    for country in countries:
                        if len(country) >= 2 and len(country) <= 3 and country.isalpha():
                            valid_countries.append(country)
                        else:
                            print(f"    ✗ '{country}' non è un codice paese valido")
                    
                    if valid_countries:
                        country_mappings[col_index] = {
                            'countries': valid_countries,
                            'group_header': header
                        }
                        print(f"    ✓ PAESE TROVATO: {header} -> {valid_countries}")
                    else:
                        print(f"    ✗ Nessun paese valido in: {header}")
                else:
                    # Also check if it's a single country
                    header_clean = header.strip().upper()
                    
                    # Exclude common non-country values that might look like country codes
                    excluded_values = {'AAP', 'TBD', 'TBC', 'XXS', 'XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL', 'ASAP'}
                    
                    if (len(header_clean) >= 2 and len(header_clean) <= 3 and 
                        header_clean.isalpha() and header_clean not in excluded_values):
                        country_mappings[col_index] = {
                            'countries': [header_clean],
                            'group_header': header
                        }
                        print(f"    ✓ SINGLE COUNTRY FOUND: {header} -> [{header_clean}]")
                    else:
                        print(f"    ✗ Does not look like country column: '{header}'")
        
        print(f"RISULTATO: Trovati {len(country_mappings)} gruppi di paesi")
        for col_idx, mapping in country_mappings.items():
            print(f"  Col {col_idx}: {mapping['countries']} ({mapping['group_header']})")
        
        return country_mappings

    def find_visibility_column(header_row):
        """Find the visibility rule column in the header"""
        visibility_keywords = [
            'e-commerce visibility',
            'visibility',
            'ecommerce visibility', 
            'commerce visibility',
            'e-commerce visibility (countries)',
            'visibility (countries)',
            'ecommerce visibility (countries)'
        ]
        
        print(f"=== RICERCA COLONNA VISIBILITY ===")
        print(f"Cercando tra {len(header_row)} colonne...")
        
        for col_index, header in enumerate(header_row):
            if header and isinstance(header, str):
                header_lower = header.lower().strip()
                print(f"  Col {col_index}: '{header}' -> '{header_lower}'")
                
                for keyword in visibility_keywords:
                    if keyword in header_lower:
                        print(f"    ✓ VISIBILITY TROVATA: Col {col_index} = '{header}' (keyword: '{keyword}')")
                        return col_index
        
        print(f"  ✗ Colonna visibility non trovata tra le keywords: {visibility_keywords}")
        
        # Seconda prova: cerca pattern più generici
        for col_index, header in enumerate(header_row):
            if header and isinstance(header, str):
                header_lower = header.lower().strip()
                if ('visib' in header_lower and 'countr' in header_lower) or \
                   ('commerce' in header_lower and 'countr' in header_lower):
                    print(f"    ✓ VISIBILITY PATTERN TROVATA: Col {col_index} = '{header}'")
                    return col_index
        
        return None

    def create_default_countries_from_visibility():
        """Fallback: crea una lista di paesi di default quando non troviamo né paesi né visibility"""
        print(f"=== FALLBACK: CREAZIONE PAESI DI DEFAULT ===")
        print("Non sono state trovate né colonne paese né regole di visibilità")
        print("Usando tutti i paesi disponibili con data 'TBD'")
        
        # Importa tutti i paesi dalle regole di visibilità
        default_countries = []
        for country_code in VisibilityRules.ALL_COUNTRIES:
            default_countries.append({
                'code': country_code,
                'live_date': 'TBD',
                'date_type': 'fallback_default',
                'group': 'default_all_countries',
                'column_index': 0,
                'source': 'fallback_all_countries',
                'visibility_rule': 'DEFAULT: ALL COUNTRIES'
            })
        
        print(f"Creati {len(default_countries)} paesi di default")
        return default_countries

    def process_product_visibility_and_countries(row, country_mappings, header_row, visibility_col_index):
        """Process both visibility rules and country activation data for a single product"""
        
        print(f"=== PROCESSING PRODUCT ROW ===")
        print(f"Row length: {len(row)}")
        print(f"Country mappings available: {len(country_mappings)}")
        print(f"Visibility column: {visibility_col_index}")
        
        # Estrai la regola di visibilità
        visibility_rule = None
        if visibility_col_index is not None and visibility_col_index < len(row):
            rule_text = row[visibility_col_index]
            if rule_text and str(rule_text).strip() and str(rule_text).strip().upper() not in ['', 'NAN', 'NONE']:
                visibility_rule = str(rule_text).strip()
                print(f"  Visibility rule found: '{visibility_rule}'")
        
        # Process countries from activation dates
        activation_countries = []
        for col_index, mapping in country_mappings.items():
            if col_index < len(row):
                value = row[col_index]
                print(f"  Col {col_index} ({mapping['group_header']}): '{value}'")
                
                # Check if there's a valid value for this country group
                if value and str(value).strip() and str(value).strip().upper() not in ['', 'NAN', 'NONE']:
                    date_value = str(value).strip()
                    
                    # Convert AAP to more readable format
                    if date_value.upper() == 'AAP':
                        live_date = 'ASAP'
                        date_type = 'immediate'
                    else:
                        live_date = date_value
                        date_type = 'scheduled'
                    
                    print(f"    ✓ Activation date: {live_date} for countries {mapping['countries']}")
                    
                    # Add each individual country with its date
                    for country_code in mapping['countries']:
                        activation_countries.append({
                            'code': country_code,
                            'live_date': live_date,
                            'date_type': date_type,
                            'group': mapping['group_header'],
                            'column_index': col_index + 1,  # 1-based indexing for reference
                            'source': 'activation_date'
                        })
                else:
                    print(f"    ✗ No date for {mapping['group_header']}")
        
        print(f"  Countries from activation: {len(activation_countries)}")
        
        # Analyze the visibility rule
        visibility_data = None
        if visibility_rule:
            try:
                visibility_data = parse_visibility_rule(visibility_rule)
                print(f"  Visibility rule: '{visibility_rule}' -> {len(visibility_data['allowed_countries'])} paesi")
            except Exception as e:
                print(f"  ✗ Error parsing visibility rule '{visibility_rule}': {e}")
                visibility_data = None
        
        # Combine data: countries from visibility rules + specific activation dates
        final_countries = []
        
        if visibility_data and visibility_data['allowed_countries']:
            # For each country allowed by the visibility rule
            for country_code in visibility_data['allowed_countries']:
                # Look for a specific activation date for this country
                activation_info = next(
                    (act for act in activation_countries if act['code'] == country_code), 
                    None
                )
                
                if activation_info:
                    # Use specific activation data
                    final_countries.append({
                        'code': country_code,
                        'live_date': activation_info['live_date'],
                        'date_type': activation_info['date_type'],
                        'group': activation_info['group'],
                        'column_index': activation_info['column_index'],
                        'source': 'both_visibility_and_activation',
                        'visibility_rule': visibility_rule
                    })
                else:
                    # Country allowed by visibility but without specific date
                    final_countries.append({
                        'code': country_code,
                        'live_date': 'TBD',  # To Be Determined
                        'date_type': 'visibility_only',
                        'group': 'from_visibility_rule',
                        'column_index': visibility_col_index + 1 if visibility_col_index is not None else 0,
                        'source': 'visibility_rule_only',
                        'visibility_rule': visibility_rule
                    })
        elif activation_countries:
            # If there's no visibility rule, use only countries with activation dates
            final_countries = activation_countries.copy()
            for country in final_countries:
                country['source'] = 'activation_date_only'
                country['visibility_rule'] = None
        else:
            # FALLBACK: If we find neither visibility nor countries, use all default countries
            print("  ⚠️ FALLBACK: No visibility rules or activation dates found")
            final_countries = create_default_countries_from_visibility()
        
        print(f"  Final countries: {len(final_countries)}")
        for country in final_countries[:3]:  # Show first 3
            print(f"    {country['code']}: {country['live_date']} ({country['source']})")
        
        return final_countries, visibility_data

    # Start building XML
    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append(
        f'<ProductPlanning source_file="{escape_xml(original_filename)}" tranche="{escape_xml(tranche_name)}">'
    )

    # Add metadata
    xml_lines.append("  <metadata>")
    xml_lines.append(f"    <total_rows>{len(edited_data)}</total_rows>")
    xml_lines.append(
        f"    <total_columns>{len(edited_data[0]) if edited_data else 0}</total_columns>"
    )
    xml_lines.append(
        f"    <generated_at>{pd.Timestamp.now().isoformat()}</generated_at>"
    )
    xml_lines.append(f"    <user>{escape_xml(username)}</user>")
    xml_lines.append("  </metadata>")

    if not edited_data:
        xml_lines.append("  <Product></Product>")
        xml_lines.append("</ProductPlanning>")
        return "\n".join(xml_lines)

    # Parse country columns from header (first row)
    header_row = edited_data[0] if edited_data else []
    print(f"=== INIZIO PARSING HEADER ===")
    print(f"Header row completo ({len(header_row)} colonne): {header_row}")
    
    country_mappings = parse_country_columns(header_row)
    visibility_col_index = find_visibility_column(header_row)
    
    # FALLBACK: Se non troviamo né paesi né visibility, aggiungi messaggio nei metadati
    if not country_mappings and visibility_col_index is None:
        xml_lines.append("  <fallback_mode>true</fallback_mode>")
        xml_lines.append("  <fallback_reason>No country columns or visibility rules found - using all countries with TBD dates</fallback_reason>")
    
    # Add country mapping info to metadata
    if country_mappings:
        xml_lines.append("  <country_groups>")
        for col_index, mapping in country_mappings.items():
            xml_lines.append(f"    <group column='{col_index + 1}' header='{escape_xml(mapping['group_header'])}'>")
            for country in mapping['countries']:
                xml_lines.append(f"      <country>{escape_xml(country)}</country>")
            xml_lines.append("    </group>")
        xml_lines.append("  </country_groups>")
    
    # Add visibility column info to metadata
    if visibility_col_index is not None:
        xml_lines.append(f"  <visibility_column>{visibility_col_index + 1}</visibility_column>")

    # Add data rows (skip header row) - DATA-CENTRIC STRUCTURE
    for i, row in enumerate(edited_data[1:], 1):  # Skip header, start from 1
        print(f"\n=== PRODUCT {i} ===")
        
        xml_lines.append("  <Product>")
        
        # Add basic product information
        product_fields = {
            1: 'ChiaveArticoloColore',
            2: 'ConcatenatedId', 
            3: 'Merceologia',
            4: 'NumeroTranche',
            5: 'Stagione',
            6: 'SKU',
            7: 'DescrizioneArticolo',
            8: 'DataInizioConsegna',
            9: 'DataSpedizioneStandard',
            10: 'ImpiantiPer'
        }
        
        for col_idx, field_name in product_fields.items():
            if col_idx < len(row) and row[col_idx]:
                xml_lines.append(f"    <{field_name}>{escape_xml(row[col_idx])}</{field_name}>")

        # Process visibility and countries
        countries_data, visibility_info = process_product_visibility_and_countries(
            row, country_mappings, header_row, visibility_col_index
        )
        
        # Add visibility rule info
        if visibility_info:
            xml_lines.append("    <VisibilityRule>")
            xml_lines.append(f"      <RuleText>{escape_xml(visibility_info['rule_text'])}</RuleText>")
            xml_lines.append(f"      <Description>{escape_xml(visibility_info['description'])}</Description>")
            xml_lines.append(f"      <AllowedCountriesCount>{visibility_info['allowed_countries_count']}</AllowedCountriesCount>")
            if visibility_info['has_special_conditions']:
                xml_lines.append("      <SpecialConditions>")
                for condition_type, condition_value in visibility_info['special_conditions'].items():
                    xml_lines.append(f"        <{condition_type}>{escape_xml(str(condition_value))}</{condition_type}>")
                xml_lines.append("      </SpecialConditions>")
            xml_lines.append("    </VisibilityRule>")
        
        # Add countries organized by date (STRUTTURA DATA-CENTRICA)
        if countries_data:
            xml_lines.append("    <Planning>")
            
            # Group by date for better organization
            from collections import defaultdict
            countries_by_date = defaultdict(list)
            
            for country_info in countries_data:
                countries_by_date[country_info['live_date']].append(country_info)
            
            # Sort dates (put TBD and ASAP at the end)
            sorted_dates = sorted(countries_by_date.keys(), key=lambda x: (
                x == 'TBD',  # TBD goes last
                x == 'ASAP',  # ASAP goes second to last
                x  # Regular dates in alphabetical/chronological order
            ))
            
            for live_date in sorted_dates:
                countries = countries_by_date[live_date]
                xml_lines.append(f"      <Availability date='{escape_xml(live_date)}'>")
                
                # Sort countries alphabetically for consistency
                countries.sort(key=lambda x: x['code'])
                
                for country_info in countries:
                    xml_lines.append(f"        <Country>{escape_xml(country_info['code'])}</Country>")
                
                xml_lines.append("      </Availability>")
            
            xml_lines.append("    </Planning>")
        else:
            # Empty planning section if no countries
            xml_lines.append("    <Planning>")
            xml_lines.append("    </Planning>")

        xml_lines.append("  </Product>")

    xml_lines.append("</ProductPlanning>")

    return "\n".join(xml_lines)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def download_xml(request):
    """View to handle XML download with edited data"""
    try:
        edited_data_str = request.POST.get("edited_data", "[]")
        tranche_name = request.POST.get("tranche_name")

        if not edited_data_str.strip():
            logger.warning("Empty edited_data received")
            return HttpResponse("No data provided.", status=400)

        if not tranche_name:
            logger.warning("Tranche name not provided")
            return HttpResponse("Tranche name not provided.", status=400)

        try:
            edited_data = json.loads(edited_data_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return HttpResponse("Invalid data format.", status=400)

        original_filename = request.session.get(
            "original_filename", "converted_file.csv"
        )

        if not edited_data:
            logger.warning("Empty edited_data list")
            return HttpResponse("No data available for download.", status=400)

        if not isinstance(edited_data, list) or not all(
            isinstance(row, list) for row in edited_data
        ):
            logger.error("Invalid data structure")
            return HttpResponse("Invalid data structure.", status=400)

        xml_content = generate_xml_content(
            edited_data, original_filename, request.user.username, tranche_name
        )

        base_filename = (
            original_filename.rsplit(".", 1)[0] if original_filename else "data"
        )
        safe_tranche_name = (
            "".join(c for c in tranche_name if c.isalnum() or c in (" ", "_"))
            .rstrip()
            .replace(" ", "_")
        )
        xml_filename = (
            f"{base_filename}_{safe_tranche_name}_edited_by_{request.user.username}.xml"
        )

        response = HttpResponse(xml_content, content_type="application/xml")
        response["Content-Disposition"] = f'attachment; filename="{xml_filename}"'
        response["Content-Length"] = len(xml_content.encode("utf-8"))

        logger.info(
            f"XML file '{xml_filename}' generated successfully for user {request.user.username}"
        )
        return response

    except Exception as e:
        logger.error(f"Unexpected error generating XML: {e}", exc_info=True)
        return HttpResponse("Error generating XML file.", status=500)
