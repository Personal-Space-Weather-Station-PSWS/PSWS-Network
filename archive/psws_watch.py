# Modifications by WDE, May 2022
import sys
import tarfile
import re
import subprocess
import time, pytz
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import h5py
import digital_rf as drf
from datetime import datetime
import numpy as np

from sqlalchemy import create_engine

import os
#  admin to use Djago ORM for db updating
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'PSWS.PSWS.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
from django.db import models
django.setup()
from centerfrequencies.models import *
from observations.models import *

from urllib.parse import quote_plus

#connect the database
engine = "[readacted]"

def get_size(start_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size

class UploadEvent(PatternMatchingEventHandler):
    def __init__(self, patterns=None):
        super(UploadEvent, self).__init__(patterns=patterns)

    def on_created(self, event):
        #Begin by identifying if continuous or not
        #Then locating the path of the event
        print("triggered on_created")
        if event.src_path.rsplit('/')[3][0] == 'd':
            print("D!")
            path = event.src_path
            channelPath = event.src_path + "/ch0"
            uploadType = 'd'
        elif event.src_path.rsplit('/')[3][0] == 'c':
            print("C! path=" + event.src_path)
#            path = "/" + event.src_path.rsplit('/')[1] + "/" + event.src_path.rsplit('/')[2] \
#                   + "/" + event.src_path.rsplit('/')[3]
#            channelPath = path + "/ch0"
#            print("computed channel path=" + channelPath)
            observation_no = event.src_path.rsplit('/')[3][1:20]
            path = "/" + event.src_path.rsplit('/')[1] + "/" +  event.src_path.rsplit('/')[2] \
                    +  "/uploads/" + observation_no
            obsSize = get_size(path)
            print("Data size=", obsSize)
            channelPath = path + "/ch0"
            print("channel path=" + channelPath)
            uploadType = 'c'
            metadata_dir = channelPath + "/metadata"
            start_idx = 0
            try:
              dmr = drf.DigitalMetadataReader(metadata_dir)
              start_idx = dmr.get_bounds()[0]

    #          print("Start:" , start_idx)
            except IOError:
              print("IO error accessing digital metadata")
              raise

            fields = dmr.get_fields()
     #       print("Available fields are <%s>" % (str(fields)))

            freq_list = []
            data_dict = dmr.read(start_idx, start_idx + 2, "center_frequencies")
   #         print("Center freq list:")
            for x in list(data_dict)[0:1]:
  #             print("key{}, val{}:".format(x, data_dict[x]))
               freq_list = data_dict[x] 
#            print("metadata contains ",len(freq_list)," frequencies")
           # for key in data_dict.keys(): # build this list in case user collects multiple frequencies
           #  print((key, data_dict[key]))
           #  freq_list.append(data_dict[key][0]) # note: possible bug here; may need to iterate thru key
            #freq_list.append(15.0)   # temporary test
#            print("freq_list:", freq_list)
            # here we handle the case where user is collecting at multiple frequencies
            cfid_list = []   # list of frequency IDs
            for this_freq in freq_list:
 #              print("metadata freq :",this_freq)
               this_cfid = CenterFrequency.objects.filter(centerFrequency=this_freq).values('id')
               cfid_list.append(this_cfid)
           # cfid = CenterFrequency.objects.filter(centerFrequency=freq_list[0]).values('id')
 #           print("cfid list",cfid_list)
# The following reads of digital metadata to get lat & long work, but are not yet
# being used for anything. They may be added to the database (observation table) in future.
#            data_dict = dmr.read(start_idx, start_idx + 2, "lat")
#            for key in data_dict.keys():
#             print((key, data_dict[key]))

 #           data_dict = dmr.read(start_idx, start_idx + 2, "long")
 #           for key in data_dict.keys():
 #            print((key, data_dict[key]))
            
        else:

            print("Error! Neither D or C!")
            return

        #Extracting tar file if a D file        
        if uploadType == 'd':
            #Request ID will be at the end of the path, findall returns a list so need to take the first 
            #(and ideally only) match before stripping the newline
            rID = re.findall("d[0-9]+", path)[0][1:]
            print("Directory Created with ID of " + rID)

            #Now need to grab the location of the tarfile
            datapath = '/' + event.src_path.rsplit('/')[1] + '/' + event.src_path.rsplit('/')[2] + '/tangerine_data/'
            print('datapath:'+datapath)
            #Grep for upload in the folder using the stripped rID
            rawfile = subprocess.check_output('ls ' + datapath + ' | grep d' + rID + '.tar', shell=True)
            #Decode output from bytestring and strip newline
            tar_file = rawfile.decode()[:-1]
            print('tarfile:'+tar_file)
            
            #Now need to set up the tar file
            data = tarfile.open(datapath + tar_file)

            #Take time to calculate size for later before extracting
            size = 0
            for mem in data.getmembers():
                size = size + mem.size

            #Finish extracting tarfile
            data.extractall(path=path) #Extracts to the d# directory
            data.close()
        #Else a C file
        else:
            size = 0
           # tar_file = 'none'
            tar_file = observation_no
            
        #Scrape the metadata from the properties files
        fp = h5py.File(channelPath + '/drf_properties.h5','r')  # WDE added 'r'
        if uploadType == 'd':  # this will be obsolete if all uploads standardize on digital_metadata
            afp = h5py.File(channelPath + '/aux_drf_properties.h5')

        # Getting start time and end time
        drf_data = drf.DigitalRFReader(path)
        startDate, endDate = drf_data.get_bounds('ch0')
        print("bounds:", startDate, endDate)
        # Converting from Unix time to datetime

        #All needed fields for insertion
        dataRate = fp.attrs.get('sample_rate_numerator')
        if uploadType == 'c':
            centerFrequency = freq_list[0] # support one for now
        size = size #Calculated earlier
        fileName = tar_file
        path = path
        station_id = path.rsplit('/')[2]
        ### Patch for demo
        station_id = station_id[-1]
        print("startDate:",startDate)
        print("dataRate:",dataRate)
        myTimestamp = startDate / dataRate
        startDate = datetime.fromtimestamp(myTimestamp, tz=pytz.UTC)

        myTimestamp = endDate / dataRate
        endDate =   datetime.fromtimestamp(myTimestamp, tz=pytz.UTC)

     
        #Finally, we can insert into the db
        conn = engine.connect()
        statement_prefix = 'INSERT INTO observations_observation '
        
        #OLD Insertion
        #statement_cols = '(dataRate, centerFrequency, size, fileName, path, station_id)'
        #statement_vals_tuple = dataRate, centerFrequency, size, fileName, path, station_id

        #NEW Insertion
        #D insertion

        
        #if uploadType == 'd': 
        #    statement_cols = '(dataRate, centerFrequency, size, fileName, path, station_id, startDate, endDate)'
        #    statement_vals_tuple = dataRate, centerFrequency, size, fileName, path, station_id, startDate, endDate
        #else:
        #    statement_cols = '(dataRate, centerFrequency, size, fileName, path, station_id, startDate)'
        #    statement_vals_tuple = dataRate, centerFrequency, size, fileName, path, station_id, startDate
        
        if uploadType == 'd': 
            statement_cols = '(dataRate, size, fileName, path, station_id, startDate, endDate)'
            statement_vals_tuple = dataRate, size, fileName, datapath, station_id, startDate, endDate
        else:
          #  statement_cols = '(dataRate, size, fileName, path, station_id, startDate)'
          #  statement_vals_tuple = dataRate, size, fileName, path, station_id, startDate
            obs_list =  Observation.objects.filter(fileName = fileName) # doe this OBS already exist?
            if len(obs_list) == 0:   # this is a new observation
              theObs  = Observation(dataRate=dataRate,size=obsSize,fileName=fileName,path=path, \
                                      station_id=station_id, startDate=startDate, endDate=endDate)
              theObs.save()
              for this_cfid in cfid_list: # add one or more center frequencies in this datase
                 theObs.centerFrequency.add(this_cfid)
                 theObs.save()
              #theObs.centerFrequency.add(cfid) # this creates entry in intersection table
              #theObs.save()
            else:  # this  observation is already in database. update endDate
              obsPtr = obs_list[0].id    # this is id of existing observation
              print("Existing ID:",obsPtr)
              #theObs = Observation.objects.filter( id = obsPtr)
              #print("existing obs:",theObs)
              Observation.objects.filter( id = obsPtr ).update(endDate = endDate, size=obsSize)

            conn.close()
            return
            
        statement_vals = str(statement_vals_tuple)
        statement = statement_prefix + statement_cols + ' VALUES ' + statement_vals + ';'
        print(statement)
        conn.execute(statement)
        conn.close()

if __name__ == "__main__":
    print("starting watchdog")
     
    path = sys.argv[1] if len(sys.argv) > 1 else '/home'
    event_handler = UploadEvent(patterns=["N*/d*", "N*/c*"])
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print("observer started")
    try:
        while True:
            #print("waiting")
            time.sleep(2)

    finally:            
        print("reached end")
        observer.stop()
        observer.join() 

