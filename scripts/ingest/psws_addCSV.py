# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
# psws_addCSV.py
# Add Graape 1 Legacy csv file to
# Observations table

import os, sys, pytz
from pathlib import Path
from dotenv import load_dotenv

# SCRIPTS_ROOT_DIR is 1 level up from scripts/ingest/
SCRIPTS_ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_ROOT_DIR))

# Load environment variables from scripts/scripts.env
load_dotenv(SCRIPTS_ROOT_DIR / "scripts.env")

# Configuration from environment variables (with defaults)
LOG_PATH = os.getenv("LOG_PATH")
PYTHON_EXECUTABLE = os.getenv("PYTHON_EXECUTABLE")
PLOT_PATH = os.getenv("PLOT_PATH")

if not LOG_PATH:
    raise EnvironmentError("LOG_PATH not set in scripts.env")
if not PYTHON_EXECUTABLE:
    raise EnvironmentError("PYTHON_EXECUTABLE not set in scripts.env")
if not PLOT_PATH:
    raise EnvironmentError("PLOT_PATH not set in scripts.env")

# Django bootstrap to set up environment for Database access
from _bootstrap_django import bootstrap 
bootstrap() 

#from centerfrequencies.models import *
from observations.models import *
from datatypes.models import *
#import datetime

from datetime import timezone
from datetime import datetime as dt
import datetime as dz

def writeLog(theMessage):
    timestamp = dt.now(timezone.utc).isoformat()[0:19]
    # Ensure log directory exists
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    f = open(LOG_PATH, "a")
    f.write(timestamp + " " + theMessage + "\n")
    f.close()

# Arguments are: (1) path, (2) station_id, (3) instrument, (4) trigger

path = str (sys.argv[1])
print("path: '" + path + "'")
station_name  = str(sys.argv[2])
print("station: '" + station_name + "'")
instrument_name = str(sys.argv[3])
print("instrument: '" + instrument_name + "'")
trigger = sys.argv[4]
time_stamp = str(sys.argv[4])[1:18]  # time stamp of the trigger

writeLog("Starting psws_addCSV, path=" + path + " station=" + station_name + " instr=" + instrument_name + " timestamp=" + time_stamp)

obsSize = os.stat(path).st_size

theStationQS = Station.objects.filter(station_id=station_name)
print("found station:",theStationQS)
writeLog("found station" + station_name)
print("values:",theStationQS.values())
print("id by item:",theStationQS.values()[0]["id"])
station_id = theStationQS.values()[0]["id"]
station_instance = Station.objects.get(station_id = station_name) # Look up ID of this Station
# Now check that the instrument name given is assigned to this Station
# In addition, we check if we are given the instrument name or ID
if instrument_name.isdigit():
    if Instrument.objects.filter(id=int(instrument_name)).exists():
        # We've been given the instrument id, so pull data using ID
        theInstrumentQS = Instrument.objects.filter(id=int(instrument_name), station_id=station_id)
else:
    # Given instrument name, so pull data using name
    theInstrumentQS = Instrument.objects.filter(instrument=instrument_name, station_id=station_id)

try:
    instrument_id = theInstrumentQS.values()[0]["id"]
except IndexError as e:
    # the instrument given is not assigned to this station
    writeLog("ERROR. User specified " + station_name + " & " + instrument_name + "; no database match")
    exit()

print("found instrument:",theInstrumentQS)
#writeLog("found instrument:" + theInstrumentQS)

# Look to seeif this observation is already in database
fileName = os.path.basename(path)
writeLog("fileName=" + fileName)
obs_list =  Observation.objects.filter(fileName = fileName, station_id=station_id, instrument_id=instrument_id) # does this OBS already exist?
writeLog("records found=" + str(len(obs_list)))
print("records found=",len(obs_list),'time stamp:',time_stamp)

stime = dt.strptime(time_stamp, '%Y-%m-%dT%H%M%S' )   # original code
#stime = dt.strptime(time_stamp, '%Y-%m-%dT%H:%M' )
startDateTZ = stime.replace(tzinfo=pytz.utc)

if len(obs_list) == 0:   # this is a new observation
  #  startDateTZ = dt.fromtimestamp(time_stamp, tz=pytz.UTC).strftime('%Y-%m-%dT%H%M%S')
   # import datetime as dt
    tdelta = dz.timedelta(minutes= 1439)
    endDateTZ = startDateTZ + tdelta
    theObs  = Observation(dataRate=1,size=obsSize,fileName=fileName,path=os.path.dirname(path), \
        #      instrument_id=instrument_id, station_id=station_id, startDate=startDateTZ, endDate=endDateTZ)
              startDate=startDateTZ, endDate=endDateTZ, \
              station_id = station_id, instrument_id = instrument_id )
    theObs.save()

# Build command for plotting this fldigi observation; use Task Spooler
    PLOTTERS_SCRIPT = str(SCRIPTS_ROOT_DIR / "plotters/plotfldigi1.py")

    cmd = 'ts ' + PYTHON_EXECUTABLE + ' ' + PLOTTERS_SCRIPT + ' -f ' + path + ' -e ' + \
        trigger + ' -p ' + PLOT_PATH + os.path.splitext(fileName)[0] # remove extension
    print("plot cmd=", cmd)
    writeLog("Plot cmd=" + cmd)
    os.system(cmd)

     #  print("saving obs")
     #  # a=input()
     #  theObs.save()

# Register a heartbeat

#from datetime import datetime, timezone

station_instance.last_alive = dt.now(timezone.utc)
# the station_status will update by itself when queried.
station_instance.save()