from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.shortcuts import render, redirect
import csv
import logging
import io
import pandas as pd
from django.http import HttpResponse, JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.views.decorators.http import require_http_methods
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
    error = None
    preview = None
    csv_data = None
    filename = None
    file_type = None
    validation_info = None

    if request.method == "POST":
        try:
            uploaded_file = request.FILES.get("file")
            if not uploaded_file:
                error = "Please select a file."
            elif not (
                uploaded_file.name.endswith(".xlsx")
                or uploaded_file.name.endswith(".xls")
                or uploaded_file.name.endswith(".csv")
            ):
                error = "Only Excel files (xlsx, xls) and CSV files are allowed."
            else:
                file_extension = uploaded_file.name.lower().split(".")[-1]

                if file_extension == "csv":
                    # Handle CSV file
                    file_type = "CSV"
                    is_valid, result = validate_csv(uploaded_file)

                    if not is_valid:
                        error = result
                    else:
                        df = result
                        validation_info = {
                            "rows": len(df),
                            "columns": len(df.columns),
                            "column_names": list(df.columns),
                        }

                        # Create preview (limit to first 20 rows for display)
                        preview_df = df.head(20)

                        # Store original data as JSON for editing
                        table_data = []
                        table_headers = preview_df.columns.tolist()

                        # Convert data to strings to avoid JSON serialization issues
                        for _, row in preview_df.iterrows():
                            row_data = []
                            for value in row.values:
                                if pd.isna(value):
                                    row_data.append("")
                                else:
                                    row_data.append(str(value))
                            table_data.append(row_data)

                        # Store in session for XML generation
                        request.session["table_data"] = table_data
                        request.session["table_headers"] = table_headers

                        preview = preview_df.to_html(
                            classes="table table-striped table-bordered",
                            index=False,
                            table_id="csv-preview",
                        )

                        # For CSV files, we can optionally store the data for re-download
                        uploaded_file.seek(0)
                        csv_data = uploaded_file.read().decode("utf-8")
                        filename = uploaded_file.name

                        request.session["csv_data"] = csv_data
                        request.session["csv_filename"] = filename

                else:
                    # Handle Excel file
                    file_type = "Excel"
                    uploaded_file.seek(0)
                    df = pd.read_excel(
                        uploaded_file, sheet_name="PIANIFICAZIONE", engine="openpyxl"
                    )

                    # Convert to CSV
                    csv_buffer = io.StringIO()
                    df.to_csv(csv_buffer, index=False)
                    csv_data = csv_buffer.getvalue()

                    # Generate filename for download
                    base_filename = uploaded_file.name.rsplit(".", 1)[0]
                    filename = f"{base_filename}_PIANIFICAZIONE.csv"

                    validation_info = {
                        "rows": len(df),
                        "columns": len(df.columns),
                        "column_names": list(df.columns),
                    }

                    # Create preview (limit to first 20 rows for display)
                    preview_df = df  # .head(20)

                    # Store original data as JSON for editing
                    table_data = []
                    table_headers = preview_df.columns.tolist()

                    # Convert data to strings to avoid JSON serialization issues
                    for _, row in preview_df.iterrows():
                        row_data = []
                        for value in row.values:
                            if pd.isna(value):
                                row_data.append("")
                            else:
                                row_data.append(str(value))
                        table_data.append(row_data)

                    # Store in session for XML generation
                    request.session["table_data"] = table_data
                    request.session["table_headers"] = table_headers

                    preview = preview_df.to_html(
                        classes="table table-striped table-bordered",
                        index=False,
                        table_id="csv-preview",
                    )

                    # Store CSV data in session for download
                    request.session["csv_data"] = csv_data
                    request.session["csv_filename"] = filename

        except Exception as e:
            error = f"Could not process the file: {str(e)}"
            logger.error(f"Error processing file: {str(e)}")

    return render(
        request,
        "home.html",
        {
            "error": error,
            "preview": preview,
            "filename": filename,
            "file_type": file_type,
            "validation_info": validation_info,
            "table_data": request.session.get("table_data", []),
            "table_headers": request.session.get("table_headers", []),
        },
    )


# Update your existing download views to require login
@login_required
def download_xml(request):
    """View to handle XML download with edited data"""
    import json

    try:
        if request.method == "POST":
            # Get edited data from the request
            edited_data_str = request.POST.get("edited_data", "[]")
            edited_data = json.loads(edited_data_str)
            original_filename = request.session.get(
                "csv_filename", "converted_file.csv"
            )

            if not edited_data:
                return HttpResponse("No data available for download.", status=400)

            # Create XML manually to avoid import issues
            xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
            xml_lines.append(f'<data source_file="{original_filename}">')

            # Add metadata
            xml_lines.append("  <metadata>")
            xml_lines.append(f"    <total_rows>{len(edited_data)}</total_rows>")
            xml_lines.append(
                f"    <total_columns>{len(edited_data[0]) if edited_data else 0}</total_columns>"
            )
            xml_lines.append(f"    <generated_at>{pd.Timestamp.now()}</generated_at>")
            xml_lines.append(f"    <user>{request.user.username}</user>")
            xml_lines.append("  </metadata>")

            # Add data rows
            xml_lines.append("  <records>")

            for i, row in enumerate(edited_data):
                xml_lines.append(f'    <record id="{i + 1}">')

                for j, cell_value in enumerate(row):
                    # Escape XML special characters
                    safe_value = (
                        str(cell_value)
                        .replace("&", "&amp;")
                        .replace("<", "&lt;")
                        .replace(">", "&gt;")
                        .replace('"', "&quot;")
                        .replace("'", "&apos;")
                        if cell_value
                        else ""
                    )
                    xml_lines.append(
                        f"      <column_{j + 1}>{safe_value}</column_{j + 1}>"
                    )

                xml_lines.append("    </record>")

            xml_lines.append("  </records>")
            xml_lines.append("</data>")

            # Join all lines
            xml_content = "\n".join(xml_lines)

            # Generate filename
            base_filename = (
                original_filename.rsplit(".", 1)[0] if original_filename else "data"
            )
            xml_filename = f"{base_filename}_edited_by_{request.user.username}.xml"

            response = HttpResponse(xml_content, content_type="application/xml")
            response["Content-Disposition"] = f'attachment; filename="{xml_filename}"'

            return response

        return HttpResponse("Invalid request method.", status=405)

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        return HttpResponse("Invalid data format.", status=400)
    except Exception as e:
        logger.error(f"Error generating XML: {e}")
        return HttpResponse("Error generating XML file.", status=500)


@login_required
def download_csv(request):
    """View to handle CSV download (kept for backward compatibility)"""
    csv_data = request.session.get("csv_data")
    filename = request.session.get("csv_filename", "converted_file.csv")

    if not csv_data:
        return HttpResponse("No CSV data available for download.", status=400)

    response = HttpResponse(csv_data, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response


def process_excel_to_csv(request):
    """
    View to handle Excel file upload and processing
    """
    if request.method == "GET":
        return render(request, "upload_form.html")

    elif request.method == "POST":
        if "excel_file" not in request.FILES:
            return JsonResponse({"error": "No file uploaded"}, status=400)

        excel_file = request.FILES["excel_file"]

        try:
            # Process the Excel file
            csv_data = process_excel_sheets(excel_file)

            if not csv_data:
                return JsonResponse(
                    {"error": "No sheets found with required columns"}, status=400
                )

            # Create HTTP response with CSV data
            response = HttpResponse(csv_data, content_type="text/csv")
            response["Content-Disposition"] = (
                'attachment; filename="processed_data.csv"'
            )
            return response

        except Exception as e:
            return JsonResponse(
                {"error": f"Error processing file: {str(e)}"}, status=500
            )


def process_excel_sheets(excel_file):
    """
    Process Excel file and return CSV data for sheets with required columns
    """
    required_columns = ["Chiave articolo", "Merceologia", "Tranche", "Data inizio"]

    try:
        # Read all sheets from Excel file
        excel_data = pd.read_excel(excel_file, sheet_name=None, engine="openpyxl")

        processed_data = []

        for sheet_name, df in excel_data.items():
            # Check if sheet has all required columns
            if has_required_columns(df, required_columns):
                # Process the sheet and convert to desired format
                formatted_rows = format_sheet_data(df, required_columns)
                processed_data.extend(formatted_rows)

        if not processed_data:
            return None

        # Convert to CSV string
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header (optional - remove if not needed)
        # writer.writerow(['Formatted_Data'])

        # Write data rows
        for row in processed_data:
            writer.writerow([row])

        csv_content = output.getvalue()
        output.close()

        return csv_content

    except Exception as e:
        raise Exception(f"Error reading Excel file: {str(e)}")


def has_required_columns(df, required_columns):
    """
    Check if dataframe has all required columns
    """
    df_columns = [col.strip() for col in df.columns.astype(str)]
    return all(req_col in df_columns for req_col in required_columns)


def format_sheet_data(df, required_columns):
    """
    Format sheet data according to the specified string format
    Based on your example: 0SN1796039EXS,1796-039E,M Slip Normale D C,AAP,25MD,0SN1796  039EXS,0SN1796,039E,XS,AAP,2025-06-12

    This function needs to be customized based on your actual data structure
    and how you want to map the columns to the output format.
    """
    formatted_rows = []

    # Clean column names
    df.columns = [col.strip() for col in df.columns.astype(str)]

    for index, row in df.iterrows():
        try:
            # Extract required column values
            chiave_articolo = (
                str(row["Chiave articolo"]).strip()
                if pd.notna(row["Chiave articolo"])
                else ""
            )
            merceologia = (
                str(row["Merceologia"]).strip() if pd.notna(row["Merceologia"]) else ""
            )
            tranche = str(row["Tranche"]).strip() if pd.notna(row["Tranche"]) else ""
            data_inizio = row["Data inizio"]

            # Format date
            if pd.notna(data_inizio):
                if isinstance(data_inizio, str):
                    # Try to parse string date
                    try:
                        date_obj = pd.to_datetime(data_inizio)
                        formatted_date = date_obj.strftime("%Y-%m-%d")
                    except Exception:
                        formatted_date = str(data_inizio)
                else:
                    formatted_date = pd.to_datetime(data_inizio).strftime("%Y-%m-%d")
            else:
                formatted_date = ""

            # Create formatted string based on your example pattern
            # You'll need to customize this logic based on your actual data structure
            # This is a template - adjust according to your specific requirements

            # Example format: 0SN1796039EXS,1796-039E,M Slip Normale D C,AAP,25MD,0SN1796  039EXS,0SN1796,039E,XS,AAP,2025-06-12
            formatted_string = create_formatted_string(
                chiave_articolo,
                merceologia,
                tranche,
                formatted_date,
                row,  # Pass entire row in case you need other columns
            )

            if formatted_string:  # Only add non-empty strings
                formatted_rows.append(formatted_string)

        except Exception as e:
            # Log error for this row but continue processing
            print(f"Error processing row {index}: {str(e)}")
            continue

    return formatted_rows


def create_formatted_string(chiave_articolo, merceologia, tranche, formatted_date, row):
    """
    Create the formatted string based on your specific requirements.
    You'll need to customize this function based on how your data maps
    to the desired output format.

    Example output: 0SN1796039EXS,1796-039E,M Slip Normale D C,AAP,25MD,0SN1796  039EXS,0SN1796,039E,XS,AAP,2025-06-12
    """

    # This is a template implementation - customize based on your data structure
    # You may need additional columns or different logic

    try:
        # Extract or generate components for your format
        # Adjust these based on your actual data structure

        component1 = chiave_articolo  # First component
        component2 = extract_component2(
            chiave_articolo
        )  # Second component (derived from chiave_articolo?)
        component3 = merceologia  # Third component
        component4 = tranche  # Fourth component
        component5 = extract_component5(row)  # Fifth component (from other column?)
        component6 = extract_component6(chiave_articolo)  # Sixth component
        component7 = extract_component7(chiave_articolo)  # Seventh component
        component8 = extract_component8(chiave_articolo)  # Eighth component
        component9 = extract_component9(row)  # Ninth component
        component10 = tranche  # Tenth component (reuse tranche?)
        component11 = formatted_date  # Date component

        # Combine components
        formatted_string = f"{component1},{component2},{component3},{component4},{component5},{component6},{component7},{component8},{component9},{component10},{component11}"

        return formatted_string

    except Exception as e:
        print(f"Error creating formatted string: {str(e)}")
        return None


# Helper functions to extract components - customize based on your data
def extract_component2(chiave_articolo):
    """Extract second component from chiave_articolo"""
    # Example logic - customize based on your data pattern
    if len(chiave_articolo) >= 10:
        return f"{chiave_articolo[3:7]}-{chiave_articolo[7:11]}"
    return chiave_articolo


def extract_component5(row):
    """Extract fifth component from row data"""
    # Add logic based on your data structure
    # This might come from another column in your Excel
    return "25MD"  # Placeholder


def extract_component6(chiave_articolo):
    """Extract sixth component"""
    # Add logic based on your data pattern
    return chiave_articolo  # Placeholder


def extract_component7(chiave_articolo):
    """Extract seventh component"""
    # Add logic based on your data pattern
    if len(chiave_articolo) >= 7:
        return chiave_articolo[:7]
    return chiave_articolo


def extract_component8(chiave_articolo):
    """Extract eighth component"""
    # Add logic based on your data pattern
    if len(chiave_articolo) >= 11:
        return chiave_articolo[7:11]
    return ""


def extract_component9(row):
    """Extract ninth component"""
    # This might come from another column or be derived
    return "XS"  # Placeholder
