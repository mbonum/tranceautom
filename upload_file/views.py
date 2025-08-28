"""
Refactored views for Tranche Automation
Focused on API endpoints and user interface, with business logic delegated to specialized modules
"""

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.shortcuts import render, redirect  # , reverse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponse, JsonResponse
from django.db import transaction
import logging

from .models import PianificazioneImport, Prodotto, PaesePianificazione
from .parsers import ExcelHeaderParser  # , VisibilityColumnParser
from .processors import (
    ProductDataProcessor,
    # CountryPlanningProcessor,
    # ValidationProcessor,
    SimpleCountryProcessor,
)
from .xml_generator import XMLExportManager
from .forms import ExcelUploadForm
from .utils import (
    _is_valid_file_type,
    _get_recent_imports,
    _get_user_plannings,
)


logger = logging.getLogger(__name__)


# ============================================================================
# AUTHENTICATION VIEWS
# ============================================================================


def user_login(request):
    """User login view"""
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, "registration/login.html")


def user_logout(request):
    """User logout view"""
    logout(request)
    return redirect("login")


def user_register(request):
    """User registration view"""
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get("username")
            messages.success(request, f"Account was created for {username}!")
            return redirect("login")
    else:
        form = UserCreationForm()
    return render(request, "registration/register.html", {"form": form})


# ============================================================================
# MAIN APPLICATION VIEWS
# ============================================================================


@login_required
def home(request):
    """Main home page with upload functionality"""
    # Handle file upload
    if request.method == "POST":
        return handle_file_upload(request)

    # GET request - show the page
    context = {
        "recent_imports": _get_recent_imports(request.user),
        "upload_form": ExcelUploadForm(),
        "user_plannings": _get_user_plannings(request.user),
    }
    return render(request, "home.html", context)


@login_required
@require_http_methods(["POST"])
@csrf_protect
def handle_file_upload(request):
    """
    Handle file upload and processing
    Delegates actual processing to specialized modules
    """
    try:
        if "excel_file" not in request.FILES:
            messages.error(request, "Please provide a valid Excel file.")
            return redirect("home")

        uploaded_file = request.FILES["excel_file"]

        # Process Excel file using new architecture
        result = _process_excel_file(uploaded_file, request.user)

        if result["success"]:
            messages.success(
                request,
                f"File processed successfully! {result['stats']['products']} products imported.",
            )
            # Redirect to the planning details page to show results
            return redirect("planning_details", planning_id=result["planning_id"])
        else:
            messages.error(request, f"Error processing file: {result['error']}")

        return redirect("home")

    except Exception as e:
        logger.error(f"Error in handle_file_upload: {str(e)}", exc_info=True)
        messages.error(request, f"Server error: {str(e)}")
        return redirect("home")


@login_required
def download_xml(request):
    """
    Generate and download XML for a planning or specific tranche
    Expects planning_id and optional tranche_name as GET parameters
    """
    try:
        planning_id = request.GET.get("planning_id")
        tranche_name = request.GET.get("tranche_name")

        if not planning_id:
            return JsonResponse({"success": False, "error": "Planning ID is required"})

        # Validate planning access
        try:
            planning = PianificazioneImport.objects.get(
                id=planning_id, imported_by=request.user
            )
        except PianificazioneImport.DoesNotExist:
            return JsonResponse(
                {"success": False, "error": "Planning not found or access denied"}
            )

        # Use XML export manager
        from .xml_generator import XMLExportManager

        export_manager = XMLExportManager(planning_id)

        if tranche_name:
            result = export_manager.export_tranche(tranche_name, request.user.username)
            filename = f"piano_{tranche_name}_optimized_by_{request.user.username}.xml"
        else:
            result = export_manager.export_full_planning(request.user.username)
            filename = f"piano_complete_optimized_by_{request.user.username}.xml"

        if not result["success"]:
            return JsonResponse(
                {
                    "success": False,
                    "error": result.get("error", "XML generation failed"),
                    "validation_errors": result.get("validation", {}).get("errors", []),
                }
            )

        # Create HTTP response with XML content
        response = HttpResponse(result["xml_content"], content_type="application/xml")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        logger.info(f"XML downloaded: {filename} by {request.user.username}")
        return response

    except Exception as e:
        logger.error(f"Error generating XML: {str(e)}", exc_info=True)
        return JsonResponse(
            {"success": False, "error": f"Error generating XML: {str(e)}"}
        )


@login_required
def planning_details(request, planning_id):
    """
    Show detailed planning results with all products
    """
    try:
        # Get planning
        planning = PianificazioneImport.objects.get(
            id=planning_id, imported_by=request.user
        )

        # Get all products
        products = Prodotto.objects.filter(pianificazione=planning).order_by(
            "row_number"
        )

        # Prepare products data with countries
        products_data = []
        products_with_dates = 0

        for product in products:
            countries = list(
                product.pianificazioni_paesi.values(
                    "codice_paese", "data_disponibilita", "data_tipo"
                )
            )

            # Count products with dates (excluding TBD and ASAP)
            if any(
                country.get("data_disponibilita")
                and country.get("data_disponibilita") != "TBD"
                and country.get("data_disponibilita") != "ASAP"
                for country in countries
            ):
                products_with_dates += 1

            products_data.append(
                {
                    "row_number": product.row_number,
                    "codice_forn": product.codice_forn,
                    "commerce": product.commerce,
                    "made_in": product.made_in,
                    "categorie": product.categorie,
                    "impianti_russia_doganale": product.impianti_russia_doganale,
                    "countries": countries,
                }
            )

        # Statistics
        stats = {
            "total_products": products.count(),
            "total_countries": PaesePianificazione.objects.filter(
                prodotto__pianificazione=planning
            )
            .values("codice_paese")
            .distinct()
            .count(),
            "products_with_dates": products_with_dates,
        }

        context = {"planning": planning, "products": products_data, "stats": stats}

        return render(request, "planning_details.html", context)

    except PianificazioneImport.DoesNotExist:
        messages.error(request, "Planning not found or access denied")
        return redirect("home")
    except Exception as e:
        logger.error(f"Error showing planning details: {str(e)}", exc_info=True)
        messages.error(request, f"Error loading planning: {str(e)}")
        return redirect("home")


# ============================================================================
# API ENDPOINTS (JSON responses)
# ============================================================================


@login_required
@require_http_methods(["POST"])
@csrf_protect
def api_upload_file(request):
    """
    API endpoint for file upload (returns JSON)
    """
    try:
        if "file" not in request.FILES:
            return JsonResponse({"success": False, "error": "No file provided"})

        uploaded_file = request.FILES["file"]

        # Validate file type
        if not _is_valid_file_type(uploaded_file):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid file type. Please upload Excel (.xlsx) files.",
                }
            )

        # Process Excel file
        result = _process_excel_file(uploaded_file, request.user)
        return JsonResponse(result)

    except Exception as e:
        logger.error(f"Error in api_upload_file: {str(e)}", exc_info=True)
        return JsonResponse({"success": False, "error": f"Server error: {str(e)}"})


# ============================================================================
# FILE PROCESSING FUNCTIONS
# ============================================================================


@transaction.atomic
def _process_excel_file(uploaded_file, user):
    print(f"🚀 DEBUG: INIZIO processamento file: {uploaded_file.name}")
    logger.info(
        f"🚀 INIZIO processamento file: {uploaded_file.name} per utente: {user.username}"
    )

    try:
        import pandas as pd
        # table test
        # data validation
        # dataframe
        # no item rows

        # Read Excel file - RIPRISTINA LOGICA ORIGINALE
        print("📖 DEBUG: Lettura file Excel...")
        uploaded_file.seek(0)
        xls = pd.ExcelFile(uploaded_file)

        print("=== ANALISI FILE EXCEL ===")
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
            return {
                "success": False,
                "error": f"Il file Excel non contiene un foglio chiamato '{sheet_to_find}' o simile.",
            }

        # Leggi il foglio SENZA HEADER (come originale)
        df_raw = pd.read_excel(xls, sheet_name=actual_sheet_name, header=None)
        print(f"Dimensioni foglio: {df_raw.shape}")

        # Trova la riga header - LOGICA ORIGINALE
        header_keyword = "chiave articolo colore"
        header_row_index = -1

        print("=== RICERCA HEADER ROW ===")
        for i, row in df_raw.iterrows():
            row_str = " ".join(str(x) for x in row.values if pd.notna(x)).lower()
            print(f"Row {i}: {row_str[:80]}...")

            if header_keyword in row_str:
                header_row_index = i
                print(f"TROVATA HEADER ROW {i}")
                break

        if header_row_index == -1:
            return {
                "success": False,
                "error": f"Non riesco a trovare la riga header contenente '{header_keyword}' nel foglio '{actual_sheet_name}'.",
            }

        # PARSING ORIGINALE FUNZIONANTE
        new_header = df_raw.iloc[header_row_index]
        print(f"Header trovato: {new_header.tolist()[:10]}...")

        df_data = df_raw[header_row_index + 1 :].copy()
        df_data.columns = new_header
        df_data.dropna(axis=1, how="all", inplace=True)

        if df_data.empty:
            return {"success": False, "error": "Nessun dato trovato dopo l'header."}

        # Parse headers DOPO aver trovato quello giusto (solo per compatibilità)
        print("🔍 DEBUG: Parsing headers...")
        header_parser = ExcelHeaderParser()
        parsed_headers = header_parser.parse_headers(new_header.tolist())
        print(
            f"✅ DEBUG: Headers parsati: {len(parsed_headers['country_mappings'])} country columns (per compatibilità)"
        )

        # Create planning import record
        print("💾 DEBUG: Creazione planning import record...")
        planning = PianificazioneImport.objects.create(
            source_file_name=uploaded_file.name,
            source_file_type="excel",
            imported_by=user,
            status="processing",
            raw_headers=[str(h) for h in new_header.tolist()],
        )
        print(f"✅ DEBUG: Planning creato con ID: {planning.id}")

        # Initialize processors
        print("🔧 DEBUG: Inizializzazione processors...")
        product_processor = ProductDataProcessor(planning)
        simple_country_processor = SimpleCountryProcessor(planning)

        # Process all data as a single table
        print("📦 DEBUG: Processamento di tutti i prodotti...")

        total_products = 0
        all_countries = set()

        for row_idx, (_, row) in enumerate(df_data.iterrows()):
            print(f"📝 DEBUG: Processamento riga {row_idx + 1}/{len(df_data)}")

            try:
                # Process product
                prodotto = product_processor.process_product_row(
                    row.tolist(), new_header.tolist(), row_idx + 1
                )

                if prodotto:
                    print(f"✅ DEBUG: Prodotto creato: {prodotto.codice_forn}")
                    total_products += 1

                    # Process countries with SIMPLE processor
                    print(
                        f"🌍 DEBUG: Processamento paesi SEMPLIFICATO per prodotto {prodotto.codice_forn}"
                    )
                    try:
                        saved_countries = (
                            simple_country_processor.process_product_countries(
                                prodotto, row.tolist(), new_header.tolist(), df_data
                            )
                        )

                        if saved_countries:
                            print(
                                f"✅ DEBUG: Creati {len(saved_countries)} paesi per {prodotto.codice_forn}"
                            )
                            all_countries.update(
                                [c.codice_paese for c in saved_countries]
                            )
                        else:
                            print(
                                f"⚠️ DEBUG: Nessun paese creato per {prodotto.codice_forn}"
                            )

                    except Exception as country_error:
                        print(
                            f"❌ DEBUG: Errore processamento paesi per {prodotto.codice_forn}: {str(country_error)}"
                        )
                        # Non blocchiamo il prodotto per errori nei paesi

                else:
                    print(
                        f"❌ DEBUG: Fallita creazione prodotto per riga {row_idx + 1}"
                    )

            except Exception as e:
                print(
                    f"💥 DEBUG: ERRORE durante processamento riga {row_idx + 1}: {str(e)}"
                )
                logger.error(
                    f"Error processing row {row_idx + 1}: {str(e)}", exc_info=True
                )
                # Continua con la prossima riga senza fermare tutto il processamento
                continue

        print(f"🎉 DEBUG: COMPLETATO! Processati {total_products} prodotti")

        # Update planning
        planning.total_products = total_products
        planning.total_countries = len(all_countries)
        planning.status = "processed"
        planning.save()

        return {
            "success": True,
            "planning_id": planning.id,
            "stats": {"products": total_products, "countries": len(all_countries)},
        }

    except Exception as e:
        print(f"💥 DEBUG: ERRORE CRITICO: {str(e)}")
        print(f"💥 DEBUG: Tipo errore: {type(e).__name__}")
        logger.error(f"Error processing Excel file: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


# ============================================================================
# LEGACY SUPPORT FUNCTIONS
# ============================================================================


def generate_optimized_xml_content(planning_id, tranche_name, username):
    """Legacy function for XML generation"""
    try:
        export_manager = XMLExportManager(planning_id)
        if tranche_name:
            result = export_manager.export_tranche(tranche_name, username)
        else:
            result = export_manager.export_full_planning(username)

        if result["success"]:
            return result["xml_content"]
        else:
            raise Exception(result.get("error", "XML generation failed"))

    except Exception as e:
        logger.error(f"Legacy XML generation error: {str(e)}")
        raise


def process_and_save_excel_file(uploaded_file, user):
    """Legacy function for Excel processing"""
    result = _process_excel_file(uploaded_file, user)
    if result["success"]:
        return result["planning_id"]
    else:
        return None
