"""
Kompilasi berkas terjemahan TANPA gettext CLI (menggunakan polib).

python manage.py compile_i18n

1. Ekstrak semua string {% trans %}, {% blocktrans %}, gettext()/_() dari
   templates & kode.
2. Gabungkan dengan kamus core/translations.py.
3. Tulis locale/id/LC_MESSAGES/django.po lalu kompilasi django.mo.
"""
import re
from pathlib import Path

import polib
from django.conf import settings
from django.core.management.base import BaseCommand

from core.translations import TRANSLATIONS_EN, TRANSLATIONS_ID

BASE_DIR = Path(settings.BASE_DIR)

TRANS_RE = re.compile(r"""\{%-?\s*trans\s+['"](.+?)['"][^%]*-?%\}""")
BLOCK_RE = re.compile(
    r"""\{%-?\s*blocktrans(late)?\b(?P<args>[^%]*)-?%\}(?P<body>.*?)\{%-?\s*endblocktrans(late)?\s*-?%\}""",
    re.DOTALL,
)
PLURAL_RE = re.compile(r"""\{%-?\s*plural\s*-?%\}""")
VAR_RE = re.compile(r"""\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}""")
PY_RE = re.compile(
    r"""\b(?:gettext_lazy|gettext|ngettext_lazy|ngettext|_)\(\s*(?P<q>['"])(?P<s>.*?)(?P=q)""",
    re.DOTALL,
)

PO_HEADER = """Katalog terjemahan Bahasa Indonesia — Nusantara Trans"""


def collapse(text: str) -> str:
    return re.sub(r'\s+', ' ', text).strip()


def block_to_msgid(body: str, argstr: str):
    """Ubah isi blocktranslate jadi (msgid, msgid_plural|None)."""
    # kumpulkan nama variabel dari argumen with/count (kanan boleh titik/filter)
    valid_names = set(re.findall(r"""(?:with|count)\s+(.*)""", argstr, re.DOTALL))
    names = set()
    for chunk in valid_names:
        for pair in chunk.split():
            if '=' in pair:
                names.add(pair.split('=', 1)[0])

    def repl(m):
        var = m.group(1)
        base = var.split('.')[0]
        if '.' in var or (names and base not in names):
            raise ValueError(
                f'Variabel "{var}" di dalam blocktranslate harus dideklarasikan '
                f'dengan with/count tanpa titik. Perbaiki template.')
        return f'%({base})s'

    parts = PLURAL_RE.split(body)
    singular = collapse(VAR_RE.sub(repl, parts[0]))
    plural = collapse(VAR_RE.sub(repl, parts[1])) if len(parts) > 1 else None
    return singular, plural


class Command(BaseCommand):
    help = 'Ekstrak string terjemahan & kompilasi locale/id ke .mo (via polib).'

    def handle(self, *args, **options):
        msgids = {}  # msgid -> plural|None

        # 1) Template
        for path in sorted((BASE_DIR / 'templates').rglob('*.html')):
            src = path.read_text(encoding='utf-8')
            for m in TRANS_RE.finditer(src):
                msgids.setdefault(collapse(m.group(1)), None)
            for m in BLOCK_RE.finditer(src):
                try:
                    msgid, plural = block_to_msgid(m.group('body'), m.group('args') or '')
                except ValueError as e:
                    self.stdout.write(self.style.ERROR(f'{path.name}: {e}'))
                    continue
                if msgid:
                    msgids[msgid] = plural

        # 2) Kode Python
        py_files = []
        for app in ('core', 'booking', 'rental'):
            py_files += list((BASE_DIR / app).rglob('*.py'))
        for path in sorted(py_files):
            if 'migrations' in str(path):
                continue
            src = path.read_text(encoding='utf-8')
            for m in PY_RE.finditer(src):
                msgid = collapse(m.group('s').replace("\\'", "'"))
                if not re.search(r'\w', msgid):
                    continue  # buang hasil regex sampah (tanda kutip kosong dsb.)
                msgids.setdefault(msgid, None)

        # 3) Buat PO untuk setiap bahasa (id = kamus ID, en = kamus EN)
        catalogs = {
            'id': (TRANSLATIONS_ID, 'Bahasa Indonesia'),
            'en': (TRANSLATIONS_EN, 'English'),
        }
        for lang, (kamus, nama) in catalogs.items():
            po = polib.POFile()
            po.metadata = {
                'Project-Id-Version': '1.0',
                'MIME-Version': '1.0',
                'Content-Type': 'text/plain; charset=UTF-8',
                'Content-Transfer-Encoding': '8bit',
                'Language': lang,
                'Plural-Forms': 'nplurals=1; plural=0;',
                'X-Generator': 'compile_i18n (polib)',
            }
            missing = []
            for msgid, plural in sorted(msgids.items()):
                entry = polib.POEntry(msgid=msgid)
                terjemahan = kamus.get(msgid, '')
                if plural:
                    entry.msgid_plural = plural
                    entry.msgstr_plural = {0: terjemahan}
                else:
                    entry.msgstr = terjemahan
                if not terjemahan:
                    missing.append(f'{msgid} | {plural}' if plural else msgid)
                po.append(entry)

            po_dir = BASE_DIR / 'locale' / lang / 'LC_MESSAGES'
            po_dir.mkdir(parents=True, exist_ok=True)
            po.save(str(po_dir / 'django.po'))
            po.save_as_mofile(str(po_dir / 'django.mo'))

            total = len(msgids)
            self.stdout.write(self.style.SUCCESS(
                f'✔ locale/{lang} ({nama}): {total} string, '
                f'{total - len(missing)} diterjemahkan, {len(missing)} fallback msgid.'))
            if missing:
                self.stdout.write(self.style.WARNING(f'  Tanpa terjemahan ({lang}):'))
                for item in missing:
                    self.stdout.write(f'    - {item}')
