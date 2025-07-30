from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from upload_file.views import (
    user_login,
    user_logout,
    user_register,
    home,
    # download_csv,
    download_xml,
    # process_excel_to_csv,
)
from django.views.static import serve


def chrome_devtools_stub(request):
    return JsonResponse({}, status=204)


urlpatterns = [
    path(".well-known/appspecific/com.chrome.devtools.json", chrome_devtools_stub),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("register/", user_register, name="register"),
    path("", home, name="home"),
    # path("process-excel/", process_excel_to_csv, name="process_excel"),
    # path("download-csv/", download_csv, name="download_csv"),
    path("download-xml/", download_xml, name="download_xml"),
    path(
        "favicon.ico",
        serve,
        {"path": "favicon.ico", "document_root": settings.STATIC_ROOT},
    ),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
