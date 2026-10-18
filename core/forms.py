"""Form bukti pembayaran bersama (dipakai modul booking & rental)."""
from django import forms
from django.utils.translation import gettext_lazy as _

from core.settings import PAYMENT_METHODS


class PaymentProofForm(forms.Form):
    """Upload bukti transfer/QRIS oleh pelanggan."""
    payment_method = forms.TypedChoiceField(
        label=_('Metode pembayaran'),
        choices=PAYMENT_METHODS,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'}),
    )
    payment_proof = forms.ImageField(
        label=_('Bukti pembayaran'),
        help_text=_('Format JPG/PNG, maks. 5 MB. Screenshot m-banking atau foto struk/QRIS.'),
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
    )

    def clean_payment_proof(self):
        proof = self.cleaned_data['payment_proof']
        if proof.size > 5 * 1024 * 1024:
            raise forms.ValidationError(_('Ukuran berkas maksimal 5 MB.'))
        return proof
