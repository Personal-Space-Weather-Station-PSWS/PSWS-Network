# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------

# Imports needed for plotting graphs from fldigi csv files

import datetime

import pytz

import numpy as np
import matplotlib as mpl
from matplotlib import pyplot as plt

from hamsci_psws import geopack,grape1  # from K. Collins et al in github

import matplotlib.colors
from   matplotlib.gridspec import GridSpec

from   pytz import timezone
import numpy as np
import digital_rf as drf

from   datetime import datetime, timedelta
import datetime as dt

import math
import os, tempfile
import maidenhead as mh
import sys, getopt, os, glob, string
import pandas as pd
import xarray as xr
from   tqdm.auto import tqdm
from   scipy.interpolate import interp1d
from   scipy import signal

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

from decimal import Decimal

tqdm.pandas(dynamic_ncols=True)

mpl.rcParams['font.size']        = 16
mpl.rcParams['font.weight']      = 'bold'
mpl.rcParams['axes.labelweight'] = 'bold'
mpl.rcParams['axes.titleweight'] = 'bold'
mpl.rcParams['axes.grid']        = True
mpl.rcParams['grid.linestyle']   = ':'
mpl.rcParams['figure.figsize']   = np.array([15, 8])
mpl.rcParams['axes.xmargin']     = 0

print("Logging")
def writeLog(theMessage):
  #  timestamp = dt.datetime.now(timezone.utc).isoformat()[0:19]
    timestamp = dt.datetime.utcnow().replace(tzinfo=pytz.utc)
    f = open("watchdog.log", "a")
    f.write(str(timestamp) + " " + theMessage + "\n")
    f.close()

target_data_path = '/home/N000015'
target_data_file = '2021-03-29T000000Z_N0000015_G1_FN20mp_FRQ_WWV10.csv'

writeLog("start CSV plotter")

# Prepare variables from supplied arguments

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
            print ("-d YYYY-MM-DD -f filename")

        elif currentArgument in ("-f", "--file"):
            print ("file:",currentValue)
            datapath = currentValue

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
stationIDstr = event_src_path.rsplit('_')[-7] # looking for something of the form N000011
print("StationID=",stationIDstr)
instrumentID = event_src_path.rsplit('_#')[1]
print("InstrumentID=", instrumentID)

#theInstrumentQS = Instrument.objects.filter(id=int(instrumentID))
print("get db observation")
theInstrumentQS = Instrument.objects.get(id = instrumentID)

observation_date = event_src_path[1:18]
print("Obs. Date=",observation_date)
sTime = datetime.strptime(observation_date, '%Y-%m-%dT%H%M%S')
sTime = sTime.replace(tzinfo=pytz.UTC) # make it UTC aware
print("formatted date:",sTime)
freq = event_src_path.rsplit('_')[-3]
freq = freq.rsplit('.')[-2]
print("Freq.=", freq)

if freq  == 'WWV5':
    freq = 5e6
if freq  == 'WWV10':
    freq = 10e6
if freq == 'WWV2p5':
    freq = 2.5e6
if freq == 'WWV15':
    freq = 15e6
if freq == 'WWV20':
    freq = 20e6
if freq == 'WWV25':
    freq = 25e6
if freq  == 'CHU3':
    freq = 3330e3
if freq  == 'CHU7':
    freq = 7850e3
if freq  == 'CHU14':
    freq = 14.67e6
if freq == 'Unknown':
    freq = 0.0
print("computed freq=", freq)


#datapath = event_src_path.rsplit('_#')[0].rsplit('g')[0] #TODO: change 'z' to 'c' when testing on server
#filename = event_src_path.rsplit('_#')[0].rsplit('g')[1] #TODO: change 'z' to 'c' when testing on server
target_data_file = os.path.basename(datapath)
target_data_path = os.path.dirname(datapath)

print("filename=", target_data_file)
print("path=",     target_data_path)

# Determine what type of instrument created this dataset.
# Make sure that this instrument is Grape 1 Legacy (means a CSV file)

instr_instance = Instrument.objects.get(id = instrumentID)
print('Instr.',instr_instance.instrument,'type',instr_instance.instrumenttype_id)
instrtype_instance = InstrumentType.objects.get(id = instr_instance.instrumenttype_id)
instr_type = instrtype_instance.instrumentType
print('Instr type',instr_type,' detected')

#suffix= '.csv'

print("starting")


inventory = grape1.DataInventory(data_path = target_data_path, data_file=target_data_file)
inventory.df

print("inventory")
print(inventory.df)
#print("plot inventory")
#inventory.plot_inventory()
print('set nodes')
nodes = grape1.GrapeNodes(logged_nodes=inventory.logged_nodes)
print('node status')
nodes.status_table()
#print('plot map')
#nodes.plot_map()

# kws  = dict(N=2,Tc_min = (15, 60),btype='bandpass',fs=1.)
filt = grape1.Filter()
filt.plotResponse()

node   = int(stationIDstr[1:len(stationIDstr)])
print("Node:", node)
#sTime  = datetime(2021,3,29, tzinfo=pytz.UTC)
eTime  = sTime + timedelta(days=1)
print("date range:",sTime, eTime)


print("calling Grape1Data",node,freq,sTime,eTime,inventory,nodes)
gd = grape1.Grape1Data(node,freq,sTime,eTime,inventory=inventory,grape_nodes=nodes, data_path= target_data_path, data_file = target_data_file)
print('**********************************')
print(node,freq,sTime,eTime,nodes)
print('inventory=',inventory)

gd.process_data()

gd.show_datasets()

gd.plot_timeSeries(ylims={'Freq':(-5,5)})

ret = gd.plot_timeSeries(['raw','filtered'])
fig = ret['fig']
#fig.savefig('/home/bengelke/nodedata/n8obj_20190524d.png',bbox_inches='tight')
print("******* Plot to",plot_output_path + '.png')

writeLog("save plot for " + plot_output_path)
fig.savefig(plot_output_path + '.png', bbox_inches='tight')
print("update database")
writeLog("Update database")
obs_instance = Observation.objects.get(fileName = target_data_file)
obs_instance.plotPath = os.path.dirname (plot_output_path)
obs_instance.plotFile = os.path.basename(plot_output_path + '.png')

Dfreq = "{:3f}".format(freq/1e6) # Database center freq table is in MHz

writeLog("Look up center freq"  )

print("Look up center freq=",Dfreq)
this_cfid = CenterFrequency.objects.filter(centerFrequency=Dfreq).first().id
writeLog("set center freq in observation")
obs_instance.centerFrequency.add(this_cfid)

obs_instance.save()
print("database update done")
plt.close('all')

