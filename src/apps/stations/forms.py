# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
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
    antenna_1 = forms.CharField(max_length=64,required=False)
    antenna_2 = forms.CharField(max_length=64, required=False)
    street_address = forms.CharField(max_length=75,required=False)
    city = forms.CharField(max_length=32,required=False)
    state = forms.CharField(max_length=15,required=False)
    postal_code = forms.CharField(max_length=15,required=False)
    phone_number = forms.CharField(max_length=20,required=False)
    
    offlineNotify = forms.BooleanField(label="Recieve email notifications if you station goes offline? (Emails sent daily)", required=False)
    
    class Meta:
        model = Station
        fields = ('nickname', 'grid', 'elevation', 'antenna_1', 'antenna_2', 'street_address', 'city', 'state', 'postal_code', 'phone_number', 'offlineNotify',)

class StationUserFilterForm(forms.Form):
    user = forms.CharField(
        required=False,
        label="Filter by user",
        widget=forms.TextInput(attrs={'placeholder': 'Filter by user'})
    )

# This is redundant with form in instruments area; may be possible to unify.

# Form used to register new instrument
#class InstrumentCreationForm(forms.ModelForm):
#    instrument = forms.CharField(max_length=40)
#    date_added = forms.DateTimeField(label="Date instrument added")
#    date_removed = forms.DateTimeField(label="Date instrument removed")
#    instrument_type = forms.ModelChoiceField(queryset=InstrumentType.objects.all())
# the above may need to be  widget=forms.Select, queryset=instr_type_set

#    nickname    = forms.CharField(max_length=40)
#    serial_no   = forms.CharField(max_length=60)
#    status      = forms.CharField(max_length=10)

 #   class Meta:
 #       model = Instrument
 #       fields = ('instrument', 'dateAdded', 'dateRemoved',  'nickname', 'serialNo' )

# need to add instrument type (via foreign key) to both Meta classes

# Form used to edit the data pertaining to a specific instrument
#class EditInstrumentForm(forms.ModelForm):
#    class Meta:
#        model =  Instrument
#        fields = ('instrument', 'dateAdded', 'dateRemoved', 'nickname', 'serialNo')

