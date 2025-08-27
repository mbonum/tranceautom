from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from upload_file.views import (
    user_login,
    user_logout,
    user_register,
    home,
    download_xml,
    planning_details,  # Aggiungiamo la vista mancante
)
from django.views.static import serve


def chrome_devtools_stub(request):
    return JsonResponse({}, status=204)


urlpatterns = [
    path(".well-known/appspecific/com.chrome.devtools.json", chrome_devtools_stub),
    path("auth/", include("social_django.urls", namespace="social")),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    path("register/", user_register, name="register"),
    path("", home, name="home"),
    path("planning/<int:planning_id>/", planning_details, name="planning_details"),
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
