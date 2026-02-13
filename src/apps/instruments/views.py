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
from apps.instruments.models import Instrument
from apps.instruments.forms import InstrumentCreationForm
from apps.instrumenttypes.models import InstrumentType
from apps.stations.models import Station
from apps.observations.models import Observation
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django_tables2 import SingleTableView

from .tables import InstrumentTable, FilteredInstrumentsTable
from .forms import EditInstrumentForm

import os
import configparser
import mimetypes
import logging
logger = logging.getLogger(__name__)

from django.http import HttpResponse

# Create your views here.

@method_decorator(login_required, name='dispatch')
# Display a list of the current station's instruments
def MyInstrumentsListView(SingleTableView):
    #To filter the queryset by user, must use a method to access the request object
    def get_queryset(self):
        return Instrument.objects.filter(_id=3)
    queryset =  Instrument.objects.filter(id=3)
    table_class = FilteredInstrumentsTable
    table = Instrument.objects.filter(id=3)
    template_name = 'my_instruments_list.html'
    return render(request, 'my_instruments_list.html', table)

#@method_decorator(login_required, name='dispatch')
@login_required
# Display the list of all instruments

def InstrumentListView(request):
    def get_queryset(self):
        return Instrument.objects.filter(id=3)
    table_class = FilteredInstrumentsTable
    table = Instrument.objects.filter(id=3)

    queryset = Instrument.objects.filter(id=3)
    template_name = 'instruments.html'
    return render(request, 'instruments.html', table)

@login_required
def instrument_details_view(request, id=id):
    instrument = get_object_or_404(Instrument, id=id)
    queryset = InstrumentType.objects.filter(id=instrument.instrumenttype_id)
     
    instrument_type_text = queryset[0].instrumentType
    return render(request, 'instrument_details.html', 
        {'instrument' : instrument, 'instrumentType': instrument_type_text,
         })

@login_required
# Allow user to add a new instrument
def add_instrument_view(request, id=id):
    if request.method == "POST":
        form = InstrumentCreationForm(request.POST)
        if form.is_valid():
            instrument = form.save(commit=False)
            iid = int(id) # ensure the db update does not receive python function
            instrument.station_id = iid
            instrument.instrument = form.cleaned_data.get('instrument')
            instrument.dateAdded  = form.cleaned_data.get('dateAdded')
            instrument.nickname   = form.cleaned_data.get('nickname')
            instrument.serialNo   = form.cleaned_data.get('serialNo')
            instrument.status     = form.cleaned_data.get('status') 
            instrument.instrumenttype = form.cleaned_data.get('instrumenttype')
            instrument.save()

            station= get_object_or_404(Station, id=iid)
            context = ('station', station)
            table = InstrumentTable(Instrument.objects.filter(station_id=iid))
            return render(request, 'station_details.html',
                {'station': station, 'table': table })


    else:
        form = InstrumentCreationForm()
    return render(request, 'add_instrument.html', {'form': form})

@login_required
# Allow user to edit data of specific instrument
def update_instrument_view(request, id=id):
    instrument = get_object_or_404(Instrument, id=id)
    if request.method == 'POST':
        form  = EditInstrumentForm(request.POST, request.FILES, instance=instrument)

        if request.POST.get("del-button"):
            station = get_object_or_404(Station, id = instrument.station_id)
            instrument.delete()
            return redirect('station_details', station.id)

        if form.is_valid(): 
            instrument.instrument  = form.cleaned_data.get('instrument')
            instrument.dateAdded   = form.cleaned_data.get('dateAdded')
            instrument.dateRemoved = form.cleaned_data.get('dateRemoved')
            instrument.nickname    = form.cleaned_data.get('nickname')
            instrument.serialNo    = form.cleaned_data.get('serialNo')
            instrument.status      = form.cleaned_data.get('status')
            instrument.instrumenttype = form.cleaned_data.get('instrumenttype')
            instrument.save()
            messages.success(request, 'Your instrument has been updated.')
            return redirect('instrument_details', instrument.id)
        else:
            form = EditInstrumentForm(instance=instrument)
            messages.error(request, 'Issue updating data.')
            return render(request, 'instrument_update.html', {'form': form, 'instrument':instrument})
    else: # display form for updating / deleting instrumen
        form = EditInstrumentForm(instance=instrument)
        obsQS = Observation.objects.filter(instrument_id=instrument.id)
        if obsQS.count() > 0:   # if this instrument has observations associated with it, warn th user.
            messages.warning(request, "(!) THERE ARE ONE OR MORE OBSERVATIONS UNDER THIS INSTRUMENT. Deleting instrument will delete observation(s).")
        return render(request, 'instrument_update.html', {'form':form, 'instrument': instrument})

@login_required
def download_config(request, id=id):
    """ Downloads uploader.config file to local computer using website
    Parameter
    ---------
    id : int
        provides id for the instrument object from which to pull 
        and download config file
    Returns
    -------
    response : HTTPResponse
        begins download of target config file to local computer
        upon request
    """
    instrument = get_object_or_404(Instrument, id=id)
    station = get_object_or_404(Station, id = instrument.station_id)
    
    config= configparser.ConfigParser()
    
    config["profile"]={}
    config["profile"]["token_value"]= station.station_pass
    config["profile"]["grid"]= station.grid
    config["profile"]["prefix"]= str(station.user).upper()
    config["profile"]["thestationid"]= station.station_id
    config["profile"]["central_host"]= "pswsnetwork.caps.ua.edu"
    config["spectrum_settings"]={}
    config["spectrum_settings"]["obs"] = '""'
    config["spectrum_settings"]["band"] = "[band you are running in MHz: 2.5, 5.0, 10.0, 15.0, 20.0, or 25.0]"
    config["spectrum_settings"]["instrumentid"] = str(id)
    config["spectrum_settings"]["throttle"] = "200K"
    config["spectrum_settings"]["spectrum_storage"] = "/home/pi/PSWS/Sxfer"
    
    config_path= "/tmp/"+ "uploader_"+str(id)+".config"
    config_file= open(config_path, 'w')
    config.write(config_file)
    config_file.close()
    config_file= open(config_path, 'r')
    mime_type= mimetypes.guess_type(config_path) # + "uploader.config")
    os.remove(config_path)
    # creates and returns site response triggering img file download
    response= HttpResponse(config_file, content_type=mime_type)
    response['Content-Disposition'] = "attachment; filename= uploader.config"
    return response
