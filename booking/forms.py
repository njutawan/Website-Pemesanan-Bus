"""Form alur pemesanan tiket: pencarian jadwal & data pemesan."""
from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from booking.models import City
from core.settings import MAX_SEATS_PER_BOOKING


class SearchForm(forms.Form):
    """Form pencarian jadwal bus (GET dari beranda / halaman bus)."""
    origin = forms.ModelChoiceField(
        label=_('Kota asal'), queryset=City.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}), empty_label=_('Pilih kota asal'))
    destination = forms.ModelChoiceField(
        label=_('Kota tujuan'), queryset=City.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'}), empty_label=_('Pilih kota tujuan'))
    date = forms.DateField(
        label=_('Tanggal perjalanan'),
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}))
    passengers = forms.IntegerField(
        label=_('Penumpang'),
        min_value=1, max_value=MAX_SEATS_PER_BOOKING, initial=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}))

    def clean_date(self):
        date = self.cleaned_data['date']
        if date < timezone.localdate():
            raise ValidationError(_('Tanggal perjalanan tidak boleh di masa lalu.'))
        return date

    def clean(self):
        cleaned = super().clean()
        origin = cleaned.get('origin')
        destination = cleaned.get('destination')
        if origin and destination and origin == destination:
            raise ValidationError(_('Kota asal dan tujuan tidak boleh sama.'))
        return cleaned


class PassengerForm(forms.Form):
    """Data kontak pemesan sebelum booking dibuat."""
    contact_name = forms.CharField(
        label=_('Nama lengkap'), max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Nama sesuai KTP/KTM')}))
    contact_phone = forms.CharField(
        label=_('No. WhatsApp'), max_length=20,
        help_text=_('Digunakan untuk konfirmasi & e-tiket.'),
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '08xxxxxxxxxx'}))
    contact_email = forms.EmailField(
        label=_('Email'), required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'nama@email.com'}))
    agree = forms.BooleanField(
        label=_('Saya menyetujui syarat & ketentuan pemesanan.'),
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    def clean_contact_phone(self):
        import re
        phone = re.sub(r'[\s\-]', '', self.cleaned_data['contact_phone'])
        if not re.fullmatch(r'\+?\d{9,16}', phone):
            raise ValidationError(_('Nomor telepon tidak valid. Contoh: 081234567890'))
        return phone
