import os
from .models import PianificazioneImport
import logging

logger = logging.getLogger(__name__)


def _is_valid_file_type(uploaded_file):
    """Validate if uploaded file is a valid Excel file"""
    if not uploaded_file:
        return False

    # Check file extension
    allowed_extensions = [".xlsx", ".xls"]
    file_extension = os.path.splitext(uploaded_file.name)[1].lower()

    return file_extension in allowed_extensions


def _get_recent_imports(user, limit=10):
    """Get recent imports for a user"""
    return PianificazioneImport.objects.filter(imported_by=user).order_by(
        "-imported_at"
    )[:limit]  # Fixed: use imported_at instead of created_at


def _get_user_plannings(user):
    """Get user plannings for the UI"""
    return PianificazioneImport.objects.filter(
        imported_by=user, status="processed"
    ).order_by("-imported_at")[:20]
