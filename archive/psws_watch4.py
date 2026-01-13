 # PSWS Watchdog - watches selected directories for creation of named subdirectories.
# When the subdirectory is created, it means that a data upload is complete and
# ready to be cross-referenced into the PSWS database.
# Author: Cole Robbins, University of Alabama, 2021-2022
# Modifications by W. Engelke, May-July 2022, to add other functions & data types
import sys
import tarfile
import re
import subprocess
import time, pytz
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import h5py
import digital_rf as drf
from datetime import timezone
from datetime import datetime as dt 
#from dt import timeezone
import numpy as np

#from sqlalchemy import create_engine

import os
from urllib.parse import quote_plus

def writeLog(theMessage):
    timestamp = dt.now(timezone.utc).isoformat()[0:19]
    f = open("/home/bengelke/Documents/watchdog.log", "a")
    f.write(timestamp + " " + theMessage + "\n")
    f.close()

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
        print("UPLOAD trigger at local time: " + dt.now().isoformat())
        print("ULOAD path='" + event.src_path +"'")
        writeLog("UPLOAD, path " + event.src_path)
        instrumentNo = event.src_path.split("_#")[1] # this should be instrument_id in database

        if event.src_path.rsplit('/')[3][0] == 'd':  # processing for Data Request type upload
            print("D!")
            path = event.src_path
            channelPath = event.src_path + "/ch0"
            uploadType = 'd'

        elif event.src_path.rsplit('/')[3][0] == 'c': # processing for Continuous type upload
            print("C! path=" + event.src_path)
            observation_no = event.src_path.rsplit('/')[3][1:20]
            path = "/" + event.src_path.rsplit('/')[1] + "/" +  event.src_path.rsplit('/')[2] \
                    +  "/" + observation_no
            obsSize = get_size(path)
            print("Data size=", obsSize)
            # prepare to get DRF metadata for inclusion into database
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
            # get list of center frequencies in this spectrum (often just 1)
            data_dict = dmr.read(start_idx, start_idx + 2, "center_frequencies")
   #         print("Center freq list:")
            for x in list(data_dict)[0:1]:
  #             print("key{}, val{}:".format(x, data_dict[x]))
               freq_list = data_dict[x] 
            #print("Freq list:", freq_list)

        elif event.src_path.rsplit('/')[3][0] == 'm': # processing for "m" (magnetometer) type upload
            observation_no = event.src_path.rsplit('/')[3][1:20]
            print("path from watchdog:" + event.src_path)
            path = "/" + event.src_path.rsplit('/')[1] + "/" +  event.src_path.rsplit('/')[2] + "/magData/"

            obsSize = get_size(path)
            station_id = path.rsplit('/')[2]
            #dataRate = 1 # one rec per second
            endDate = event.src_path[-16:]  # get the last 16 char of the trigger, this is timestamp of the upload
          #  datapath = '/' + event.src_path.rsplit('/')[1] + '/' + event.src_path.rsplit('/')[2] + '/tangerine_data/'
            print('path='+path + ' station_id=' + station_id)
            #startDate = "2022-01-01T00:00" # temporary
            #endDate = "2022-01-01T00:00"
            #fileList = os.listdir(path)
            #fileName = fileList[0]  # for this version we support only one file in this directory

          #  fileName = observation_no

            # Assumptions
            # Last 16 bytes of trigger directory is time stamp of the upload
            # The path contains one to n zip files that are daily magnetometer logs
            # Each zipped magnetometer file is of the form OBSYYYY-MM-DDTHH:SS.zip 
            # The date in the zip file name is when the magnetometer data starts, in UTC

            command = "python3 psws_addMAG.py " + path + " " + \
                      station_id + " " + instrumentNo + " "  + endDate 
            #freq_list = [] # for magnetometer
            #freq_list.append('0.0') # single frequency
            #for this_freq in freq_list:
            #    command = command + str(this_freq) + " "
            print("Issuing command: " + command)
            os.system(command)
            writeLog("Issued syscommand:" + command)
            return

        else:
            print("Error! Unrecognized upload type: " + event.src_path.rsplit('/')[3][0] )
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
        elif uploadType == 'c':
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
            datapath = path
        # size = size #Calculated earlier
        fileName = tar_file
       # path = path
        station_id = path.rsplit('/')[2]
        ### Patch for demo
 #       station_id = station_id[-1]
        print("startDate:",startDate)
        print("dataRate:",dataRate)
        myTimestamp = startDate / dataRate

        startDate = dt.fromtimestamp(myTimestamp, tz=pytz.UTC).strftime('%Y-%m-%dT%H:%M')
        print("Start date:" + startDate)
        myTimestamp = endDate / dataRate
        endDate =   dt.fromtimestamp(myTimestamp, tz=pytz.UTC).strftime('%Y-%m-%dT%H:%M')
        print("End date:"+endDate)
        command = "python3 psws_addOBS.py " + str(dataRate) + " " + str(obsSize) + " " +  \
                   fileName + " " + datapath + " " + station_id + " " + instrumentNo + " " + \
                   startDate + " " + endDate + " "
        for this_freq in freq_list:
            command = command + str(this_freq) + " "
        print("Issuing command: " + command)
        os.system(command)
        writeLog("Issued syscommand:" + command)

if __name__ == "__main__":
    print("starting watchdog")
     
    path = sys.argv[1] if len(sys.argv) > 1 else '/home'
# directory starting with "d" - this upload is in response to a Data Request
# directory starting with "c" = this upload is from a Continuous Upload
# directory starting with "m" = this upload is from magnetometer data
# The "N" prefixes are legacy, need to delete after test period
    event_handler = UploadEvent(patterns=["S*/m*", "N*/c*", "N*/m*", "S*/d*", "S*/c*", "N*/c*" ]) 
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print("observer started")
    writeLog("Starting watchdog")
    try:
        while True:
        #    print("waiting")
            time.sleep(2)

    finally:            
        print("reached end")
        observer.stop()
        observer.join() 


