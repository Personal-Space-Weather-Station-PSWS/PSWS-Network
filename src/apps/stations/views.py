# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic.edit import UpdateView
from datetime import datetime
from stations.models import Station
from stations.forms import StationCreationForm
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django_tables2 import SingleTableView
from django.conf import settings

import maidenhead as mh
from .tables import StationTable, FilteredStationTable, StationUserTable, StationInstrumentTable
from .forms import EditStationForm
from .tokens import station_activation_token
from .forms import StationUserFilterForm

from instruments.models import Instrument
from instruments.tables import InstrumentTable
from observations.models import Observation

import os, sys
import logging
logger = logging.getLogger(__name__)

from django.http import HttpResponse


@method_decorator(login_required, name='dispatch')
# Display a list of the currently logged in user's stations
class MyStationsListView(SingleTableView):
    #To filter the queryset by user, must use a method to access the request object
    def get_queryset(self):
        return Station.objects.filter(user=self.request.user)

    table_class = FilteredStationTable
    template_name = 'my_stations_list.html'
    paginate_by = 4




# Display the list of all registered stations
class StationListView(SingleTableView):
    template_name = 'stations.html'
    paginate_by = 4
    def get_table_class(self):
        if(self.request.user.is_superuser):    
            if self.request.GET.get('swap') == '1':
                return StationUserTable
        return StationTable 

    def get_queryset(self):
        qs = Station.objects.all()
        if self.request.user.is_superuser and self.request.GET.get('swap') == '1':
            usename = self.request.GET.get('user', "").strip()
            if usename:
                qs = qs.filter(user__username__istartswith=usename)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['swap'] = self.request.GET.get('swap') == '1'
        context['filter_form'] = StationUserFilterForm(self.request.GET)
        return context

@login_required
def station_instrument_view(request, id):
    if not request.user.is_superuser:
        return redirect('stations')
    instruments = (
        Instrument.objects
        .filter(station__user__id=id)  # only instruments for stations owned by this user
        .select_related("station", "instrumenttype", "station__user")
    )

    table = StationInstrumentTable(instruments)
    table.paginate(page=request.GET.get("page", 1), per_page=10)

    return render(request, "station_instruments.html", {
        "table": table,
    })

@login_required
# Display more detailed information about a station
def station_details_view(request, id=None):
    station = get_object_or_404(Station, id=id, user=request.user)

    context = {'station': station}
    table = InstrumentTable(Instrument.objects.filter(station_id=id))
    table.paginate(page=request.GET.get("page", 1), per_page=8)
    return render(request, 'station_details.html', 
        {'station': station, 'table': table}
            )

@login_required
# Allow a user to register a new station
def add_station_view(request):
    if request.method == "POST":
        form = StationCreationForm(request.POST)
        if form.is_valid():
            station = form.save(commit=False)
            station.user_id = request.user.id
            
            # Determine new station's ID number
            try:
                new_id_number = Station.objects.latest('create_date').id + 1
            except ObjectDoesNotExist:
                new_id_number = 1
            
            station.station_id = 'S' + str(new_id_number).zfill(6)
            station.station_pass = station_activation_token.make_token(request.user)
            station.station_pass = station.station_pass.replace('-', station.station_pass[0])[4:36]
            station.nickname = form.cleaned_data.get('nickname')
            station.grid = form.cleaned_data.get('grid')
            try:
                station.latitude =  mh.to_location(station.grid, center=True)[0]
                station.longitude = mh.to_location(station.grid, center=True)[1]
            except Exception as e:
                text = "You entered an invalid grid square value. For help with this see <a href='https://www.levinecentral.com/ham/grid_square.php'>here.</a>"
                return HttpResponse(text)
            station.elevation = form.cleaned_data.get('elevation')
            station.antenna_1 = form.cleaned_data.get('antenna_1')
            station.antenna_2 = form.cleaned_data.get('antenna_2')
            station.street_address = form.cleaned_data.get('street_address')
            station.city = form.cleaned_data.get('city')
            station.state = form.cleaned_data.get('state')
            station.postal_code = form.cleaned_data.get('postal_code')
            station.phone_number = form.cleaned_data.get('phone_number')
            station.create_date = datetime.now()
            station.save()
            os.system('sudo ' + str(settings.BASE_DIR) + '/scripts/ingest/stationcreation4.sh ' + station.station_id + ' ' + station.station_pass)
            return redirect('stations')
    else:
        form = StationCreationForm()

    return render(request, 'add_station.html', {'form': form})

@login_required
# Allow a user to edit the data of a specific station
def update_station_view(request, id=None):
    station = get_object_or_404(Station, id=id, user=request.user)

    if request.method == 'POST':
        form = EditStationForm(request.POST, request.FILES, instance=station)

        if request.POST.get("del-button"):
          instrQS = Instrument.objects.filter(station_id=station.id)
          if instrQS.count() > 0:   # this station has instrument(s), deny the deletion
            messages.error(request, "(!) YOU CAN ONLY DELETE THIS STATION AFTER DELETING ITS INSTRUMENT(S).")
            return render(request, 'station_update.html', {'form': form, 'station': station})
          station.delete()
          return redirect('my_stations_list')

        if request.POST.get("del-button"):
            instrQS = Instrument.objects.filter(station_id=station.id)
            if instrQS.count() > 0:   # this station has instrument(s), deny the deletion
                messages.error(request, "(!) YOU CAN ONLY DELETE THIS STATION AFTER DELETING ITS INSTRUMENT(S).")
                return render(request, 'station_update.html', {'form': form, 'station': station})
            station.delete()
            return redirect('my_stations_list')

        if form.is_valid():
            station.nickname = form.cleaned_data.get('nickname')
            station.grid = form.cleaned_data.get('grid')
            station.latitude = mh.to_location(station.grid,center=True)[0]
            station.longitude = mh.to_location(station.grid,center=True)[1]
            station.elevation = form.cleaned_data.get('elevation')
            station.antenna_1 = form.cleaned_data.get('antenna_1')
            station.antenna_2 = form.cleaned_data.get('antenna_2')
            station.street_address = form.cleaned_data.get('street_address')
            station.city = form.cleaned_data.get('city')
            station.state = form.cleaned_data.get('state')
            station.postal_code = form.cleaned_data.get('postal_code')
            station.phone_number = form.cleaned_data.get('phone_number')
            station.save()
            messages.success(request, 'Your station has been updated!')
            return render(request, 'station_update.html', {'form': form, 'station': station})
        else:
            form = EditStationForm(instance=station)
            messages.error(request, 'Issue updating information.')
            return render(request, 'station_update.html', {'form': form, 'station': station})
    else:
        form = EditStationForm(instance=station)
        instrQS = Instrument.objects.filter(station_id=station.id)
        if instrQS.count() > 0:  # if this station has instrument(s) issue warning
            messages.warning(request, "(!) ONE OR MORE INSTRUMENT(S) UNDER THIS STATION. You must delete them before deleting station.")

        return render(request, 'station_update.html', {'form': form, 'station': station})

@login_required
# Allow user to add a new instrument
def add_instrument_view(request, id=id):
    if request.method == "POST":
        form = InstrumentCreationForm(request.POST)
        if form.is_valid():
            instrument = form.save(commit=False)
            instrument.station_id = id

            instrument.instrument = form.cleaned_data.get('instrument')
            instrument.dateAdded  = form.cleaned_data.get('date_added')
            instrument.nickname   = form.cleaned_data.get('nickname')
            instrument.serialNo   = form.cleaned_data.get('serial_no')
            instrument.status     = form.cleaned_data.get('status')

            instrument.save()
            return redirect('instruments')
    else:
        form = InstrumentCreationForm()

    return render(request, 'add_instrument.html', {'form': form})
