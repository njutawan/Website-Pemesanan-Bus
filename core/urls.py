from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static
from django.urls import include, path
from django.contrib.sitemaps.views import sitemap
from django.views.i18n import JavaScriptCatalog

from core import views, sitemaps
from core.admin import admin_site

SITEMAPS = sitemaps.SITEMAPS

urlpatterns = [
    path('admin/', admin_site.urls),
]

# Halaman berbahasa — ID tanpa prefiks ("/"), EN dengan prefiks ("/en/")
urlpatterns += i18n_patterns(
    path('', views.HomeView.as_view(), name='home'),
    path('tentang/', views.AboutView.as_view(), name='about'),
    path('kontak/', views.ContactView.as_view(), name='contact'),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    path('bus/', include('booking.urls')),
    path('rental/', include('rental.urls')),
    prefix_default_language=False,
)

urlpatterns += [
    path('sitemap.xml', sitemap, {'sitemaps': SITEMAPS}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', views.RobotsView.as_view(), name='robots'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
