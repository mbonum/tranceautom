from django.shortcuts import render
import logging
import pandas as pd
# from io import BytesIO


logger = logging.getLogger(__name__)


def home(request):
    error = None
    preview = None
    if request.method == "POST":
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            error = "Please select a file."
        elif not (
            uploaded_file.name.endswith(".xlsx") or uploaded_file.name.endswith(".xls")
        ):
            error = "Only excel files (xlsx, xls) are allowed."
        else:
            try:
                uploaded_file.seek(0)
                df = pd.read_excel(uploaded_file, sheet_name="PIANIFICAZIONE", engine="openpyxl")  # , nrows=20
                preview = df.to_html(
                    classes="table table-striped table-bordered", index=False
                )
            except Exception as e:
                error = "Could not read the excel file."
                logger.exception("Error reading Excel file: %s", e)
    return render(request, "home.html", {"error": error, "preview": preview})
