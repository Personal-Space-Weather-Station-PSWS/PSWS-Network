# DRF Spectrum Plotter
# Author: W. Engelke, AB4EJ, University of Alabama

import matplotlib.pyplot as plt
import matplotlib.colors
import numpy as np
import digital_rf as drf
from datetime import datetime
import datetime
from datetime import timezone
import math
import os, tempfile
import maidenhead as mh 
import sys, getopt, os

# imports needed to interact with database
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'PSWS.PSWS.settings'
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
from django.db import models
django.setup()
from centerfrequencies.models import *
from observations.models import *
from stations.models import *

output_path = "/home/plots" # for use on pswsnetwork server

# Get supplied argument(s)
# Remove 1st argument from the
# list of command line arguments
argumentList = sys.argv[1:]
print("Arg list:",argumentList)

# Options - these are valid options
options = "hf:p:e:"
 
# Long options
long_options = ["Help", "theDate", "file"]

try:
    # Parsing argument
    arguments, values = getopt.getopt(argumentList, options, long_options)
     
    # checking each argument
    for currentArgument, currentValue in arguments:
 
        if currentArgument in ("-h", "--Help"):
            print ("-d YYYY-MM-DD -f filewname")

        elif currentArgument in ("-f", "--file"):
            print ("the file:",currentValue)
            dataDir = currentValue

        elif currentArgument in ("-p", "--outpath"):
            print("output path:",currentValue)
            output_path = currentValue
           
        elif currentArgument in ("-e", "--event"):
            print("the event:",currentValue)
            event_src_path = currentValue

except getopt.error as err:
    # output error, and return with an error code
    print (str(err))

# parse the event (which came from watchdog)
stationIDstr = event_src_path.rsplit('/')[2]
instrumentID = event_src_path.rsplit('_#')[1]
#filename = datapath.rsplit('c')[1]
datapath = event_src_path.rsplit('_#')[0].rsplit('c')[0]
filename = event_src_path.rsplit('_#')[0].rsplit('c')[1]
print("datapath",datapath)
print("filename",filename)
dataDir = os.path.join(datapath,filename)
print("data dir=", dataDir)
   

plt.style.use('_mpl-gallery-nogrid')
maidenheadGrid = 'EN91' # default
# plot
fig, ax = plt.subplots()

metadata_dir = dataDir + '//ch0//metadata'

print("Looking for metadata at:" + metadata_dir)

do = drf.DigitalRFReader(dataDir)
s, e = do.get_bounds('ch0')

#print("Plot spectrum for what date?  (YYYY-MM-DD)")
#t =input()
t = dataDir[-16:] # + "T00:00"

station = dataDir[-27:-20] # may come from database
print("station ",station)

print("request date:" + t)
requestTime = datetime.strptime(t, '%Y-%m-%dT%H-%M')
# these are based on unix time * 10 (for 10 samples/sec)
timestamp = requestTime.replace(tzinfo=timezone.utc).timestamp() * 10

s = int(timestamp)
print("time stamp ",s)

freqList = [0]
theLatitude = 0
theLongitude = 0


# get Metadata, if it exists
try:
    dmr = drf.DigitalMetadataReader(metadata_dir)
    print("metadata init okay")
    first_sample, last_sample = dmr.get_bounds()
    print("metadata bounds are %i to %i" % (first_sample, last_sample))

    start_idx = int(np.uint64(first_sample))
    print('computed start_idx = ',start_idx)

    fields = dmr.get_fields()
    print("Available fields are <%s>" % (str(fields)))

    print("first read - just get one column ")
    data_dict = dmr.read(start_idx, start_idx + 2, "center_frequencies")
    for key in data_dict.keys():
      #  print((key, data_dict[key]))
        freqList = data_dict[key]
        print("freq = ",freqList[0])

    data_dict = dmr.read(start_idx, start_idx + 2, "lat")
    for key in data_dict.keys():
     #   print((key, data_dict[key]))
        theLatitude = data_dict[key]
        print("Latitude: ",theLatitude)
        
    data_dict = dmr.read(start_idx, start_idx + 2, "long")
    for key in data_dict.keys():
      #  print((key, data_dict[key]))
        theLongitude = data_dict[key]
        print("Longitude: ",theLongitude)

   #  maidenheadGrid = to_grid(theLatitude, theLongitude)
    maidenheadGrid = mh.to_maiden(theLatitude, theLongitude, 3)
      
except IOError:
    print("IO Error; metadata not found at " + metadata_dir)

# size of bigarray max is 1440 (min) X 1024 (samples per FFT) = 1474560
# Note that there is intentional overlap for better visibility of spectrum features

bigarray = np.zeros(1474560,dtype=complex)
bptr = 0
#gain = 2

hr1 = np.arange(1024, dtype='f')
#print("numpy array type = ",type(hr1[0]))
zeros = np.zeros(1024, dtype='f')

freqLowerExtreme = 0
freqHigherExtreme = 0

print('Read data... this may take a few minutes...')
offset = 0

# Get data from DRF dataset
for i in range(1439): # 1439 gives 1440 bins
    try:
        data = do.read_vector(s + offset, 1024, 'ch0')
        for val in data:
            bigarray[bptr] = val
            bptr += 1

    except IOError: # tried to read DRF data but did not find requsted time slice
        for pad in range(0,1024):
            bigarray[bptr] = 0  # pad this area with zeros (no signal info; show the gap)
            bptr += 1
                   
    # in narrow case, there are 10 samples/sec, so 600 samples = 1 minute
    offset = offset + 600  #  note overlap of the 1024 bins
    if (i % 100 == 0): # progress indicator, marching dots
        print(".",end='')

# create custom color map to simulate gnuradio display on Grape1DRF system
cmap = matplotlib.colors.LinearSegmentedColormap.from_list(" ", ["black","darkgreen","green","yellow","red"])


fig, ax = plt.subplots(2,1, figsize=(14,8)) # plot size, inches x and y
plt.subplot(211)
plt.tight_layout()

plt.yticks(np.arange(-1,1.4,0.2),labels=['-5','-4','-3','-2','-1','0','1','2','3','4','5','6'])
plt.xticks(np.arange(0,744000, 62000), labels=['00','02','04','06','08','10','12','14','16','18','20','22'])

#Create the spectrogram
freqs = plt.specgram(bigarray, NFFT=1024, cmap =cmap)

ax[0].set_ylabel('Doppler Shift (Hz)')
ax[0].set_xlabel('Hours, UTC')

# get info from database for use in plot titles
theStationQS = Station.objects.filter(station_id=stationIDstr)
station_id = theStationQS.values()[0]['id']
station_nickname = theStationQS.values()[0]['nickname']
print("Station name:" + station_nickname)

ax[0].set_title('Grape Narrow Spectrum, Freq. = ' + str(freqList[0]) + " MHz, " + t + ' , Lat. '
                + '{:6.2f}'.format(theLatitude) + ", Long. " + '{:6.2f}'.format(theLongitude) + ' (Grid'
                + maidenheadGrid + ') Station: ' + station_nickname)

print("File loaded")
plt.subplot(212)

plt.margins(x=0)

plt.autoscale(enable=True,axis='y')

abs_amplitude = np.absolute(bigarray)
minute_sample = np.zeros(1440,dtype=float)
minute_pointer = 0
minute_max = 0

# For each minute, find max amplitude in bigarray. Each minute contains 1024 samples.

for sample in range(0,1474559):
    if sample % 1024 == 0:
        minute_sample[minute_pointer] = minute_max
        minute_max = 0
        minute_pointer += 1
    else:
        if abs_amplitude[sample] > minute_max:
            minute_max = abs_amplitude[sample]

ax[1].plot(minute_sample)

plt.xticks(np.arange(0,1560, 120), labels=['00','02','04','06','08','10','12','14','16','18','20','22','24'])

ax[1].set_ylabel('Amplitude, uncalibrated units')
ax[1].set_xlabel('Hours, UTC')
ax[1].set_title('Peak Amplitude by Minute' )
fig.tight_layout()

output_filename =  stationIDstr + '_' + instrumentID + '_' + t + '_' + maidenheadGrid + '.png'
plt.savefig(output_path + '/' + stationIDstr + '_' + instrumentID + '_' + t + '_' + maidenheadGrid + '.png')

print("Saving to database...")
print("stationID",station_id,"instrumentID",instrumentID,"datapath",datapath,"filename",filename)

theObsQS = Observation.objects.filter(station_id=station_id, instrument_id=instrumentID,fileName=filename)

print('obs id:',theObsQS.values()[0]["id"])
obs_id   = theObsQS.values()[0]["id"]
obs_instance = Observation.objects.get(id = obs_id)
obs_instance.plotFile = output_filename
obs_instance.plotPath = output_path
obs_instance.save()

plt.close('all')




