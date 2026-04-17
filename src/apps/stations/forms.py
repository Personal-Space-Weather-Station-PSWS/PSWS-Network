# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
import re
import base64

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from apps.stations.models import Station
from apps.instruments.models import Instrument
from apps.instrumenttypes.models import InstrumentType

instr_type_set = InstrumentType.objects.all()


# Form used to register new stations
class StationCreationForm(forms.ModelForm):
    nickname = forms.CharField(max_length=30)
    grid = forms.CharField(label='Maidenhead Grid Square', max_length=6, widget=forms.TextInput(attrs={'placeholder': 'Ex: AA11aa'}))
    elevation = forms.FloatField(required=False, help_text='meters above sea level')
    antenna_1 = forms.CharField(max_length=64, required=False)
    antenna_2 = forms.CharField(max_length=64, required=False)
    street_address = forms.CharField(max_length=75, required=False)
    city = forms.CharField(max_length=32, required=False)
    state = forms.CharField(max_length=15, required=False)
    postal_code = forms.CharField(max_length=15, required=False)
    phone_number = forms.CharField(max_length=20, required=False)

    class Meta:
        model = Station
        fields = ('nickname', 'grid', 'elevation', 'antenna_1', 'antenna_2', 'street_address', 'city', 'state', 'postal_code', 'phone_number')


# Form used to edit the data pertaining to a specific station
class EditStationForm(forms.ModelForm):
    nickname = forms.CharField(max_length=30)
    grid = forms.CharField(label='Maidenhead Grid Square', max_length=6, widget=forms.TextInput(attrs={'placeholder': 'Ex: AA11aa'}))
    elevation = forms.FloatField(required=False, help_text='meters above sea level')
    antenna_1 = forms.CharField(max_length=64, required=False)
    antenna_2 = forms.CharField(max_length=64, required=False)
    street_address = forms.CharField(max_length=75, required=False)
    city = forms.CharField(max_length=32, required=False)
    state = forms.CharField(max_length=15, required=False)
    postal_code = forms.CharField(max_length=15, required=False)
    phone_number = forms.CharField(max_length=20, required=False)

    offlineNotify = forms.BooleanField(
        label="Recieve email notifications if your station goes offline? (Emails sent daily)",
        required=False
    )

    ssh_public_key = forms.CharField(
        label="SSH Public Key",
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Paste your SSH public key here (ssh-rsa, ssh-ed25519, ecdsa-sha2-nistp256)'
        }),
        help_text="Your public key only — never paste your private key."
    )

    ALLOWED_KEY_TYPES = {
        'ssh-rsa',
        'ssh-ed25519',
        'ecdsa-sha2-nistp256',
        'ecdsa-sha2-nistp384',
        'ecdsa-sha2-nistp521',
        'sk-ssh-ed25519@openssh.com',
        'sk-ecdsa-sha2-nistp256@openssh.com',
    }

    def clean_ssh_public_key(self):
        key = self.cleaned_data.get('ssh_public_key', '').strip()

        if not key:
            return key

        lines = [l for l in key.splitlines() if not l.startswith('#')]
        key = ' '.join(lines).strip()

        parts = key.split()
        if len(parts) < 2:
            raise forms.ValidationError("Invalid SSH public key format.")

        key_type, key_data = parts[0], parts[1]

        if key_type not in self.ALLOWED_KEY_TYPES:
            raise forms.ValidationError(
                f"Unsupported key type '{key_type}'. "
                f"Allowed types: {', '.join(sorted(self.ALLOWED_KEY_TYPES))}"
            )

        if not re.fullmatch(r'[A-Za-z0-9+/=]+', key_data):
            raise forms.ValidationError("SSH key data contains invalid characters.")

        try:
            decoded = base64.b64decode(key_data)
        except Exception:
            raise forms.ValidationError("SSH key data is not valid base64.")

        if len(decoded) < 32 or len(decoded) > 4096:
            raise forms.ValidationError("SSH key data length is outside expected bounds.")

        return f"{key_type} {key_data}"

    class Meta:
        model = Station
        fields = (
            'nickname', 'grid', 'elevation', 'antenna_1', 'antenna_2',
            'street_address', 'city', 'state', 'postal_code', 'phone_number',
            'offlineNotify',
        )


class StationUserFilterForm(forms.Form):
    user = forms.CharField(
        required=False,
        label="Filter by user",
        widget=forms.TextInput(attrs={'placeholder': 'Filter by user'})
    )


# This is redundant with form in instruments area; may be possible to unify.

#class InstrumentCreationForm(forms.ModelForm):
#    instrument = forms.CharField(max_length=40)
#    date_added = forms.DateTimeField(label="Date instrument added")
#    date_removed = forms.DateTimeField(label="Date instrument removed")
#    instrument_type = forms.ModelChoiceField(queryset=InstrumentType.objects.all())
#    nickname    = forms.CharField(max_length=40)
#    serial_no   = forms.CharField(max_length=60)
#    status      = forms.CharField(max_length=10)
#    class Meta:
#        model = Instrument
#        fields = ('instrument', 'dateAdded', 'dateRemoved',  'nickname', 'serialNo' )

#class EditInstrumentForm(forms.ModelForm):
#    class Meta:
#        model =  Instrument
#        fields = ('instrument', 'dateAdded', 'dateRemoved', 'nickname', 'serialNo')
