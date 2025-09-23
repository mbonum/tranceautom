from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.http import JsonResponse
from django.urls import include, path
from upload_file.views import (
    home,
    # upload_file,
    data_view,
    download_xml,
)
from upload_file.api_views import (
    save_products,
    get_product_details,
    bulk_update_products,
    validate_product_data,
    apply_visibility_rules_to_product,
)
# from django.views.static import serve
from django.contrib.staticfiles.storage import staticfiles_storage
from django.views.generic.base import RedirectView


def chrome_devtools_stub(request):
    return JsonResponse({}, status=204)


urlpatterns = [
    path(".well-known/appspecific/com.chrome.devtools.json", chrome_devtools_stub),
    path("auth/", include("social_django.urls", namespace="social")),
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", home, name="home"),
    path("dati/<int:import_id>/", data_view, name="data_view"),
    path("download-xml/<int:import_id>/", download_xml, name="download_xml"),
    
    # API endpoints
    path("api/products/save/", save_products, name="api_save_products"),
    path("api/products/<int:product_id>/", get_product_details, name="api_product_details"),
    path("api/products/<int:product_id>/apply-visibility-rules/", apply_visibility_rules_to_product, name="apply_visibility_rules_to_product"),
    path("api/products/bulk-update/", bulk_update_products, name="api_bulk_update"),
    path("api/products/validate/", validate_product_data, name="api_validate_product"),
    
    path(
        "favicon.ico", RedirectView.as_view(url=staticfiles_storage.url("favicon.ico"))
    ),
    # path(
    #     "favicon.ico",
    #     serve,
    #     {"path": "favicon.ico", # "document_root": settings.STATIC_ROOT},
    # ),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
