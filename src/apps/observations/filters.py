# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
import django_filters

from .models import Observation
from apps.stations.models import Station
from apps.bands.models import Band
from apps.centerfrequencies.models import CenterFrequency
from apps.instruments.models import Instrument
from apps.instrumenttypes.models import InstrumentType
from django import forms

class ObservationForm(forms.Form):

    # Used to check for valid latitude and longitude inputs in observations filter
    def clean(self):
        # Obtain latitude and longitude values from user input
        # Because latitude and longitude are RangeFilters, they are stored as Python slice objects
        # This means the lower end of the range is latitude.start and the upper end is latitude.stop
        cleaned_data = super(ObservationForm, self).clean()
        latitude = self.cleaned_data.get("latitude")
        longitude = self.cleaned_data.get("longitude")

        # If user entered latitude, check for valid input
        if latitude != None:
            # The user did not provide both an upper and lower bound
            if latitude.start == None and latitude.stop != None or latitude.start != None and latitude.stop == None:
                self._errors['latitude'] = self._errors.get('latitude', [])
                self._errors['latitude'].append("Please enter values for both upper and lower bound.")
                
                # No need to check other cases
                return cleaned_data

            # One or both latitude values are outside of valid range
            if latitude.start < -90 or latitude.start > 90 or latitude.stop < -90 or latitude.stop > 90:
                self._errors['latitude'] = self._errors.get('latitude', [])
                self._errors['latitude'].append("Latitude must be between -90.0 and 90.0.")

            # Lower bound is greater than upper bound
            if latitude.start > latitude.stop:
                self._errors['latitude'] = self._errors.get('latitude', [])
                self._errors['latitude'].append("Invalid range.")

        # If user entered longitude, check for valid input
        if longitude != None:
            # The user did not provide both an upper and lower bound
            if longitude.start == None and longitude.stop != None or longitude.start != None and longitude.stop == None:
                self._errors['longitude'] = self._errors.get('longitude', [])
                self._errors['longitude'].append("Please enter values for both upper and lower bound.")

                # No need to check other cases
                return cleaned_data

            # One or both longitude values are outside of valid range
            if longitude.start < -180 or longitude.start > 180 or longitude.stop < -180 or longitude.stop > 180:
                self._errors['longitude'] = self._errors.get('longitude', [])
                self._errors['longitude'].append("Longitude must be between -180.0 and 180.0.")

            # Lower bound is greater than upper bound
            if longitude.start > longitude.stop:
                self._errors['longitude'] = self._errors.get('longitude', [])
                self._errors['longitude'].append("Invalid range.")


        return cleaned_data


class ObservationFilter(django_filters.FilterSet):
    # Select a single station to filter the query
    station = django_filters.ModelChoiceFilter(
         #   queryset=Station.objects.all(), 
         queryset=Station.objects.order_by("nickname"),
            label='Station Nickname',
            widget=forms.Select(
                attrs={'class': 'form-control'}
            )
    )

#    band = django_filters.filters.ModelMultipleChoiceFilter(
#            field_name='band__band',
#            to_field_name='band',
#            queryset=Band.objects.all(),
#            label='Band',
#    )

    # Select one or more instrument types to include in query
    instrument = django_filters.filters.ModelMultipleChoiceFilter(
            field_name='instrument__instrumenttype__instrumentType',
            to_field_name='instrumentType',
            queryset=InstrumentType.objects.all(),
            label='Instrument Type',
            widget=forms.SelectMultiple(
                attrs={'class': 'form-control'}
            )
    )
    
    # Select one or more center frequencies to include in query
    centerFrequency = django_filters.filters.ModelMultipleChoiceFilter(
            field_name='centerFrequency__centerFrequency',
            to_field_name='centerFrequency',
            queryset=CenterFrequency.objects.all(),
            label='Center Frequency',
            widget=forms.SelectMultiple(
                attrs={'class': 'form-control'}
            )
    )
    
    # Filter for observations beginning after the start date
    startDate__gte = django_filters.DateFilter(
            field_name='startDate',
            lookup_expr='date__gte',
            label='Start Date (UTC)',
            widget=forms.DateTimeInput(
                attrs={'type': 'date', 'class': 'form-control'}
            )
    )
    
    # Filter for observations ending before the end date
    endDate__lte = django_filters.DateFilter(
            field_name='endDate', 
            lookup_expr='date__lte',
            label='End Date (UTC)',
            widget=forms.DateTimeInput(
                attrs={'type': 'date', 'class': 'form-control'}
            )
    )

    # Filter for observations from stations located within a rectangle set by the user's desired coordinates
    # Latitude range filter
    latitude = django_filters.filters.RangeFilter(
            field_name='station__latitude',
            label='Latitude Range:',
            widget=django_filters.widgets.RangeWidget(
                attrs={'class': 'form-control', 'size': 6, 'placeholder': '[-90, 90]'}
            )
    )

    # Longitude range filter
    longitude = django_filters.filters.RangeFilter(
            field_name='station__longitude',
            label='Longitude Range:',
            widget=django_filters.widgets.RangeWidget(
                attrs={'class': 'form-control', 'size': 6, 'placeholder': '[-180, 180]'}
            )
    )

    class Meta:
        model = Observation
        fields = ['instrument', 'centerFrequency', 'station']
        form = ObservationForm
