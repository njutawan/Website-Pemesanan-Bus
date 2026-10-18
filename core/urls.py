from django.conf.urls.i18n import i18n_patterns
from django.urls import include, path, re_path
from django.contrib.sitemaps.views import sitemap
from django.views.decorators.cache import cache_page
from django.views.i18n import JavaScriptCatalog

from core import views, sitemaps
from core.admin import admin_site
from core.private_media import serve_media

SITEMAPS = sitemaps.SITEMAPS

handler400 = 'core.views.error_400'
handler403 = 'core.views.error_403'
handler404 = 'core.views.error_404'
handler500 = 'core.views.error_500'

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
    # Sitemap publik & identik untuk semua — aman di-cache 30 menit (TTFB crawler)
    path('sitemap.xml', cache_page(1800)(sitemap), {'sitemaps': SITEMAPS}, name='django.contrib.sitemaps.views.sitemap'),
    path('robots.txt', views.RobotsView.as_view(), name='robots'),
]

# Media dilayani Django sebagai fallback dev/preview lewat view terkontrol
# akses (core.private_media): foto mobil & OG image publik bebas diakses,
# tetapi bukti pembayaran (payment_proofs/ & rental_proofs/) hanya untuk
# staf atau sesi pemilik bookingnya — berlaku juga saat DEBUG=0, URL saja
# tidak cukup. Di produksi Nginx menyajikan media publik langsung dan
# mem-proxy awalan bukti pembayaran ke view ini (lihat deploy/nginx.conf).
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve_media),
]
