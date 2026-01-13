# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
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
import numpy as np

import os
from urllib.parse import quote_plus

def writeLog(theMessage):
    timestamp = dt.now(timezone.utc).isoformat()[0:19]
    f = open("/var/www/html/watchdog.log", "a")
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
        print('event')
        if event.src_path.rsplit('/')[-1] == 'm_Test':
            print("Test file seen!")
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
        writeLog("parsed event 0=" + event.src_path.rsplit('/')[0] + ',1=' +event.src_path.rsplit('/')[1] + \
             ',2=' + event.src_path.rsplit('/')[2] + ',3=' + event.src_path.rsplit('/')[3])

        try:
            instrumentNo = event.src_path.split("_#")[1] # this should be instrument_id in database
            writeLog("Instrument number found at -> " + event.src_path.split("_#")[1])
        except:
            print("ERROR, parsing failure, the '_#' not found")
            writeLog("ERROR - parsing failure, the '_#' not found")
            return

        writeLog("conditional string -> " + event.src_path.rsplit('/')[-1][0])
        writeLog("event.src_path.rsplit('/')[-1][0]='" + event.src_path.rsplit('/')[-1][0] +"'")

        # if event.src_path.rsplit('/')[-1][0] == 'd':  # processing for Data Request type upload
            # print("D!")
            # path = event.src_path
            # channelPath = event.src_path + "/ch0"
            # uploadType = 'd'

            # GRAPHING COMMAND TESTING
            # graph_command = "ts python3 /var/www/html/graphing_testing.py " + event.src_path
            #os.system(graph_command)

        if event.src_path.rsplit('/')[-1][0] == 'g': # processing for Grape 1 Legacy (fldigi) upload
            writeLog("processing Grape 1 Legacy trigger:" + event.src_path)
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
            if event.src_path.rsplit('/')[3][0] == 'g':
               trigger = event.src_path.rsplit('/')[3]  # this is non-jailed account
            else:
               trigger = event.src_path.rsplit('/')[6] # this is jailed account
            writeLog("trigger=" + trigger)
            # for calling addCSV, arguments are: (1) path, (2) station_id, (3) instrument, (4) trigger
            cmd = '/opt/venv311/bin/python3 psws_addCSV.py ' + path + " " + stationID + \
                " " + instrumentID + " " + trigger
            writeLog("call to psws_addCSV cmd=" + cmd)
            print("psws_addCSV cmd:",cmd)
            os.system(cmd)
            # prepare command for plotting
         #   cmd = 'python3 plotfldigi1.py -f ' + path + ' -e ' + event.src_path + \
          #        ' -p /var/www/html/PSWS/static/PSWS/media'
          #  writeLog('plot command=' + cmd)
            return

        if event.src_path.rsplit('/')[-1][0] == 'c': # processing for Continuous type upload (Grape 1 DRF)
          #  print("C! path=" + event.src_path)
            writeLog("Processing trigger:" + event.src_path)
            observation_no = event.src_path.rsplit('/')[-1][1:20]
            # path = "/" + event.src_path.rsplit('/')[1] + "/" +  event.src_path.rsplit('/')[2] \
            #        +  "/" + observation_no
            #path = "/" + "/".join(event.src_path.rsplit('/')[:-1]) + '/' + observation_no # WDE replaced by the following
            path =        "/".join(event.src_path.rsplit('/')[:-1]) + '/' + observation_no
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
    #          print("Start:" , start_idx)
            except IOError as e:
              writeLog("IO error accessing digital metadata, path=" + metadata_dir)
              writeLog(str(e))
              #print("IO error accessing digital metadata")
              return
            fields = dmr.get_fields()
            #writeLog("Available fields are <%s>" % (str(fields)))
            freq_list = []
            # get list of center frequencies in this spectrum (often just 1)
            data_dict = dmr.read(start_idx, start_idx + 2, "center_frequencies")
            #writeLog("Center freq list:")
            for x in list(data_dict)[0:1]:
                #writeLog("key{}, val{}:".format(x, data_dict[x]))
                freq_list = data_dict[x]
            #print("Freq list:", freq_list)

            # GRAPHING COMMAND
            if not (os.path.isfile(channelPath + '/drf_properties.h5')):
                writeLog("DRF Properties file missing!")
                return
            # EMERGENCY CHNAGE TO PREVENT s000123 from crashing watchdog
            if not (os.path.exists(channelPath)):
                writeLog("Channel path does not exist! Might be issue with parsing of trigger file name.")
                return
            if not (os.path.exists(channelPath + '/metadata/dmd_properties.h5')):
                writeLog("DMD Properties file missing!")
                return
            try:
                writeLog("Trigger graphing  program")
                # This uses task spooler (ts) to make multiple plot jobs run in a queue
                graph_command = "ts /opt/venv311/bin/python3 /var/www/html/plotspectrum_v8.py -e " + event.src_path + " -p /psws/psws/media/plots" 
            #    graph_command = "ts /home/N000004/virtualenvs/dev/bin/python3 /var/www/html/plotspectrum_v7.py -e " + event.src_path + " -p /var/www/html/PSWS/static/PSWS/plots" 
                # graph_command = subprocess.Popen(['/home/N000004/virtualenvs/dev/bin/python3', '/var/www/html/plotspectrum_v5.py', '-e', event.src_path, '-p', '/var/www/html/PSWS/static/PSWS/plots'])
                #graph_command = "/home/N000004/virtualenvs/dev/bin/python3 /var/www/html/plotspectrum_v7.py -e " + event.src_path + " -p /var/www/html/PSWS/static/PSWS/plots | at -q b -m now & "
                # graph_command = subprocess.Popen(['/home/N000004/virtualenvs/dev/bin/python3', '/var/www/html/plotspectrum_v7.py', '-e', event.src_path, '-p', '/var/www/html/PSWS/static/PSWS/plots'])

                writeLog("Running graph_command ----> " + graph_command)
                os.system(graph_command)
                # writeLog(graph_command.stdout)
                writeLog("Graphing command run!")
            except Exception as ex:
                print("Exception: ", str(ex))
                writeLog("Exception: " + str(ex))


        elif event.src_path.rsplit('/')[-1][0] == 'm': # processing for "m" (magnetometer) type upload
            observation_no = event.src_path.rsplit('/')[-1][1:20]
            print("path from watchdog:" + event.src_path)
            # path = "/" + event.src_path.rsplit('/')[1] + "/" +  event.src_path.rsplit('/')[2] + "/magData/"
            #path = "/" + '/'.join(event.src_path.rsplit('/')[:-1]) + '/magData'  # WDE replaced with following
            path =        '/'.join(event.src_path.rsplit('/')[:-1]) + '/magData'
            writeLog("Path generated -> " + path)
            obsSize = get_size(path)
            station_id = path.rsplit('/')[-2]
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

            command = "/opt/venv311/bin/python3 psws_addMAG.py " + path + " " + \
                      station_id + " " + instrumentNo + " "  + endDate 
            #freq_list = [] # for magnetometer
            #freq_list.append('0.0') # single frequency
            #for this_freq in freq_list:
            #    command = command + str(this_freq) + " "
            print("Issuing command: " + command)
            # os.system(command)
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

        #Extracting tar file if a D file        
        if uploadType == 'd':
            #Request ID will be at the end of the path, findall returns a list so need to take the first 
            #(and ideally only) match before stripping the newline
            rID = re.findall("d[0-9]+", path)[0][1:]
            print("Directory Created with ID of " + rID)

            #Now need to grab the location of the tarfile
            # datapath = '/' + event.src_path.rsplit('/')[1] + '/' + event.src_path.rsplit('/')[2] + '/tangerine_data/'
            # print('datapath:'+datapath)
            datapath = '/'.join(event.src_path.rsplit('/')[:-1]) + '/tangerine_data/'
            writeLog("Path generated -> " + datapath)
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
        writeLog("Scraping metadata!")
        if (os.path.isfile(channelPath + '/drf_properties.h5')):
            fp = h5py.File(channelPath + '/drf_properties.h5','r')  # WDE added 'r'
        else:
            writeLog("Cannot find metadata!")
            return
        if uploadType == 'd':  # this will be obsolete if all uploads standardize on digital_metadata
            afp = h5py.File(channelPath + '/aux_drf_properties.h5')
        writeLog("Successfully scraped metadata!")
        
        # Getting start time and end time
        drf_data = drf.DigitalRFReader(path)
        startDate, endDate = drf_data.get_bounds('ch0')
        print("bounds:", startDate, endDate)
        writeLog("Got Bounds")
        # writeLog("bounds: " + startDate + " " + endDate)
        # Converting from Unix time to datetime

        #All needed fields for insertion
        dataRate = fp.attrs.get('sample_rate_numerator')
        if uploadType == 'c':
            centerFrequency = freq_list[0] # support one for now
            datapath = path
        # size = size #Calculated earlier
        fileName = tar_file
       # path = path
        station_id = path.rsplit('/')[-2]
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
        command = "/opt/venv311/python3 psws_addOBS.py " + str(dataRate) + " " + str(obsSize) + " " +  \
                   fileName + " " + datapath + " " + station_id + " " + instrumentNo + " " + \
                   startDate + " " + endDate + " "
        for this_freq in freq_list:
            command = command + str(this_freq) + " "
        
        print   ("Issuing command:" + command)
        writeLog("Issuing command:" + command)
        # os.system(command)
        args = list(command.split(" "))
        subprocess.run(args)
        # writeLog("Issued syscommand:" + command)

        # Removes target directory
        os.rmdir(event.src_path)
        writeLog("Removed directory:" + event.src_path)

##############################################################################################################################

if __name__ == "__main__":
    print("starting watchdog, v10")
    writeLog("Watchdog triggered")
     
    path = sys.argv[1] if len(sys.argv) > 1 else '/home'

# directory starting with "d" - upload is in response to a Data Request  (future)
# directory starting with "c" = upload is from a Continuous Upload (Grape 1 DRF)
# directory starting with "m" = upload is from magnetometer data
# directory starting with "g" = upload is from Grape 1 Legacy instrument
# directory starting with "G" = upload is from Grape 2 instrument (future)

    event_handler = UploadEvent(patterns=["S*/m*", "N*/c*", "N*/m*", "S*/d*", "S*/c*", "N*/c*", "N*/g*", 
        "stations/N*/home/N*/c*", "stations/N*/home/N*/m*", "stations/m*", "stations/N*/m*", "stations/N*/home/N*/m*", 
        "stations/N*/home/N*/g*", 'abliddle/m_Test' ]) 
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    print("observer started")
    writeLog("Starting watchdog, v8")
    try:
        while True:
        #    print("waiting")
            time.sleep(2)

    finally:            
        print("reached end")
        observer.stop()
        observer.join() 



