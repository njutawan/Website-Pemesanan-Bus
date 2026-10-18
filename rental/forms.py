"""Form pemesanan sewa mobil."""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from rental.models import Vehicle


class RentalForm(forms.Form):
    """Data sewa + kontak penyewa (total dihitung server-side)."""
    pickup_date = forms.DateField(
        label=_('Tanggal ambil'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    return_date = forms.DateField(
        label=_('Tanggal kembali'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    pickup_location = forms.CharField(
        label=_('Lokasi ambil'),
        max_length=200,
        help_text=_('Mis. "Bandara Juanda Surabaya" atau alamat hotel.'),
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    with_driver = forms.BooleanField(
        label=_('Sertakan sopir (+biaya/hari)'),
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))
    contact_name = forms.CharField(
        label=_('Nama lengkap'), max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control'}))
    contact_phone = forms.CharField(
        label=_('No. WhatsApp'), max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '08xxxxxxxxxx'}))
    contact_email = forms.EmailField(
        label=_('Email'), required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}))

    def clean_pickup_date(self):
        pickup = self.cleaned_data['pickup_date']
        if pickup < timezone.localdate():
            raise ValidationError(_('Tanggal ambil tidak boleh di masa lalu.'))
        return pickup

    def clean(self):
        cleaned = super().clean()
        pickup = cleaned.get('pickup_date')
        ret = cleaned.get('return_date')
        if pickup and ret:
            days = (ret - pickup).days + 1  # inklusif: ambil & kembali dihitung 1 hari
            if days < 1:
                raise ValidationError(
                    _('Tanggal kembali harus sama dengan atau setelah tanggal ambil.'))
            if days > 30:
                raise ValidationError(_('Maksimal sewa 30 hari. Untuk lebih, hubungi kami.'))
            cleaned['days'] = days
        return cleaned
