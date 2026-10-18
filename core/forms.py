"""Form bukti pembayaran bersama (dipakai modul booking & rental)."""
from pathlib import Path

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

from core.settings import PAYMENT_METHODS


def manual_payment_methods():
    """Metode yang perlu bukti transfer manual.

    Saat QRIS online (Pakasir) aktif, opsi QRIS statis disembunyikan agar
    pelanggan tidak membayar ke dua kanal QRIS yang berbeda.
    """
    from core.pakasir import is_enabled
    if is_enabled():
        return [item for item in PAYMENT_METHODS if item[0] != 'qris']
    return list(PAYMENT_METHODS)


class PaymentProofForm(forms.Form):
    """Upload bukti transfer/QRIS oleh pelanggan."""
    payment_method = forms.TypedChoiceField(
        label=_('Metode pembayaran'),
        choices=[],
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['payment_method'].choices = manual_payment_methods()

    payment_proof = forms.ImageField(
        label=_('Bukti pembayaran'),
        help_text=_('Format JPG/PNG, maks. 5 MB. Screenshot m-banking atau foto struk/QRIS.'),
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
    )

    def clean_payment_proof(self):
        proof = self.cleaned_data['payment_proof']
        if proof.size > 5 * 1024 * 1024:
            raise forms.ValidationError(_('Ukuran berkas maksimal 5 MB.'))
        if proof.size == 0:
            raise forms.ValidationError(_('Berkas kosong tidak diterima.'))
        suffix = Path(proof.name or '').suffix.lower()
        allowed = getattr(settings, 'MEDIA_ALLOWED_EXTENSIONS',
                          ('.jpg', '.jpeg', '.png', '.webp'))
        if suffix not in allowed:
            raise forms.ValidationError(
                _('Format berkas harus JPG, PNG, atau WebP.'))
        # Verifikasi isi berkas (bukan hanya ekstensi/Content-Type kiriman
        # klien): pastikan benar-benar gambar & ukurannya wajar.
        try:
            from PIL import Image
            proof.seek(0)
            with Image.open(proof) as image:
                image.verify()
                fmt = (image.format or '').upper()
                width, height = image.size
            proof.seek(0)
        except Exception:
            raise forms.ValidationError(_('Berkas gambar tidak valid.'))
        if fmt not in {'JPEG', 'PNG', 'WEBP'}:
            raise forms.ValidationError(_('Format gambar tidak didukung.'))
        max_pixels = int(getattr(settings, 'IMAGE_MAX_PIXELS', 25_000_000))
        if width < 1 or height < 1 or width * height > max_pixels:
            raise forms.ValidationError(_('Dimensi gambar terlalu besar.'))
        return proof
