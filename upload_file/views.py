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
# import openpyxl
# from datetime import datetime
# import traceback
# from io import BytesIO


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
        # Clear only the data related to a previous file upload, not the whole session.
        # request.session.flush() would log the user out.
        for key in ["tranches_data", "original_filename"]:
            if key in request.session:
                del request.session[key]
        try:
            uploaded_file = request.FILES["file"]
            if not (
                uploaded_file.name.lower().endswith(".xlsx")
                or uploaded_file.name.endswith(".xls")
            ):
                context["error"] = "Only Excel files (.xlsx, .xls) are allowed."
            else:
                # Handle Excel file
                uploaded_file.seek(0)
                xls = pd.ExcelFile(uploaded_file)
                sheet_to_find = "PIANIFICAZIONE"
                actual_sheet_name = next(
                    (s for s in xls.sheet_names if s.lower() == sheet_to_find.lower()),
                    None,
                )

                if not actual_sheet_name:
                    context["error"] = (
                        f"The Excel file does not contain a sheet named '{sheet_to_find}'."
                    )
                else:
                    df_raw = pd.read_excel(
                        xls, sheet_name=actual_sheet_name, header=None
                    )
                    header_keyword = "chiave articolo colore"
                    header_row_index = -1
                    for i, row in df_raw.iterrows():
                        row_str = " ".join(
                            str(x) for x in row.values if pd.notna(x)
                        ).lower()
                        if header_keyword in row_str:
                            header_row_index = i
                            break

                    if header_row_index == -1:
                        context["error"] = (
                            f"Could not find the header row containing '{header_keyword}' in sheet '{actual_sheet_name}'."
                        )
                    else:
                        new_header = df_raw.iloc[header_row_index]
                        df_data = df_raw[header_row_index + 1 :].copy()
                        df_data.columns = new_header
                        df_data.dropna(axis=1, how="all", inplace=True)

                        df_data["tranche_group"] = df_data.isnull().all(axis=1).cumsum()
                        df_data_no_empty = df_data.dropna(how="all").copy()

                        if df_data_no_empty.empty:
                            context["error"] = "No data found after header."
                        else:
                            tranches_dfs = [
                                group.drop("tranche_group", axis=1)
                                for _, group in df_data_no_empty.groupby(
                                    "tranche_group"
                                )
                            ]
                            tranches_data = {}
                            for i, tranche_df in enumerate(tranches_dfs):
                                df = tranche_df.copy()
                                if not df.empty:
                                    df.dropna(subset=[df.columns[0]], inplace=True)

                                if not df.empty:
                                    # Add original row number (1-based) as the first column
                                    df.insert(0, "#", df.index + 1)
                                    df.reset_index(drop=True, inplace=True)
                                    df.fillna("", inplace=True)

                                    table_headers = df.columns.tolist()
                                    table_data = df.astype(str).values.tolist()
                                    tranche_name = f"Tranche {i + 1}"
                                    tranches_data[tranche_name] = {
                                        "headers": table_headers,
                                        "data": table_data,
                                    }
                            if not tranches_data:
                                context["error"] = "No valid data tranches found."
                            else:
                                request.session["tranches_data"] = tranches_data
                                request.session["original_filename"] = (
                                    uploaded_file.name
                                )
                                first_tranche_name = list(tranches_data.keys())[0]
                                return redirect(
                                    f"{reverse('home')}?tranche={first_tranche_name}"
                                )
        except Exception as e:
            context["error"] = f"Could not process the file: {str(e)}"
            logger.error(f"Error processing file: {str(e)}", exc_info=True)

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
        elif selected_tranche_name:
            context["error"] = f"Tranche '{selected_tranche_name}' not found."

    return render(request, "home.html", context)


def generate_xml_content(edited_data, original_filename, username, tranche_name):
    """Generate XML content from edited data"""

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

    xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml_lines.append(
        f'<data source_file="{escape_xml(original_filename)}" tranche="{escape_xml(tranche_name)}">'
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

    # Add data rows
    xml_lines.append("  <records>")

    for i, row in enumerate(edited_data):
        xml_lines.append(f'    <record id="{i + 1}">')

        for j, cell_value in enumerate(row):
            safe_value = escape_xml(cell_value) if cell_value else ""
            xml_lines.append(f"      <column_{j + 1}>{safe_value}</column_{j + 1}>")

        xml_lines.append("    </record>")

    xml_lines.append("  </records>")
    xml_lines.append("</data>")

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
