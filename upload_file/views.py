"""
Simplified views for Tranche Automation
Three pages: Login -> Upload -> Data Visualization
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import models
from django.conf import settings
from django.http import JsonResponse
import os
import logging

from .models import PianificazioneImport  # , Prodotto
from .forms import FileUploadForm
from .django_country_processor import DjangoCountryProcessor

logger = logging.getLogger(__name__)


@login_required
def home(request):
    """
    Main upload page
    """
    if request.method == "POST":
        return upload_file(request)

    form = FileUploadForm()

    context = {
        "upload_form": form,
    }

    return render(request, "upload_simple_clean.html", context)


@login_required
def upload_file(request):
    """
    Handle Excel file upload and processing
    """
    if request.method != "POST":
        return redirect("home")

    form = FileUploadForm(request.POST, request.FILES)

    if not form.is_valid():
        logger.warning(f"Invalid form for user {request.user.username}: {form.errors}")
        messages.error(request, "Invalid file. Please upload an Excel file (.xlsx)")
        return redirect("home")

    try:
        uploaded_file = form.cleaned_data["file"]

        # File is already validated by Django form
        logger.info(
            f"Processing file: {uploaded_file.name} ({uploaded_file.size} bytes)"
        )

        # Create import record
        import_record = PianificazioneImport.objects.create(
            source_file_name=uploaded_file.name,
            imported_by=request.user,
            status="pending",
        )

        # Save file temporarily
        temp_dir = os.path.join(settings.MEDIA_ROOT, "temp_uploads")
        os.makedirs(temp_dir, exist_ok=True)

        temp_file_path = os.path.join(
            temp_dir, f"upload_{import_record.id}_{uploaded_file.name}"
        )

        with open(temp_file_path, "wb+") as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Process file with the new processor
        try:
            processor = DjangoCountryProcessor()
            stats = processor.process_excel_to_database(temp_file_path, import_record)

            # Clean up temporary file
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            messages.success(
                request,
                f"File processed successfully! "
                f"Products: {stats['products_created']}, "
                f"Country records: {stats['country_records_created']}",
            )

            logger.info(
                f"Upload completed successfully! Redirecting to data_view for import {import_record.id}"
            )
            return redirect("data_view", import_id=import_record.id)

        except Exception as e:
            logger.error(
                f"Error processing file {uploaded_file.name} for import {import_record.id}: {e}",
                exc_info=True,
            )

            # Clean up on error
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            import_record.status = "error"
            import_record.error_message = str(e)
            import_record.save()

            messages.error(request, f"Error processing file: {str(e)}")
            return redirect("home")

    except Exception as e:
        logger.error(f"General upload error: {e}", exc_info=True)
        messages.error(request, f"Upload error: {str(e)}")
        return redirect("home")


@login_required
def data_view(request, import_id):
    """
    Modern data visualization with pagination and AJAX support
    """
    pianificazione = get_object_or_404(PianificazioneImport, id=import_id)

    # Get all products with relations
    prodotti_base = pianificazione.get_all_products().prefetch_related(
        "paesi_pianificazione"
    )

    # Apply search filter
    search = request.GET.get("search", "")
    if search:
        prodotti_base = prodotti_base.filter(
            models.Q(chiave_articolo__icontains=search)
            | models.Q(descrizione__icontains=search)
            | models.Q(sku__icontains=search)
            | models.Q(articolo__icontains=search)
            | models.Q(fornitore__icontains=search)
            | models.Q(colore__icontains=search)
        )

    # Apply additional filters
    date_filter = request.GET.get("date-filter")
    if date_filter == "no_delivery_date":
        prodotti_base = prodotti_base.filter(data_inizio_consegna__isnull=True)
    elif date_filter == "past_due":
        from datetime import date

        prodotti_base = prodotti_base.filter(data_inizio_consegna__lt=date.today())

    category_filter = request.GET.get("category-filter")
    if category_filter:
        prodotti_base = prodotti_base.filter(categorie__icontains=category_filter)

    # Pagination
    per_page = int(request.GET.get("per_page", 20))
    page = int(request.GET.get("page", 1))

    paginator = Paginator(prodotti_base, per_page)
    prodotti = paginator.get_page(page)

    # For AJAX requests, return JSON data
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        from django.template.loader import render_to_string

        # Handle single row refresh
        if request.GET.get("single_row") and request.GET.get("product_id"):
            try:
                product_id = int(request.GET.get("product_id"))
                product = prodotti_base.get(id=product_id)
                return JsonResponse(
                    {
                        "html": render_to_string(
                            "table_row.html", {"product": product}
                        )
                    }
                )
            except (ValueError, pianificazione.get_all_products().model.DoesNotExist):
                return JsonResponse({"html": ""}, status=404)

        # Render product table rows HTML
        products_html = ""
        for product in prodotti:
            products_html += render_to_string("table_row.html", {"product": product})

        return JsonResponse(
            {
                "html": products_html,
                "products": [{"id": p.id, "name": p.chiave_articolo} for p in prodotti],
                "pagination": {
                    "current_page": page,
                    "total_pages": paginator.num_pages,
                    "has_next": prodotti.has_next(),
                    "has_previous": prodotti.has_previous(),
                    "next_page_number": prodotti.next_page_number()
                    if prodotti.has_next()
                    else None,
                    "previous_page_number": prodotti.previous_page_number()
                    if prodotti.has_previous()
                    else None,
                    "start": prodotti.start_index() if prodotti else 0,
                    "end": prodotti.end_index() if prodotti else 0,
                    "total": paginator.count,
                },
            }
        )

    # Regular page load
    context = {
        "pianificazione": pianificazione,
        "prodotti": prodotti,
        "search": search,
        "total_products": paginator.count,
        "current_page": page,
        "per_page": per_page,
    }

    return render(request, "modern_table_view.html", context)


@login_required
def download_xml(request, import_id):
    """
    Generate and download XML file for PIM integration
    """
    pianificazione = get_object_or_404(PianificazioneImport, id=import_id)

    try:
        from .xml_generator import XMLGenerator

        # Generate XML
        xml_generator = XMLGenerator()
        xml_content = xml_generator.generate_planning_xml(pianificazione)

        # Prepare response for download
        from django.http import HttpResponse

        response = HttpResponse(xml_content, content_type="application/xml")
        response["Content-Disposition"] = (
            f'attachment; filename="pianificazione_{pianificazione.id}_{pianificazione.source_file_name.replace(".xlsx", "")}.xml"'
        )

        logger.info(
            f"XML generated and downloaded for import {import_id} by user {request.user.username}"
        )
        return response

    except Exception as e:
        logger.error(f"Error generating XML for import {import_id}: {str(e)}")
        messages.error(request, f"Error generating XML: {str(e)}")
        return redirect("data_view", import_id=import_id)
