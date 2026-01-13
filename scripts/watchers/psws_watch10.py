# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
# PSWS Watchdog - watches selected directories for creation of named subdirectories
# When the subdirectory is created, it means that a data upload is complete and
# ready to be cross-referenced into the PSWS database.
# Author: Cole Robbins, University of Alabama, 2021-2022
# Modifications by W. Engelke, May-July 2022, to add other functions & data types
import sys
import tarfile
import re
import subprocess
import time, pytz
#from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers.polling import PollingObserver

import h5py
import digital_rf as drf
from datetime import timezone
from datetime import datetime as dt 
import numpy as np

import os
from urllib.parse import quote_plus

def writeLog(theMessage):
    timestamp = dt.now(timezone.utc).isoformat()[0:19]
    f = open("/var/log/watchdog/watchdog.log", "a")
    f.write(timestamp + " " + theMessage + "\n")
    f.close()

def get_size(start_path):
    global fp
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size

class UploadEvent(PatternMatchingEventHandler):
 #   def __init__(self, patterns=None):
 #       super(UploadEvent, self).__init__(patterns=patterns)

  #  def on_created(self, event):
    def on_created(self, event):
        global fp
        print('event!')
#        return
        if event.src_path.rsplit('/')[-1] == 'm_Test':
            print("Test trigger seen!")
            writeLog("Test file seen at  " + event.src_path)
            print("Located at " + event.src_path)
            os.rmdir(event.src_path)
            print("Removed directory:" + event.src_path)
            time.sleep(1)
            return
        #Begin by identifying if continuous or not
        #Then locating the path of the event
        writeLog("trigger event:" + event.src_path)
        print("UPLOAD trigger at local time: " + dt.now().isoformat())
        e = event.src_path.split('/')
        writeLog("parsed event 1=" + event.src_path.rsplit('/')[1] + ',2=' +event.src_path.rsplit('/')[2] + \
             ',3=' + event.src_path.rsplit('/')[3] + ',4=' + event.src_path.rsplit('/')[4])
        print("parsed event 1=" + event.src_path.rsplit('/')[1] + ',2=' +event.src_path.rsplit('/')[2] + \
             ',3=' + event.src_path.rsplit('/')[3] + ',4=' + event.src_path.rsplit('/')[4])
        try:
            instrumentNo = event.src_path.split("_#")[1] # this should be instrument_id in database
            writeLog("Instrument number found at -> " + event.src_path.split("_#")[1])
            print("Instrument number found at -> " + event.src_path.split("_#")[1])
        except:
            print("ERROR, parsing failure, the '_#' not found")
            writeLog("ERROR - parsing failure, the '_#' not found")
            return

        writeLog("conditional string -> " + event.src_path.rsplit('/')[-1][0])
        writeLog("event.src_path.rsplit('/')[-1][0]='" + event.src_path.rsplit('/')[-1][0] +"'")
        print("conditional string -> " + event.src_path.rsplit('/')[-1][0])
        print("event.src_path.rsplit('/')[-1][0]='" + event.src_path.rsplit('/')[-1][0] +"'")

        if event.src_path.rsplit('/')[-1][0] == 'g': # processing for Grape 1 Legacy (G1L) (fldigi) upload
            writeLog("processing Grape 1 Legacy trigger:" + event.src_path)
            print('G1L trigger',event.src_path)
            observation_no = event.src_path.rsplit('/')[-1][1:len(event.src_path)] # get entire trigger
            observation_no = observation_no.rsplit('_#')[0] # get the filename in trigger
            print("Observation#=" + observation_no)
            writeLog("Observation#=" + observation_no)
            path =        "/".join(event.src_path.rsplit('/')[:-1]) + '/csvData/' + observation_no
            writeLog("Path generated -> " + path)
            obsSize = get_size(path)
            stationID = observation_no.rsplit('_')[1]
            # if this is the 8-character node number, remove the leading zero in the number
            # (This is normal for Grape 1 Legacy stations)
            if len(stationID) == 8:
                stationID = stationID[0] + stationID[2:8]
            writeLog("Station#=" + stationID)
            print("StationID=",stationID)
            instrumentID = event.src_path.rsplit('_#')[1]
            writeLog("Instrument#=" + instrumentID)
            trigger = event.src_path.rsplit('/')[4]
#            if event.src_path.rsplit('/')[3][0] == 'g':
#               trigger = event.src_path.rsplit('/')[3]  # this is non-jailed account
#            else:
#               trigger = event.src_path.rsplit('/')[6] # this is jailed account
            writeLog("trigger=" + trigger)
            # for calling addCSV, arguments are: (1) path, (2) station_id, (3) instrument, (4) trigger
            cmd = '/opt/venv311/bin/python3 psws_addCSV.py ' + path + " " + stationID + \
                " " + instrumentID + " " + trigger
            writeLog("call to psws_addCSV cmd=" + cmd)
            print("psws_addCSV cmd:",cmd)
            os.system(cmd)

            # prepare command for plotting
            cmd = '/opt/venv311/bin/python3 plotfldigi1.py -f ' + path + ' -e ' + event.src_path + \
                  ' -p /psws/psws/media/plots'
            writeLog('plot command=' + cmd)
            return

        if event.src_path.rsplit('/')[-1][0] == 'c': # processing for Continuous type upload (Grape 1 DRF, including rx888)    
            writeLog("Processing trigger:" + event.src_path)
            observation_no = event.src_path.rsplit('/')[-1][1:20]
            path =  "/".join(event.src_path.rsplit('/')[:-1]) + '/' + observation_no
            print('path',path,'observation no',observation_no)
            writeLog("Path generated -> " + path)
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
              print("Start:" , start_idx)
            except IOError as e:
              writeLog("IO error accessing digital metadata, path=" + metadata_dir)
              writeLog(str(e))
              #print("IO error accessing digital metadata")
              return
            fields = dmr.get_fields()
            writeLog("Available fields are <%s>" % (str(fields)))
            print("Available DRF metadata fields are <%s>" % (str(fields)))
            freq_list = []
            # get list of center frequencies in this spectrum (often just 1)
            data_dict = dmr.read(start_idx, start_idx + 2, "center_frequencies")
            writeLog("Center freq list:")
            for x in list(data_dict)[0:1]:
                #writeLog("key{}, val{}:".format(x, data_dict[x]))
                freq_list = data_dict[x]
            print("Freq list:", freq_list)

            print('sample_rate_numerator:',dmr.read(start_idx, start_idx + 2, "sample_rate_numerator"))

            s_r_dict = dmr.read(start_idx, start_idx + 2, "sample_rate_numerator")
            fkey, fval = next(iter(s_r_dict.items()))
            print('s_r_dict fkey fval',fkey, fval)
            dataRate = fval  # this is the sample rate for the observation
            if not (os.path.isfile(channelPath + '/drf_properties.h5')):
                writeLog("DRF Properties file missing!")
                return
      
            if not (os.path.exists(channelPath)):
                writeLog("Channel path does not exist! Might be issue with parsing of trigger file name.")
                return
            if not (os.path.exists(channelPath + '/metadata/dmd_properties.h5')):
                writeLog("DMD Properties file missing!")
                return

            # Getting start time and end time
            drf_data = drf.DigitalRFReader(path)
            startDate, endDate = drf_data.get_bounds('ch0')
            print("bounds:", startDate, endDate)
            writeLog("Got Bounds")

        #All needed fields for insertion
          #  dataRate = fp.attrs.get('sample_rate_numerator') # this orig. code is INOP
            if uploadType == 'c':
                centerFrequency = freq_list[0] # support one for now
            datapath = path
            fileName = observation_no
            station_id = path.rsplit('/')[-2]
            print("startDate:",startDate)
            print("dataRate:",dataRate)
            myTimestamp = startDate / dataRate

            startDate = dt.fromtimestamp(myTimestamp, tz=pytz.UTC).strftime('%Y-%m-%dT%H:%M')
            print("Start date:" + startDate)
            myTimestamp = endDate / dataRate
            endDate =   dt.fromtimestamp(myTimestamp, tz=pytz.UTC).strftime('%Y-%m-%dT%H:%M')
            print("End date:"+endDate)
            command = "/opt/venv311/bin/python3 psws_addOBS.py " + str(dataRate) + " " + str(obsSize) + " " +  \
                   fileName + " " + datapath + " " + station_id + " " + instrumentNo + " " + \
                   startDate + " " + endDate + " "
            for this_freq in freq_list:
                command = command + str(this_freq) + " "
        
            print   ("Issuing command:" + command)
            writeLog("Issuing command:" + command)
            os.system(command)
            args = list(command.split(" "))
            subprocess.run(args)
            writeLog("Issued syscommand:" + command)

            try:
                writeLog("Trigger graphing  program")
                # This uses task spooler (ts) to make multiple plot jobs run in a queue
                graph_command = "ts /opt/venv311/bin/python3 /var/www/html/plotspectrum_v8.py -e " + event.src_path + " -p /psws/psws/media/plots" 
          
                writeLog("Running graph_command ----> " + graph_command)
                os.system(graph_command)
                writeLog("Graphing command run!")

               # Removes target directory
                os.rmdir(event.src_path)
                writeLog("Removed directory:" + event.src_path)


            except Exception as ex:
                print("Exception: ", str(ex))
                writeLog("Exception: " + str(ex))


        elif event.src_path.rsplit('/')[-1][0] == 'm': # processing for "m" (magnetometer) type upload
            observation_no = event.src_path.rsplit('/')[-1][1:20]
            print("path from watchdog:" + event.src_path)
            path =        '/'.join(event.src_path.rsplit('/')[:-1]) + '/magData'
            writeLog("Path generated -> " + path)
            obsSize = get_size(path)
            station_id = path.rsplit('/')[-2]
            #dataRate = 1 # one rec per second
            endDate = event.src_path[-16:]  # get the last 16 char of the trigger, this is timestamp of the upload
            print('path='+path + ' station_id=' + station_id)

            # Assumptions
            # Last 16 bytes of trigger directory is time stamp of the upload
            # The path contains one to n zip files that are daily magnetometer logs
            # Each zipped magnetometer file is of the form OBSYYYY-MM-DDTHH:SS.zip 
            # The date in the zip file name is when the magnetometer data starts, in UTC

            command = "/opt/venv311/bin/python3 psws_addMAG.py " + path + " " + \
                      station_id + " " + instrumentNo + " "  + endDate 
            #freq_list = [] # for magnetometer
            #freq_list.append('0.0') # single frequency
            #for this_freq in freq_list:
            #    command = command + str(this_freq) + " "
            print("Issuing command: " + command)
            os.system(command)
            writeLog("Issued syscommand:" + command)
            
            # Using venv instead of os.system
            args = list(command.split(" "))
            subprocess.run(args)

            # Removes target directory
            os.rmdir(event.src_path)
            writeLog("Removed directory:" + event.src_path)
            return

        else:
            writeLog("ERROR. Unrecognized upload type: " + event.src_path.rsplit('/')[-1][0] )
         #   print   ("Error! Unrecognized upload type: " + event.src_path.rsplit('/')[-1][0] )
            return

        # Here removed obsolete code for "d" (data request) - was never implemented
        #Else a C file

        if uploadType == 'c':
            size = 0
           # tar_file = 'none'
            tar_file = observation_no
            
        #Scrape the metadata from the properties files
        writeLog("Scraping metadata!")
        if (os.path.isfile(channelPath + '/drf_properties.h5')):
            fp = h5py.File(channelPath + '/drf_properties.h5','r')  # WDE added 'r'
        else:
            writeLog("Cannot find metadata!")
            return
        writeLog("Successfully scraped metadata!")
        

##############################################################################################################################

# directory starting with "d" - upload is in response to a Data Request  (future)
# directory starting with "c" = upload is from a Continuous Upload (Grape 1 DRF)
# directory starting with "m" = upload is from magnetometer data
# directory starting with "g" = upload is from Grape 1 Legacy instrument
# directory starting with "G" = upload is from Grape 2 instrument (future)


if __name__ == "__main__":
    print("starting watchdog, v10")
    writeLog("Watchdog 10 starting")

    root = sys.argv[1] if len(sys.argv) > 1 else "/psws/home"
    root = os.path.abspath(root)


    print("Starting watchdog (polling, non-recursive S*/N*/T*)")
    writeLog("Watchdog polling starting at " + root)

    observer = PollingObserver(timeout=10.0)  # 2 for testing; bump to 10+ in production
    handler = UploadEvent()

    # Watch each existing S*, N*, T* directory directly under /psws/home
    for entry in os.scandir(root):
        if entry.is_dir() and entry.name[0] in ( "T", "S", "N"): #  "S", "N" are production, "T" is for testing
            print("Watching:", entry.path)
            observer.schedule(handler, entry.path, recursive=False)

    observer.start()
    print("observer started")
    writeLog("Watchdog polling observer started")

    try:
        while True:
            time.sleep(2)
    finally:
        print("Stopping observer")
        observer.stop()
        observer.join()

