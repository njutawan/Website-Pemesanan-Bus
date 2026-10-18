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

    ASSET_PREFIXES = ('/static/', '/media/')

    def __call__(self, request):
        path = request.path
        if path != path.lower() and not path.startswith(self.ASSET_PREFIXES):
            # Aset statis/media TIDAK dialihkan: lookup file case-sensitive
            # (301 hanya mengubah 404 menjadi 404 dengan redirect tambahan).
            try:
                resolve(path)
            except Resolver404:
                query = request.META.get('QUERY_STRING', '')
                target = path.lower() + (f'?{query}' if query else '')
                return HttpResponsePermanentRedirect(target)
        return self.get_response(request)


class XRobotsTagMiddleware:
    """Header X-Robots-Tag: kendali perayapan per-respons (melengkapi robots.txt).

    * /admin/ & /media/ -> ``noindex, nofollow`` — halaman internal dan
      berkas unggahan (termasuk bukti pembayaran) tidak untuk mesin pencari.
    * Halaman dengan parameter pencarian dinamis (origin/destination/kode)
      -> ``noindex, follow`` — hasil pencarian per-kombinasi bukan konten
      kanonik; link-nya tetap boleh diikuti crawler.
    """

    NOINDEX_PREFIXES = ('/admin/', '/media/')
    SEARCH_PARAMS = {'origin', 'destination', 'kode', 'code', 'kategori'}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(self.NOINDEX_PREFIXES):
            response.headers.setdefault('X-Robots-Tag', 'noindex, nofollow')
        elif request.GET and set(request.GET) & self.SEARCH_PARAMS:
            response.headers.setdefault('X-Robots-Tag', 'noindex, follow')
        return response
