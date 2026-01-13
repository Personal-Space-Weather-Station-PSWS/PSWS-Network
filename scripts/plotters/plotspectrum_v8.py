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

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Django bootstrap to set up environment for Database access
from _bootstrap_django import bootstrap 
bootstrap() 

# Imports necessary modules from PSWS database
from centerfrequencies.models 	import *
from observations.models 	import *
from stations.models 		import *
from instruments.models       	import *
from instrumenttypes.models   	import *

plot_output_path= "/psws/psws/media/plots" # for use on pswsnetwork server
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

# Determine what type of instrument created this dataset.
# This will determine calibration for amplitud plot

instr_instance = Instrument.objects.get(id = instrumentID)
print('Instr.',instr_instance.instrument,'type',instr_instance.instrumenttype_id)
instrtype_instance = InstrumentType.objects.get(id = instr_instance.instrumenttype_id)
instr_type = instrtype_instance.instrumentType
print('Instr type',instr_type,' detected')

print("datapath: ",datapath)
print("filename: ",filename)
dataDir = os.path.join(datapath,filename)
print("data dir: ", dataDir)

plt.style.use('classic') #TODO: replace w/ '_mpl-gallery-nogrid' when testing on server
#plt.style.use('_mpl-gallery-nogrid') 
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
#        print("frequencies: ", freqList)

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
#                print(" val type:",type(val))
                if "ndarray" in  str(type(val)) :   # did DRF return a number or an array?
                    bigarray[bptr] = val[i]
                else:
                    bigarray[bptr] = val
                # i is the frequency from the metadata array
                # bigarray[bptr]= val[i]
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
    plt.grid() # WDE added
    plt.yticks(np.arange(-1,1.4,0.2),labels=['-5','-4','-3','-2','-1','0','1','2','3','4','5','6'])
    plt.xticks(np.arange(0,744000, 62000), labels=['00','02','04','06','08','10','12','14','16','18','20','22'])

    #Create the spectrogram
    print("Plot spectrogram",i, " on axis",2*i)
    freqs = plt.specgram(bigarray, NFFT=1024, cmap =cmap)

    axs[2*i].set_ylabel('Doppler Shift (Hz)')
    axs[2*i].set_xlabel('Hours, UTC')

    # get info from database for use in plot titles
    print("Look for station",stationIDstr)    
    theStationQS = Station.objects.filter(station_id=stationIDstr) # WDE test
    station_id = theStationQS.values()[0]['id']  # WDE test
    station_nickname = theStationQS.values()[0]['nickname']
    
    #station_nickname= "test station" # WDE testing
    print("axis#",i)
    print("Station name: " + station_nickname)

    axs[2*i].set_title('Grape Narrow Spectrum, Freq. = ' + str(frequency) + " MHz, " + t + ' ,\nLat. '
                    + '{:6.2f}'.format(theLatitude) + ", Long. " + '{:6.2f}'.format(theLongitude) + ' (Grid'
                    + maidenheadGrid + ') Station: ' + station_nickname + " Subchannel " + str(i),
                       fontsize=10)

    
    print("File loaded. Frequency: ",freqList[i])

    # subplot is                nrows, ncols, index
    axs[2*i+1] = plt.subplot(freqCount*2,1,(2*i)+2)

    print("Amplitude subplot", freqCount*2, 1 ,(2*i)+2)

    plt.margins(x=0)
    plt.grid()   # WDE added
    plt.autoscale(enable=True,axis='y')

    abs_amplitude = np.absolute(bigarray)
    minute_sample = np.zeros(1440,dtype=float)
    minute_pointer = 0
    minute_maxs = 0
    calib_amplitude = np.zeros(1440) # number of minutes in the 24 hr plot

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
    print(" ")
    print("instr_type: '" + instr_type + "'")

    if instr_type == 'Grape 1 DRF':
       
        for j in range(0,len(minute_sample)-1):
          #  X = (np.abs(minute_sample[j]) - 0.001879 ) / 464. # convert to Vrms using magnitude
            X = (-np.abs(minute_sample[j]) - 0.001879 ) / 464. # convert to Vrms using magnitude
            calib_amplitude[j] = 10. * math.log10((X**2 * 1000.)/50.) # convert to dBm
          #  print(j,minute_sample[j],calib_amplitude[j])
        y_min = calib_amplitude.min()
        y_max = calib_amplitude.max()
        axs[(2*i)+1].plot(calib_amplitude)
        axs[(2*i)+1].set_ylabel('Amplitude, dBm')

    else: # in future, add calculations for calibration of additional instruments here (e.g. rx888)
        y_min = minute_sample.min() - 0.05 * minute_sample.min()
        y_max = minute_sample.max() + 0.05 * minute_sample.max()
        axs[(2*i)+1].plot(minute_sample)
        axs[(2*i)+1].set_ylabel('Amplitude, uncalibrated units')

    print("Plot amplitude",i," on axis",(2*i)+1)
   # axs[(2*i)+1].plot(minute_sample)
    

    plt.xticks(np.arange(0,1560, 120), labels=['00','02','04','06','08','10','12','14','16','18','20','22','24'])

        
    axs[(2*i)+1].set_xlabel('Hours, UTC')
    axs[(2*i)+1].set_title('Peak Amplitude by Minute' ) 
    axs[(2*i)+1].set_ylim(y_min,y_max)
    
fig.tight_layout()
output_filename =  stationIDstr + '_' + instrumentID + '_' + t + '_' + maidenheadGrid + '.png'
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

