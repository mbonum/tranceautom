from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.urls import include, path
from upload_file.views_simple import (
    home,
    # upload_file,
    data_view,
)
from django.views.static import serve


def chrome_devtools_stub(request):
    return JsonResponse({}, status=204)


urlpatterns = [
    path(".well-known/appspecific/com.chrome.devtools.json", chrome_devtools_stub),
    path("auth/", include("social_django.urls", namespace="social")),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", home, name="home"),
    path("dati/<int:import_id>/", data_view, name="data_view"),
    path(
        "favicon.ico",
        serve,
        {"path": "favicon.ico", "document_root": settings.STATIC_ROOT},
    ),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
