"""Middleware kustom: standardisasi URL (SEO — hindari duplikasi kanonik)."""
from django.http import HttpResponsePermanentRedirect
from django.urls import Resolver404, resolve


class LowercasePathMiddleware:
    """301 untuk URL berhuruf kapital -> huruf kecil (bila versi kecil cocok).

    Google memperlakukan /BUS/ dan /bus/ sebagai halaman berbeda. Semua URL
    kanonik situs ini huruf kecil, jadi path kapital dialihkan permanen:

    * ``/BUS/`` -> 301 ``/bus/`` (versi kecil resolve, versi asli tidak)
    * ``/bus/booking/NT-ABC123/`` TIDAK disentuh — path sudah resolve dan
      kode booking memang berhuruf kapital (NT-XXXXXX / SEWA-XXXXXX).
    * Query string dipertahankan utuh.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if path != path.lower():
            try:
                resolve(path)
            except Resolver404:
                query = request.META.get('QUERY_STRING', '')
                target = path.lower() + (f'?{query}' if query else '')
                return HttpResponsePermanentRedirect(target)
        return self.get_response(request)
