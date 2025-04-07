# ruff: noqa
import os
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
from django.views.generic import TemplateView

URL_PREFIX = os.getenv('DJANGO_URL_PREFIX', '').strip('/')

def prefix_url_patterns(patterns):
    if not URL_PREFIX:
        return patterns
    
    return [
        path(f'{URL_PREFIX}/', include((patterns, 'prefixed'), namespace=None))
    ]


raw_urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path(
        "about/",
        TemplateView.as_view(template_name="pages/about.html"),
        name="about",
    ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("pptp.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    path('products/', include('pptp.urls.products', namespace='products')),
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    raw_urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        raw_urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + raw_urlpatterns

if URL_PREFIX:
    urlpatterns = [
        path(f'{URL_PREFIX}/', include(raw_urlpatterns))
    ]
else:
    urlpatterns = raw_urlpatterns