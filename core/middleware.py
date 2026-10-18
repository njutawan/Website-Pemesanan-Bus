"""Middleware kustom: keamanan (CSP, CORS, rate limit, allowlist admin),
standardisasi URL (SEO), dan header bot.

Urutan pemasangan di ``settings.MIDDLEWARE`` penting:

* ``SecurityHeadersMiddleware`` sedekat mungkin dengan atas agar header tetap
  terpasang pada respons 4xx/5xx dan respons middleware lain.
* ``CorsMiddleware`` & ``RateLimitMiddleware`` sebelum view agar request
  lintas-origin/berlebihan ditolak tanpa menyentuh database.
* ``BlockSourceMapsMiddleware`` sebelum WhiteNoise agar ``*.map`` tidak pernah
  tersaji walau berkasnya ada di disk.
"""
import base64
import hashlib
import ipaddress
import logging
import re
import time

from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseNotFound
from django.urls import Resolver404, resolve

logger = logging.getLogger('audit')
security_logger = logging.getLogger('django.security')


# ---------------------------------------------------------------------------
# Utilitas IP
# ---------------------------------------------------------------------------
def get_client_ip(request):
    """IP klien dengan menghormati X-Forwarded-For HANYA dari proxy tepercaya.

    Tanpa ini, penyerang bisa memalsukan header X-Forwarded-For untuk
    melewati rate limit atau allowlist admin.
    """
    remote = (request.META.get('REMOTE_ADDR') or '').strip()
    trusted = getattr(settings, 'TRUSTED_PROXY_IPS', ())
    if _ip_in_networks(remote, trusted):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if forwarded:
            # Ambil elemen PALING KANAN: proxy tepercaya menambahkan IP
            # sebenarnya di akhir. Mengambil yang pertama memudahkan
            # penyerang memalsukan "X-Forwarded-For: 1.2.3.4" untuk
            # melewati rate limit/allowlist.
            for candidate in reversed(forwarded.split(',')):
                candidate = candidate.strip()
                if _is_ip(candidate):
                    return candidate
    return remote if _is_ip(remote) else '0.0.0.0'


def _is_ip(value):
    try:
        ipaddress.ip_address(str(value))
        return True
    except ValueError:
        return False


def _ip_in_networks(ip, networks):
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    for raw in networks:
        try:
            if address in ipaddress.ip_network(str(raw).strip(), strict=False):
                return True
        except ValueError:
            continue
    return False


# ---------------------------------------------------------------------------
# Header proxy tepercaya
# ---------------------------------------------------------------------------
class TrustedProxyHeadersMiddleware:
    """Hormati ``X-Forwarded-Proto`` hanya dari proxy yang terdaftar.

    Django membaca ``SECURE_PROXY_SSL_HEADER`` tanpa memeriksa asal request.
    Bila aplikasi (tanpa Nginx) dapat dihubungi langsung, klien bisa mengirim
    ``X-Forwarded-Proto: https`` untuk membuat ``request.is_secure()`` True —
    berbahaya untuk pemeriksaan CSRF/redirect. Middleware ini membuang header
    tersebut bila ``REMOTE_ADDR`` tidak ada di ``TRUSTED_PROXY_IPS``.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        remote = (request.META.get('REMOTE_ADDR') or '').strip()
        trusted = getattr(settings, 'TRUSTED_PROXY_IPS', ())
        if not _ip_in_networks(remote, trusted):
            request.META.pop('HTTP_X_FORWARDED_PROTO', None)
        return self.get_response(request)


# ---------------------------------------------------------------------------
# Header keamanan + Content-Security-Policy
# ---------------------------------------------------------------------------
# <script>...</script> tanpa atribut src -> hash SHA-256 dimasukkan ke CSP.
# Hash dihitung PER RESPONS sehingga tetap benar untuk halaman ber-cache_page
# (nonce tidak kompatibel dengan cache bersama: nonce baru + body lama =
# script diblokir).
_INLINE_SCRIPT_RE = re.compile(
    rb'<script\b(?P<attrs>[^>]*)>(?P<body>.*?)</script\s*>',
    re.IGNORECASE | re.DOTALL,
)
_HTML_TYPES = ('text/html', 'application/xhtml+xml')


def inline_script_hashes(content: bytes):
    """Daftar ``'sha256-...'`` untuk semua inline script pada HTML."""
    hashes = []
    for match in _INLINE_SCRIPT_RE.finditer(content or b''):
        attrs = match.group('attrs') or b''
        if re.search(rb'\bsrc\s*=', attrs, re.IGNORECASE):
            continue
        digest = base64.b64encode(hashlib.sha256(match.group('body')).digest())
        hashes.append("'sha256-%s'" % digest.decode('ascii'))
    # Duplikat dibuang, urutan stabil.
    return list(dict.fromkeys(hashes))


class SecurityHeadersMiddleware:
    """Header keamanan konsisten untuk semua respons.

    * CSP ketat untuk halaman publik: tanpa ``unsafe-inline`` pada script;
      inline script (JSON-LD & skrip kecil) diizinkan lewat hash SHA-256.
    * CSP admin lebih longgar (Django admin memakai inline handler/script),
      tetapi tetap mengunci object/frame/base/form.
    * ``frame-ancestors`` hanya dikunci di produksi agar pratinjau sandbox
      berbasis iframe tetap berfungsi.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        self._apply(request, response)
        return response

    def _apply(self, request, response):
        # Jangan menimpa CSP khusus (mis. media: default-src 'none'; sandbox).
        if getattr(settings, 'CSP_ENABLED', True) and not response.has_header(
                'Content-Security-Policy'):
            if request.path.startswith('/admin/'):
                policy = self._admin_policy()
            else:
                policy = self._public_policy(response)
            header = ('Content-Security-Policy-Report-Only'
                      if getattr(settings, 'CSP_REPORT_ONLY', False)
                      else 'Content-Security-Policy')
            response[header] = policy

        response.setdefault('X-Content-Type-Options', 'nosniff')
        response.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.setdefault(
            'Permissions-Policy',
            'accelerometer=(), autoplay=(), camera=(), geolocation=(), '
            'gyroscope=(), magnetometer=(), microphone=(), payment=(), '
            'usb=(), interest-cohort=()',
        )
        response.setdefault('Cross-Origin-Opener-Policy', 'same-origin')
        response.setdefault('Cross-Origin-Resource-Policy', 'same-origin')
        response.setdefault('X-Permitted-Cross-Domain-Policies', 'none')

        if getattr(settings, 'SECURE_SSL_REDIRECT', False):
            # X-Frame-Options hanya di produksi: di preview iframe dibutuhkan.
            options = getattr(settings, 'X_FRAME_OPTIONS', 'DENY')
            if options:
                response.setdefault('X-Frame-Options', options)
        else:
            response.headers.pop('X-Frame-Options', None)

        if request.path.startswith('/admin/'):
            response.setdefault('Cache-Control', 'private, no-store')

        # Jangan bocorkan versi server framework.
        if 'Server' in response:
            del response['Server']

    def _public_policy(self, response):
        hashes = []
        content_type = (response.get('Content-Type') or '').split(';')[0].strip()
        if (response.status_code != 304
                and content_type in _HTML_TYPES
                and not getattr(response, 'streaming', False)):
            try:
                hashes = inline_script_hashes(response.content)
            except Exception:  # pragma: no cover — respons tak terbaca
                hashes = []
        script_src = "'self'" + ((' ' + ' '.join(hashes)) if hashes else '')
        styles = ' '.join(getattr(settings, 'CSP_STYLE_ORIGINS', ()))
        fonts = ' '.join(getattr(settings, 'CSP_FONT_ORIGINS', ()))
        frames = ("frame-ancestors 'none'; "
                  if getattr(settings, 'SECURE_SSL_REDIRECT', False) else '')
        upgrade = ('upgrade-insecure-requests; '
                   if getattr(settings, 'SECURE_SSL_REDIRECT', False) else '')
        return (
            "default-src 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            f"{frames}"
            "form-action 'self'; "
            f"script-src {script_src}; "
            "script-src-attr 'none'; "
            f"style-src 'self' 'unsafe-inline' {styles}; "
            f"font-src 'self' {fonts}; "
            "img-src 'self' data:; "
            "media-src 'self'; "
            "frame-src 'none'; "
            "connect-src 'self'; "
            "worker-src 'self'; "
            "manifest-src 'self'; "
            f"{upgrade}".strip().rstrip(';') + ';'
        )

    def _admin_policy(self):
        frames = ("frame-ancestors 'none'; "
                  if getattr(settings, 'SECURE_SSL_REDIRECT', False) else '')
        return (
            "default-src 'self'; "
            "base-uri 'self'; "
            "object-src 'none'; "
            f"{frames}"
            "form-action 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; "
            "font-src 'self' https://cdnjs.cloudflare.com; "
            "img-src 'self' data:; "
            "frame-src 'self'; "
            "connect-src 'self'; "
            "worker-src 'self'; "
        ).strip()


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
class CorsMiddleware:
    """CORS eksplisit tanpa wildcard.

    Default: tidak ada header CORS sama sekali (browser memblokir pembacaan
    lintas-origin). Hanya origin yang terdaftar di ``CORS_ALLOWED_ORIGINS``
    yang mendapat ``Access-Control-Allow-Origin`` persis (echo), bukan ``*``.
    Preflight dari origin tak terdaftar ditolak 403.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _allowed(origin):
        if not origin or origin == 'null':
            return False
        allowed = [o.rstrip('/') for o in getattr(
            settings, 'CORS_ALLOWED_ORIGINS', ()) if o != '*']
        return origin.rstrip('/') in allowed

    def __call__(self, request):
        origin = request.headers.get('Origin', '')
        requested_method = request.headers.get('Access-Control-Request-Method')
        is_preflight = request.method == 'OPTIONS' and bool(requested_method)

        if is_preflight:
            if not self._allowed(origin):
                return HttpResponse(
                    'CORS origin tidak diizinkan.', status=403,
                    content_type='text/plain; charset=utf-8')
            response = HttpResponse(status=204)
            response['Access-Control-Allow-Origin'] = origin
            response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            response['Access-Control-Allow-Headers'] = (
                'Content-Type, X-CSRFToken, X-Requested-With')
            response['Access-Control-Max-Age'] = '600'
            response['Vary'] = 'Origin'
            return response

        response = self.get_response(request)
        if self._allowed(origin):
            response['Access-Control-Allow-Origin'] = origin
            response['Vary'] = 'Origin'
            if getattr(settings, 'CORS_ALLOW_CREDENTIALS', False):
                response['Access-Control-Allow-Credentials'] = 'true'
        return response


# ---------------------------------------------------------------------------
# Rate limit
# ---------------------------------------------------------------------------
_RATE_SCOPE_PATTERNS = (
    ('booking_create', re.compile(r'^/(?:en/)?bus/pesan/\d+/?$')),
    # Form sewa mobil juga membuat booking (jangan hanya bus yang dibatasi).
    ('booking_create', re.compile(
        r'^/(?:en/)?rental/mobil/[^/]+/sewa/?$')),
    ('proof_upload', re.compile(
        r'^/(?:en/)?(?:bus/booking|rental/sewa)/[^/]+/upload/?$')),
    ('lookup', re.compile(
        r'^/(?:en/)?(?:bus/booking|bus/cek-booking|rental/sewa)/[^/]*/?$')),
)


class RateLimitMiddleware:
    """Rate limit fixed-window per IP, disimpan di cache.

    Semua request kena ``global``. Request non-GET/HEAD/OPTIONS kena
    ``unsafe``. Endpoint sensitif punya kuota tambahan (login admin, buat
    booking, upload bukti, pencarian kode booking). Nilai default aman untuk
    situs publik; bisa diubah lewat ``RATELIMIT_RULES``.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'RATELIMIT_ENABLED', True):
            return self.get_response(request)
        path = request.path
        if path.startswith(getattr(settings, 'RATELIMIT_EXEMPT_PREFIXES', ())):
            return self.get_response(request)

        ip = get_client_ip(request)
        scopes = [('global', ip)]
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            scopes.append(('unsafe', ip))

        if request.method == 'POST' and path.startswith('/admin/login/'):
            scopes.append(('admin_login', ip))
            username = self._admin_username(request)
            if username:
                digest = hashlib.sha256(
                    username.casefold().encode('utf-8')).hexdigest()[:24]
                scopes.append(('admin_login_user', digest))

        for scope, pattern in _RATE_SCOPE_PATTERNS:
            if pattern.match(path):
                scopes.append((scope, ip))
                break

        for scope, identity in scopes:
            allowed, retry_after, count = self._hit(scope, identity)
            if not allowed:
                if count == self._limit(scope) + 1:
                    # Audit hanya pada pelanggaran pertama per jendela.
                    self._audit_block(request, scope, ip)
                response = HttpResponse(
                    'Terlalu banyak permintaan. Coba lagi dalam %d detik.'
                    % retry_after,
                    status=429,
                    content_type='text/plain; charset=utf-8',
                )
                response['Retry-After'] = str(retry_after)
                response['Cache-Control'] = 'no-store'
                return response
        return self.get_response(request)

    @staticmethod
    def _limit(scope):
        rule = (getattr(settings, 'RATELIMIT_RULES', {}) or {}).get(scope) or {}
        return int(rule.get('limit', 0) or 0)

    def _hit(self, scope, identity):
        rule = (getattr(settings, 'RATELIMIT_RULES', {}) or {}).get(scope) or {}
        limit = int(rule.get('limit', 0) or 0)
        window = int(rule.get('window', 60) or 60)
        if limit <= 0:
            return True, 0, 0
        now = int(time.time())
        bucket = now // window
        key = f'rl:{scope}:{bucket}:{identity}'
        try:
            cache.add(key, 0, timeout=window + 5)
            try:
                count = cache.incr(key)
            except ValueError:
                cache.set(key, 1, timeout=window + 5)
                count = 1
        except Exception:  # cache down: jangan jatuhkan situs
            security_logger.warning(
                'Rate limit cache tidak tersedia; request diteruskan.')
            return True, 0, 0
        retry_after = window - (now % window)
        return count <= limit, retry_after, count

    @staticmethod
    def _admin_username(request):
        try:
            return (request.POST.get('username') or '').strip()[:150]
        except Exception:
            return ''

    @staticmethod
    def _audit_block(request, scope, ip):
        # Log sekali per kejadian (bukan per request beruntun) sudah cukup;
        # hindari banjir DB saat serangan.
        logger.warning(
            'RATE_LIMIT scope=%s ip=%s path=%s', scope, ip, request.path)
        try:
            from core.audit import log_event
            log_event(
                'RATE_LIMITED', request=request, success=False,
                target=scope, metadata={'scope': scope},
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Allowlist admin
# ---------------------------------------------------------------------------
class AdminIPAllowlistMiddleware:
    """Batasi /admin/ ke CIDR tertentu bila ``ADMIN_ALLOWED_IPS`` diisi.

    Respons 404 (bukan 403) agar keberadaan panel tidak terkonfirmasi.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        networks = getattr(settings, 'ADMIN_ALLOWED_IPS', ())
        if request.path.startswith('/admin/') and networks:
            ip = get_client_ip(request)
            if not _ip_in_networks(ip, networks):
                logger.warning(
                    'ADMIN_IP_DENIED ip=%s path=%s', ip, request.path)
                return HttpResponseNotFound(
                    'Halaman tidak ditemukan.',
                    content_type='text/plain; charset=utf-8',
                )
        return self.get_response(request)


# ---------------------------------------------------------------------------
# Source map
# ---------------------------------------------------------------------------
class BlockSourceMapsMiddleware:
    """Tolak semua permintaan ``*.map`` (source map tidak untuk publik)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.lower().endswith('.map'):
            response = HttpResponseNotFound(
                'Berkas tidak ditemukan.',
                content_type='text/plain; charset=utf-8',
            )
            response['Cache-Control'] = 'no-store'
            return response
        return self.get_response(request)


# ---------------------------------------------------------------------------
# Standardisasi URL (SEO — hindari duplikasi kanonik) & header bot
# ---------------------------------------------------------------------------
class LowercasePathMiddleware:
    """301 untuk URL berhuruf kapital -> huruf kecil (bila versi kecil cocok).

    Google memperlakukan /BUS/ dan /bus/ sebagai halaman berbeda. Semua URL
    kanonik situs ini huruf kecil, jadi path kapital dialihkan permanen:

    * ``/BUS/`` -> 301 ``/bus/`` (versi kecil resolve, versi asli tidak)
    * ``/bus/booking/NT-A7K2QP9M/`` TIDAK disentuh — path sudah resolve dan
      kode booking memang berhuruf kapital (NT-XXXXXXXX / SEWA-XXXXXXXX).
    * Query string dipertahankan utuh.
    """

    ASSET_PREFIXES = ('/static/', '/media/')

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        from django.http import HttpResponsePermanentRedirect
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
