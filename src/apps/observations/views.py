# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
#Authors:   Nicholas Muscolino, Anderson Liddle, Cole Robbins
# University of Alabama, Apr-May 2022 with funding from  NSF Grant 80NSSC21K1772
# Modified by W. Engelke, July 2022 

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django_tables2 import SingleTableView, SingleTableMixin
from django_filters.views import FilterView
from django.http import HttpResponse, HttpResponseRedirect
from django.contrib import messages
from django.core.files.temp import NamedTemporaryFile
from django.conf import settings

from .models import Observation
from .models import Instrument
from .tables import ObservationTable
from .filters import ObservationFilter
from .forms import DateTimeForm

import shutil
import os
import mimetypes
import zipfile

import digital_rf as drf
import h5py
from datetime import datetime

def download_plot(request, id=None):
    """ Downloads observation plot to local computer using website
    Parameter
    ---------
    id : int
        provides id for the observation object from which to pull 
        and download plot file
    Returns
    -------
    response : HTTPResponse
        begins download of target plot img file to local computer
        upon request
    """

    # retreives observation by provied id or throws 404 error to site
    observation= get_object_or_404(Observation, id=id)
    
    # determines path to retrieve plot img from as well as file type
    file_path= observation.plotPath + '/' + observation.plotFile
    img_file= open(file_path, 'rb')
    mime_type= mimetypes.guess_type(file_path)
    
    # creates and returns site response triggering img file download
    response= HttpResponse(img_file, content_type=mime_type)
    response['Content-Disposition'] = "attachment; filename=%s" % observation.plotFile
    return response

def download_file(request, id=None):
    observation = get_object_or_404(Observation, id=id)
   
    fl_path = observation.path
    filename = observation.fileName
    #NJIT Fix 

    # for magnetometer data, this opens file; for DRF data, it takes the exception
    fl_path = fl_path + '/' + filename
    
    fl_path = fl_path.replace(":", "_")

    try:  # does the requested tar file exist?
        fl = open(fl_path, 'rb')
        os.remove(fl_path)
    except IOError:  # file is not there, see if this is request for download of  DRF dataset
        obs = get_object_or_404(Observation, id=id)
        fl_path =  obs.fileName
        file_extension  = os.path.splitext(fl_path)[1]
        # here we skip doing the tar if the file is already in zip format
        # In version 1, this is magnetometer
        if file_extension == ".zip":
            fl_path = observation.path + "/" +observation.fileName # correct this
            fl = open(fl_path, 'rb')
            mime_type, _ = mimetypes.guess_type(fl_path)
            response = HttpResponse(fl, content_type=mime_type)
            response['Content-Disposition'] = "attachment; filename=%s" % observation.fileName
            return response
        
        total_path = obs.path
        zip_path = "/psws/temp/ziptemp/" + total_path.rsplit('/')[2] +   \
                   "/temp/" + total_path.rsplit('/')[3]
        print("tar file to: " + zip_path)

        shutil.make_archive(zip_path, 'zip', total_path)
        command = "chmod 777 " + zip_path + ".zip"  # this is to allow leter cleanup
        os.system(command)  
        #fl = open(zip_path + '.zip', 'rb')

        # The following replaces the original tar/gzip code as it produces a
        # zip file without the internal directory structure
        fl = open(zip_path + '.zip', 'rb')
        os.remove(zip_path)
        mime_type, _ = mimetypes.guess_type(zip_path+'.zip')
        response = HttpResponse(fl, content_type=mime_type)
        response['Content-Disposition'] = "attachment; filename=%s" % fl_path+'.zip'

        return response 

    mime_type, _ = mimetypes.guess_type(fl_path)
    # potentially need to change content_type="application/x-tar"
    response = HttpResponse(fl, content_type=mime_type)
    # response = HttpResponse(fl, content_type="application/x-tar")
    response['Content-Disposition'] = "attachment; filename=%s" % filename
    return response

def download_range(request, id=None):
    observation = get_object_or_404(Observation, id=id)

    #start = str(request.POST.get('start_date'))
    #end = str(request.POST.get('end_date'))

    #if start == '' or end == '':
    #    messages.error(request, "Error: Blank fields")
    #    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

    #start = start[:10]
    #end = end[:10]
    
    # TODO: Add try catch here to replace blank if statement above
    #start_converted = datetime.strptime(start, '%Y-%m-%d').date()
    #end_converted = datetime.strptime(end, '%Y-%m-%d').date()

    # if (end < start):
        #messages.error(request, "Error: End date before start date")
        #return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
 
    #if (end_converted - start_converted).days > 7:
        #messages.error(request, "You've selected " + str((end_converted - start_converted).days) + " days. Please limit to at most 7 days")
        #return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/')) 

    #print(start)
    #print(end)

    fl_path = observation.path
    filename = observation.fileName
    full_path = fl_path # + filename

    instrument = get_object_or_404(Instrument, id=observation.instrument.id)
    print(instrument.instrumenttype)
    print(instrument.id)
    
    if instrument.instrumenttype_id == 3 or instrument.instrumenttype_id == 6:
        full_path = fl_path + "/" + filename
        fl = open(full_path, "rb")
        mime_type, _ = mimetypes.guess_type(fl_path)
        response = HttpResponse(fl, content_type=mime_type)
        response['Content-Disposition'] = "attachment; filename=%s" % filename
        return response

    #zip_path = "/home/ziptemp/" + fl_path.rsplit('/')[2] + \
    #        "/temp/" + filename[:3] + start + "-" + end

    zip_name = "Range-" + filename
    zip_path = "/psws/temp/ziptemp/" + zip_name
    print(zip_path)

    shutil.make_archive(zip_path, 'zip', full_path)
    command = "chmod 777 " + zip_path + ".zip"  # this is to allow leter cleanup
    os.system(command)
    #fl = open(zip_path + '.zip', 'rb')

    # The following replaces the original tar/gzip code as it produces a
    # zip file without the internal directory structure
    fl = open(zip_path + ".zip", 'rb')
    os.remove(zip_path + ".zip")
    mime_type, _ = mimetypes.guess_type(zip_path+'.zip')
    response = HttpResponse(fl, content_type=mime_type)
    response['Content-Disposition'] = "attachment; filename=%s" % filename+'.zip'

    return response


    """
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipF:

        #zipF.write(full_path + "/ch0/drf_properties.h5", \
         #        arcname = "ch0/drf_properties.h5")

        #zipF.write(full_path + "/ch0/metadata/dmd_properties.h5", \
         #        arcname = "ch0/metadata/dmd_properties.h5")

        for file in os.listdir(full_path + '/ch0'):

            if '-' not in file: continue

            file_name = str(file[0:10])
            for sub_file in os.listdir(full_path + '/ch0/' + file):
                zipF.write(full_path + "/ch0/" + file + "/" + sub_file,\
                        arcname = "ch0/" + file + "/" + sub_file)

        for file in os.listdir(full_path + '/ch0/metadata'):
            file_name = str(file[0:10])
            if os.path.isdir(full_path + '/ch0/metadata/' + file): continue
            for sub_file in os.listdir(full_path + '/ch0/metadata/' + file):
                zipF.write(full_path + "/ch0/metadata/" + file + "/" + sub_file, \
                        arcname = "ch0/metadata/" + file + "/" + sub_file) 
        zipF.close()        

        fl = open(zip_path, 'rb')
        
        os.remove(zip_path)
    
        mime_type, _ = mimetypes.guess_type(zip_path)
        response = HttpResponse(fl, content_type=mime_type)
        response['Content-Disposition'] = "attachment; filename=%s" % zip_name

        return response
"""

def get_date_range(request, id=None): 
    observation = get_object_or_404(Observation, id=id) 
   
    fl_path = observation.path
    filename = observation.fileName
     
    drf_data = drf.DigitalRFReader(fl_path + filename)
    start, end = drf_data.get_bounds('ch0')
    startDate = datetime.fromtimestamp(start / 10)
    endDate = datetime.fromtimestamp(end / 10)
    print(str(startDate) + " " + str(endDate))

    start = datetime.fromtimestamp(start / 10)
    start_string = start.strftime("%Y-%m-%d")
    end = datetime.fromtimestamp(end / 10)
    end_string = end.strftime("%Y-%m-%d")

    print(start_string)
    print(end_string)
   
    
     
    return redirect("/observations/observation_list/")

def select_download_range(request, id=None):
    observation = get_object_or_404(Observation, id=id)

    # Intermediary variables meant to get the ID of datatype from the stinkin' intersection table b/w observations and datatypes
    # For now, accessing only the first query, as we only have observations with one datatype
    # In the future, will need to convert this to handle multiple datatypes
    datatype_list       = observation.dataType.all()
    centerfreq_list     = observation.centerFrequency.all()
    if datatype_list:
        datatype        = datatype_list[0]
    else:
        datatype        = None
    if centerfreq_list:
        centerfreq      = centerfreq_list[0]
    else:
        centerfreq      = None

    form_class  = DateTimeForm
    return render(request, 'select_download_range.html', {'observation': observation, 'datatype': datatype, 'centerfreq': centerfreq, 'form': form_class})

# Display a list of all observations in the database
#class ObservationListView(SingleTableView):
#    table_class = ObservationTable
#    queryset = Observation.objects.all()
#    template_name = "observation_list.html"

#@method_decorator(login_required, name='dispatch')
# Display a list of all observations in the database
class ObservationListView(SingleTableMixin, FilterView):
    mapbox_access_token = settings.MAPBOX_ACCESS_TOKEN
    table_class = ObservationTable
    model = Observation
    template_name = "observation_list.html"
    filterset_class = ObservationFilter
    paginate_by = 8
    ordering = ['-endDate', 'id'] # list newest observations first
