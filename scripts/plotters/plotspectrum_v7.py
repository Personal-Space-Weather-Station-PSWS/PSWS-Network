# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------

# Imports needed for ploting graphs from metadata
import matplotlib.pyplot as plt
import matplotlib.colors
from matplotlib.gridspec import GridSpec
import numpy as np
import digital_rf as drf
from datetime import datetime
import math
import os, tempfile
import maidenhead as mh
import sys, getopt, os

from pytz import timezone

# Imports needed to interact with PSWS database
import django
from django.core.wsgi import get_wsgi_application
from django.db import models

# Sets up envirtonment to host modules from PSWS database
os.environ['DJANGO_SETTINGS_MODULE'] = 'PSWS.PSWS.settings'
application= get_wsgi_application()
django.setup()

# Imports necessary modules from PSWS database
from centerfrequencies.models import *
from observations.models import *
from stations.models import *

plot_output_path= "/home/plots" # for use on pswsnetwork server
#plot_output_path = "C:\\temp"  # test

# Retrieve supplied arg(s)
# Remove the first arg from the list of command line args
argumentList= sys.argv[1:]
print("Arg List: ", argumentList)

# Valid options
options= "hf:p:e:"

# Long options
long_options= ["Help", "theDate", "file"]

try:
    # Parsing args
    arguments, values = getopt.getopt(argumentList, options, long_options)
     
    # Checking each arg
    for currentArgument, currentValue in arguments:
 
        if currentArgument in ("-h", "--Help"):
            print ("-d YYYY-MM-DD -f filewname")

        elif currentArgument in ("-f", "--file"):
            print ("file:",currentValue)
            dataDir = currentValue

        elif currentArgument in ("-p", "--outpath"):
            print("outputPath:",currentValue)
            plot_output_path = currentValue
           
        elif currentArgument in ("-e", "--event"):
            print("event:",currentValue)
            event_src_path = currentValue

except getopt.error as err:
    # Output error. Return w/ error code
    print (str(err))

# Parse event from watchdog
print("event:",event_src_path)
stationIDstr = event_src_path.rsplit('/')[-2]
instrumentID = event_src_path.rsplit('_#')[1]
datapath = event_src_path.rsplit('_#')[0].rsplit('c')[0] #TODO: change 'z' to 'c' when testing on server
filename = event_src_path.rsplit('_#')[0].rsplit('c')[1] #TODO: change 'z' to 'c' when testing on server

# following just for testing
#stationIDstr = 'T000107'
#instrumentID = '117'
#datapath = 'C:\\Users\\engel\\Downloads'
#filename = 'OBS2024-02-19T00-00'
print("datapath: ",datapath)
print("filename: ",filename)
dataDir = os.path.join(datapath,filename)
print("data dir: ", dataDir)

plt.style.use('classic') #TODO: replace w/ '_mpl-gallery-nogrid' when testing on server 
maidenheadGrid= 'EN91' # Default grid

# Plot creation
fig, axs= plt.subplots()

metadata_dir= dataDir + '//ch0//metadata'
print("Looking for metadata at: ", metadata_dir)

# DRF reader creation
do= drf.DigitalRFReader(dataDir)
s, e= do.get_bounds('ch0')

# Date and time of metadata start
t= dataDir[-16:]

# Station declaration
station= dataDir[-27:20]
print("station: ", station)

print("requestDate: ", t)
requestTime= datetime.strptime(t, '%Y-%m-%dT%H-%M')

# Timestamp based in unix time multiplied by 10 (for 10 samples/second)
timestamp= requestTime.replace(tzinfo=timezone('UTC')).timestamp()*10
s= int(timestamp)
print("timestamp: ", s)

# Declaration of Frequencies and Lattitude and Longitude
freqList= [0]
theLattitude= 0
theLongitude= 0

# Retrieve Metadata, if the data exists
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
        freqList = data_dict[key]
        print("frequencies: ", *freqList)

    data_dict = dmr.read(start_idx, start_idx + 2, "lat")
    for key in data_dict.keys():
        theLatitude = data_dict[key]
        print("Latitude: ",theLatitude)
        
    data_dict = dmr.read(start_idx, start_idx + 2, "long")
    for key in data_dict.keys():
        theLongitude = data_dict[key]
        print("Longitude: ",theLongitude)
    
    maidenheadGrid = mh.to_maiden(theLatitude, theLongitude)     

except IOError:
    print("IO Error; metadata not found at " + metadata_dir)

# Loops through all of the frequencies in a given metadata file

freqCount = len(freqList)

# Create all the axes
fig, axs = plt.subplots(nrows=freqCount*2,ncols=1,figsize=(10,5*freqCount)) # plot size, inches x and y
print("# axes created=",len(axs))

for i in range(0,freqCount):
    print("Working on frequency #",i, "  ", freqList[i],"Mhz")
    frequency = freqList[i]
    # The size of bigarray maxs is 1440 (min) x 1024 (samples/FFT) = 1474560
    # Note: there is intentional overlap for better visibility of specturm features
    bigarray = np.zeros(1474560,dtype=complex)
    bptr = 0

    hr1= np.arange(1024, dtype= 'f')
    zeros= np.zeros(1024, dtype= 'f')

    freqLowerExtreme= 0
    freqHigherExtreme= 0

    print("Reading data... this might take a few minutes...")
    offset= 0

    # Retrieve data from DRF dataset
    for j in range(1439):
        try:
            data= do.read_vector(s + offset, 1024, 'ch0')
            
            for val in data:
                if "ndarray" in  str(type(val)) :   # did DRF return a number or an array?
                    bigarray[bptr] = val[i]
                else:
                    bigarray[bptr] = val
                bptr += 1

        # Tried to read DRF data but didn't find requested time slice       
        except IOError:
            for pad in range(0,1024):
                # Pad this area with zeros (no signal info; show the gap)
                bigarray[bptr]= 0
                bptr += 1
        
        # In narrow case, there are 10 samples/sec, so 600 samples = 1 minute
        # Note: Overlap of the 1024 bins
        offset= offset + 600
        # Progress indicator, marching dots
        if (j % 100 == 0):
            print(".", end='')
        
    # Creates new line for ease of console logging
    print()

    # Create custom color map to simulate gnuradio display
    cmap= matplotlib.colors.LinearSegmentedColormap.from_list(" ", ["black", "darkgreen", "green", "yellow", "red"])

    # WDE - moved this outside the main loop, only should be done once
  #  fig, axs = plt.subplots(len(freqList)*2,1, figsize=(14,len(freqList)*3)) # plot size, inches x and y

    axs[2*i] = plt.subplot(freqCount*2,1,(2*i)+1)
    print("Doppler subplot", freqCount*2, 1 ,(2*i)+1)
    plt.tight_layout()

    plt.yticks(np.arange(-1,1.4,0.2),labels=['-5','-4','-3','-2','-1','0','1','2','3','4','5','6'])
    plt.xticks(np.arange(0,744000, 62000), labels=['00','02','04','06','08','10','12','14','16','18','20','22'])

    #Create the spectrogram
    print("Plot spectrogram",i, " on axis",2*i)
    freqs = plt.specgram(bigarray, NFFT=1024, cmap =cmap)

    axs[2*i].set_ylabel('Doppler Shift (Hz)')
    axs[2*i].set_xlabel('Hours, UTC')

    # get info from database for use in plot titles    
    theStationQS = Station.objects.filter(station_id=stationIDstr) # WDE test
    station_id = theStationQS.values()[0]['id']  # WDE test
    station_nickname = theStationQS.values()[0]['nickname']
    

    print("axis#",i)
    print("Station name: " + station_nickname)

    axs[2*i].set_title('Grape Narrow Spectrum, Freq. = ' + str(frequency) + " MHz, " + t + ' ,\nLat. '
                    + '{:6.2f}'.format(theLatitude) + ", Long. " + '{:6.2f}'.format(theLongitude) + ' (Grid'
                    + maidenheadGrid + ') Station: ' + station_nickname + " Subchannel " + str(i),
                       fontsize=10)

    plt.grid() # put grid into spectrum plot    
    print("File loaded. Frequency: ",freqList[i])

    # subplot is                nrows, ncols, index
    axs[2*i+1] = plt.subplot(freqCount*2,1,(2*i)+2)

    print("Amplitude subplot", freqCount*2, 1 ,(2*i)+2)

    plt.margins(x=0)

    plt.autoscale(enable=True,axis='y')

    abs_amplitude = np.absolute(bigarray)
    minute_sample = np.zeros(1440,dtype=float)
    minute_pointer = 0
    minute_maxs = 0

    # For each minute, find maxs amplitude in bigarray. Each minute contains 1024 samples.

    for sample in range(0,1474559):
        if sample % 1024 == 0:
            minute_sample[minute_pointer] = minute_maxs
            
            minute_maxs = 0
            minute_pointer += 1
            
        else:
            if abs_amplitude[sample] > minute_maxs:
                minute_maxs = abs_amplitude[sample]

    print("i",2*i,"minute sample", minute_sample)

    print("Plot amplitude",i," on axis",(2*i)+1)
    axs[(2*i)+1].plot(minute_sample)

    plt.xticks(np.arange(0,1560, 120), labels=['00','02','04','06','08','10','12','14','16','18','20','22','24'])
    plt.grid() # put grid into amplitude chart
    axs[(2*i)+1].set_ylabel('Amplitude, uncalibrated units')
    axs[(2*i)+1].set_xlabel('Hours, UTC')
    axs[(2*i)+1].set_title('Peak Amplitude by Minute' ) 
  
    
fig.tight_layout()
output_filename =  stationIDstr + '_' + instrumentID + '_' + t + '_' + maidenheadGrid + '.png'
plt.grid()
plt.savefig(plot_output_path + '/' + stationIDstr + '_' + instrumentID + '_' + t + '_' + maidenheadGrid + '.png')

print("Saving to database...")
print("stationID",station_id,"instrumentID",instrumentID,"datapath",plot_output_path ,"filename","'"+filename+"'")
o = filename.rsplit("/",2)
filename = o[-1]
print("filename:",filename)
# remove database update for testing
theObsQS = Observation.objects.filter(station_id=station_id, instrument_id=instrumentID,fileName=filename)

print('obs id:',theObsQS.values()[0]["id"])
obs_id   = theObsQS.values()[0]["id"]
obs_instance = Observation.objects.get(id = obs_id)
obs_instance.plotFile = output_filename
obs_instance.plotPath = plot_output_path
obs_instance.save()

plt.close('all')
