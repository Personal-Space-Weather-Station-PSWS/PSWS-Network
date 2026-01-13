# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
#!/usr/bin/env python3

# THese imports support interoperation with Django and digital_rf objects
import tarfile
import re
import subprocess
import pytz
import h5py
import digital_rf as drf
from datetime import timezone
from datetime import datetime as dt
import numpy as np
from urllib.parse import quote_plus

import os, sys, time
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from watchdog.observers.polling import PollingObserver  # <- polling, not inotify

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "/home")

# Trigger types
# m - magnetometer
# t - test
# g - grape 1 Legacy (G1L)
# c - grapde 1 digital RF  (G1DRF)
# d - future item for data request (not yet implemented)

TRIGGER_NAMES = {"m", "t", "g", "c", "m_Test"}

'''
def writeLog(msg):
    print(msg, flush=True)  # replace with your real logger
'''
def writeLog(theMessage):
    print("log:",theMessage)
    timestamp = dt.now(timezone.utc).isoformat()[0:19]
    f = open("/var/log/watchdog/watchdog.log", "a")
    f.write(timestamp + " " + theMessage + "\n")
    f.close()

def get_size(start_path): # Calculate size of directory containing observation
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)

    return total_size

# These routines support the watchdog polling system

def is_parent_of_interest(name: str) -> bool:
    # Parent directory must be exactly T000001 or start with S/N
    return name == "T000001" or name.startswith(("S", "N"))

class TriggerDirHandler(FileSystemEventHandler):
    """Watches ONE parent directory (non-recursive) for the trigger dir(s)."""
    def __init__(self, parent_path: Path):
        self.parent_path = Path(parent_path)

    def on_created(self, event):
        print('event detected:',event)
        if event.is_directory:
            leaf = os.path.basename(event.src_path)
            if leaf in TRIGGER_NAMES or leaf[0] in TRIGGER_NAMES:
                writeLog(f"[TRIGGER] {event.src_path} created under {self.parent_path}")
 
   # Process a test trigger; if it is m_Test, delete is, else leave it.
                if event.src_path.rsplit('/')[-1] == 'm_Test':
                    print("Test file seen!")
                    writeLog("Test file seen at  " + event.src_path)
                    print("Located at " + event.src_path)
                    os.rmdir(event.src_path)
                    print("Removed directory:" + event.src_path)
                    return
 
                print("UPLOAD trigger at local time: " + dt.now().isoformat())
                writeLog("parsed event 0=" + event.src_path.rsplit('/')[0] + ',1=' +event.src_path.rsplit('/')[1] + \

                  ',2=' + event.src_path.rsplit('/')[2] + ',3=' + event.src_path.rsplit('/')[3])
   
  # Now we have trigger directory; does it contain an instrument number?
                try:
                    instrumentNo = event.src_path.split("_#")[1] # this should be instrument_>
                    writeLog("Instrument number found at -> " + event.src_path.split("_#")[1])
                except:
                    print("ERROR, parsing failure, the '_#' not found")
                    writeLog("ERROR - parsing failure, the '_#' not found")
                    return

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
                    cmd = '/opt/venv311/bin/python3 /var/www/html/psws_addCSV.py ' + path + " " + stationID + \
                        " " + instrumentID + " " + trigger
                    writeLog("call to psws_addCSV cmd=" + cmd)
                    print("psws_addCSV cmd:",cmd)
                    os.system(cmd)            
                    return


                if event.src_path.rsplit('/')[-1][0] == 'c': # processing for Continuous type upload (Grape 1 DRF)
                    writeLog("Processing trigger:" + event.src_path)
                    observation_no = event.src_path.rsplit('/')[-1][1:20]
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
                      print("Start:" , start_idx)
                    except IOError as e:
                      writeLog("IO error accessing digital metadata, path=" + metadata_dir)
                      writeLog(str(e))
                      print("IO error accessing digital metadata")
                      return
                    fields = dmr.get_fields()
                    freq_list = []
                    # get list of center frequencies in this spectrum (often just 1)
                    data_dict = dmr.read(start_idx, start_idx + 2, "center_frequencies")
                    for x in list(data_dict)[0:1]:
                         #writeLog("key{}, val{}:".format(x, data_dict[x]))
                        print("key{}, val{}:".format(x, data_dict[x]))
                        freq_list = data_dict[x]
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

# Add OBS to database section

                    size = 0
                    tar_file = observation_no
                    #Scrape the metadata from the properties files
                    writeLog("Scraping metadata!")
                    if (os.path.isfile(channelPath + '/drf_properties.h5')):
                        fp = h5py.File(channelPath + '/drf_properties.h5','r')
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
                    #All needed fields for insertion
                    dataRate = fp.attrs.get('sample_rate_numerator')
                    if type(dataRate) == None:
                        writeLog('sample_rate_numerator not found in metadata; skipping record')
                        print('sample_rate_numerator not found; skip')
                        return 
                    if uploadType == 'c': # is sample_rate numerator a float or a list
                        if isinstance(freq_list, float):
                            centerFrequency = freq_list # this should be a float
                        elif isinstance(freq_list, (list, dict)):
                            centerFrequency = freq_list[0] # support one for now
                        datapath = path
                    fileName = tar_file
                    station_id = path.rsplit('/')[-2]
                    if dataRate is None:
                        print("sample_rate_numerator not found")
                        writeLog('sample_rate_numerator not found, skipping')
                        return
                    if startDate is None:
                        writeLog('startDate missing, skipping')
                        return
                    print("startDate:",startDate)
                    print("dataRate:",dataRate)
                    try:
                        myTimestamp = startDate / dataRate
                    except:
                        writeLog('Bad/missing dataRate in metadata, skipping')
                        return
                    startDate = dt.fromtimestamp(myTimestamp, tz=pytz.UTC).strftime('%Y-%m-%dT%H:%M')
                    print("Start date:" + startDate)
                    myTimestamp = endDate / dataRate
                    endDate =   dt.fromtimestamp(myTimestamp, tz=pytz.UTC).strftime('%Y-%m-%dT%H:%M')
                    print("End date:"+endDate)

                    command = 'ts -S 12'    # set task spooler to support up to 12 simultaneous taaks
                    args = list(command.split(" "))
                    subprocess.run(args)
                    
                    command = "/opt/venv311/bin/python psws_addOBS.py " + str(dataRate) + " " + str(obsSize) + " " +  \
                        fileName + " " + datapath + " " + station_id + " " + instrumentNo + " " + \
                        startDate + " " + endDate + " "

                    if isinstance(freq_list, float):   # this is a single float or a list
                        command = command + str(freq_list) + " "  # this is a single value
                    elif isinstance(freq_list, list):
                        for this_freq in freq_list:
                            command = command + str(this_freq) + " "
                    print   ("Issuing command:" + command)
                    writeLog("Issuing command:" + command)
                    args = list(command.split(" "))
                    subprocess.run(args)
                    # Removes target directory
                    os.rmdir(event.src_path)
                    writeLog("Removed directory:" + event.src_path)

# End of database section




                    try:
                        writeLog("Trigger graphing  program")
                        # This uses task spooler (ts) to make multiple plot jobs run in a queue
                        graph_command = "ts /opt/venv311/bin/python3 /var/www/html/plotspectrum_v8.py -e " + \
                            event.src_path  # plot path will be set in plotspectrum
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
                    path =        '/'.join(event.src_path.rsplit('/')[:-1]) + '/magData'
                    writeLog("Path generated -> " + path)
                    obsSize = get_size(path)
                    station_id = path.rsplit('/')[-2]
                    endDate = event.src_path[-16:]  # get the last 16 char of the trigger, this is timestamp of the upload
                    print('path='+path + ' station_id=' + station_id)

                    # Assumptions
                    # Last 16 bytes of trigger directory is time stamp of the upload
                    # The path contains one to n zip files that are daily magnetometer logs
                    # Each zipped magnetometer file is of the form OBSYYYY-MM-DDTHH:SS.zip
                    # The date in the zip file name is when the magnetometer data starts, in UTC

                    # Make sure to use the correct virtual environment here; needs to match
                    #  what is in /etc/systemd/system/watchX.service
                    command = "/opt/venv311/bin/python3 /var/www/html/psws_addMAG.py " + path + " " + \
                              station_id + " " + instrumentNo + " "  + endDate
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
                    return



############### Handlers for watchdog #######################################
class RootHandler(FileSystemEventHandler):
    """Watches ROOT (non-recursive) for new parent dirs, then adds per-parent watches."""
    def __init__(self, observer, root: Path):
        self.observer = observer
        self.root = Path(root)

    def on_created(self, event):
        if event.is_directory:
            name = os.path.basename(event.src_path)
            if is_parent_of_interest(name):
                writeLog(f"[PARENT-NEW] {event.src_path} — adding trigger watch")
                self.observer.schedule(TriggerDirHandler(Path(event.src_path)),
                                       event.src_path, recursive=False)

def add_existing_parents(observer, root: Path):
    """At startup, add watches for parents that already exist."""
    for child in root.iterdir():
        try:
            if child.is_dir() and is_parent_of_interest(child.name):
                writeLog(f"[PARENT-EXISTING] {child} — adding trigger watch")
                observer.schedule(TriggerDirHandler(child), str(child), recursive=False)
        except PermissionError:
            writeLog(f"[WARN] permission denied scanning {child}")



######################################################################################
if __name__ == "__main__":
    print("starting watchdog (polling), V10")
    writeLog(f"Watching ROOT: {ROOT} (exists={ROOT.is_dir()})")

    observer = PollingObserver(timeout=5.05)  # polling loop; tune timeout if desired

    # 1) Watch /home non-recursively for new S*/N*/T000001 parents
    root_handler = RootHandler(observer, ROOT)
    observer.schedule(root_handler, str(ROOT), recursive=False)

    # 2) Also watch any existing parents at startup
    add_existing_parents(observer, ROOT)

    observer.start()
    writeLog("Polling observer started")

    try:
        while True:
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        writeLog("Stopping observer…")
        observer.stop()
        observer.join()
