"""
grape1.py

Code for analyzing and visualizing HamSCI Grape1 Personal Space Weather Station
Observations.

Contributions by:
    Nathaniel Frissell W2NAF
    Kristina Collins KD8OXT
    Aidan Montare KB3UMD
    David Kazdan AD8Y
    John Gibbons N8OBJ
    Bob Benedict KD8CGH

    July 2022
"""

import os
import sys
import glob
import string
letters = string.ascii_lowercase

import datetime
import pytz

import numpy as np
import pandas as pd
import xarray as xr

import plotly.express as px
import plotly.graph_objects as go

import matplotlib as mpl
import matplotlib.pyplot as plt

from tqdm.auto import tqdm
tqdm.pandas(dynamic_ncols=True)

from scipy.interpolate import interp1d
from scipy import signal

from . import locator
#import locator, solar, goes
#import gen_lib as gl
from . import solar
from . import goes
from . import gen_lib as gl

prm_dict = {}

pkey = 'Freq'
prm_dict[pkey] = {}
prm_dict[pkey]['label'] = 'Doppler Shift [Hz]'
prm_dict[pkey]['vmin']  = -0.5
prm_dict[pkey]['vmax']  =  0.5
prm_dict[pkey]['cmap']  = 'bwr_r'
prm_dict[pkey]['title'] = 'Grape Doppler Shift'

pkey = 'Vpk'
prm_dict[pkey] = {}
prm_dict[pkey]['label'] = 'Peak Voltage [V]'

pkey = 'Power_dB'
prm_dict[pkey] = {}
prm_dict[pkey]['label'] = 'Received Power [dB]'
prm_dict[pkey]['title'] = 'Grape Received Power'

pkey = 'LMT'
prm_dict[pkey] = {}
prm_dict[pkey]['label'] = 'Mean Solar Time'

pkey = 'LMT_Hour'
prm_dict[pkey] = {}
prm_dict[pkey]['label'] = 'Solar Mean Time [Hours]'

pkey = 'LMT_Date'
prm_dict[pkey] = {}
prm_dict[pkey]['label'] = 'Date'

pkey = 'UTC_Hour'
prm_dict[pkey] = {}
prm_dict[pkey]['label'] = 'UTC [Hours]'

pkey = 'UTC_Date'
prm_dict[pkey] = {}
prm_dict[pkey]['label'] = 'Date'

pkey = 'lon'
prm_dict[pkey] = {}
prm_dict[pkey]['label'] = 'Longitude'

pkey = 'lat'
prm_dict[pkey] = {}
prm_dict[pkey]['label'] = 'Latitude'

class DataInventory(object):
    def __init__(self,nodes=None,G=None,freq=None,sTime=None,eTime=None,
                    data_path='/home/bengelke/data',data_file='data',suffix='.csv'):
        """
        Create an inventory of availble grape1 data in the data_path.
        Inventory will be dataframe df attached to DataInventory object.

        data_path: location of grape1 data
        suffix:    suffix of data files. Defaults to '.csv'
	"""
        print("starting,data_path = data_path")
      #  data_path = '/home/bengelke/data'
        # Load filenames and create a dataframe.
        fpaths = glob.glob(os.path.join(data_path,'*'+suffix))
      #  fpaths = glob.glob('/home/bengelke/data/*.csv')
        print("fpaths",fpaths)
        bnames = [os.path.basename(fpath) for fpath in fpaths]
       # df = pd.DataFrame({'Filename':bnames})
        df = pd.DataFrame({'Filename':[data_file]}) # specify a single file
        print("df:",df)
        # Parse filenames into useful information and place into dataframe.
        df['Filename']   = df['Filename'].astype('string')
        df2              = df['Filename'].str.split('_', expand=True)
        df2.columns      =['Datetime', 'Node', 'G', 'Grid Square', 'FRQ', 'Frequency']
        df2              = df2.drop(columns=['FRQ']) # no information in this columnn
        df2["Frequency"] = df2["Frequency"].str.strip(suffix)

        # # Parse Grid Squares
        # lat,lon = locator.gridsquare2latlon(df2['Grid Square'])
        # df2['Latitude']  = lat
        # df2['Longitude'] = lon

        df               = pd.concat([df2, df], axis = 1) # concatenate dataframes horizontally
        df['Datetime']   = pd.to_datetime(df['Datetime']) # cast to datetime
        df['Node']       = df['Node'].str.strip("N")                   # Ditch the leading N on the node numbers
        df['Node']       = df['Node'].astype(str).astype(int)          # Cast node number to int
        df               = df[~df['Frequency'].str.contains('G1')]     # discarding files with naming errors

        # Convert frequency abbreviations to numbers:
        
        df.loc[df['Frequency'] == 'WWV5',    'Frequency'] = '5e6' # WDE changed to strings
        df.loc[df['Frequency'] == 'WWV10',   'Frequency'] = '10e6'
        df.loc[df['Frequency'] == 'WWV2p5',  'Frequency'] = '2.5e6'
        df.loc[df['Frequency'] == 'WWV15',   'Frequency'] = '15e6'
        df.loc[df['Frequency'] == 'WWV20',   'Frequency'] = '20e6'
        df.loc[df['Frequency'] == 'WWV25',   'Frequency'] = '25e6'
        df.loc[df['Frequency'] == 'CHU3',    'Frequency'] = '3330e3'
        df.loc[df['Frequency'] == 'CHU7',    'Frequency'] = '7850e3'
        df.loc[df['Frequency'] == 'CHU14',   'Frequency'] = '14.67e6'
        df.loc[df['Frequency'] == 'Unknown', 'Frequency'] = '0'

        df['Frequency'] = df['Frequency'].astype(float) # WDE force this to float

        # Sort by Datetime
        df = df.sort_values(['Datetime','Frequency','Node']).copy()
        
        # Save dataframe to object
        self.df_unfiltered = df

        df = self.filter(nodes=nodes,G=G,freq=freq,sTime=sTime,eTime=eTime)

    def filter(self,nodes=None,G=None,freq=None,sTime=None,eTime=None):
        """
        Filter data by parameters. The filtered results will be returned
        and stored in self.df. Unfiltered results will always be available
        in self.df_unfiltered.

        Parameters
        ----------
        nodes:  node numbers (int or list of ints)
        G:      type of receiving station (string or list of strings)
		        G – Grape (Low Cost Platform)
		    	1 – Generation 1 (has 1 receiver)
		    	2 – Generation 2 (has 4 receivers)
		        T – Tangerine (High Performance Platform)
		    	1 – Generation 1
		     	2 – Generation 2
		        S – Standard / Commercial (Amateur) Hardware (details in Metadata)
		        U – User Custom Hardware (details in Metadata)
		        N – No radio collection – instrument(s) only – defaults to N0
        freq:   frequency in Hz (float or list of floats)
        sTime:  UTC starting time of observations (datetime object)
        eTime:  UTC ending time of observations (datetime object)

        """

        df = self.df_unfiltered.copy()

        if nodes is not None:
            nodes   = gl.get_iterable(nodes)
            tf      = df['Node'].isin(nodes)
            df      = df[tf].copy()

        if G is not None:
            G       = gl.get_iterable(G)
            tf      = df['G'].isin(G)
            df      = df[tf].copy()

        if freq is not None:
            freq    = gl.get_iterable(freq)
            tf      = df['Frequency'].isin(freq)
            df      = df[tf].copy()

        if sTime is not None:
            # Return files that start a day early,
            # otherwise you may not get all of the files you need.
            sTime  -= datetime.timedelta(days=1)   

            tf      = df['Datetime'] >= sTime
            df      = df[tf].copy()

        if eTime is not None:
            # Return files that end a day after eTime,
            # otherwise you may not get all of the files you need.
            eTime  += datetime.timedelta(days=1)   

            tf      = df['Datetime'] < eTime
            df      = df[tf].copy()

        self.df = df

        # List of logged nodes during the period of interest, for sorting:
        logged_nodes = df["Node"].unique().tolist()
        logged_nodes.sort()
        self.logged_nodes = logged_nodes

        return df

    def get_nodes(self):
        """
        Return a list of all of the unique node numbers in the inventory.
        """
        nodes = self.df['Node'].unique().tolist()
        return nodes
    
    def plot_inventory(self,html_out='inventory.html'):
        """
        Generate a plot of the data inventory using plotly.

        html_out: Filename of html-version of data inventory plot.
        """
        # We can create a Data Inventory (Gantt chart) showing when different stations were active. 
        invt         = self.df.copy()
        logged_nodes = self.logged_nodes
        
        invt.set_index('Node')
        invt = invt.drop(columns=['G', 'Grid Square'])
        invt['EndTime'] = invt['Datetime']+ datetime.timedelta(days=1) # create an end
        invt['Filename'].str.strip('FRQ_')

        fig = px.timeline(invt, x_start="Datetime", x_end="EndTime", y="Node", color="Frequency", category_orders={"Node": logged_nodes})
        fig.update_yaxes(type='category')
        fig.update_annotations(text = "Filename", clicktoshow='on')
        
        fig.update_layout({
            'plot_bgcolor': 'rgba(0, 0, 0, 0)',
            'paper_bgcolor': 'rgba(0, 0, 0, 0)',
            'font_size': mpl.rcParams['font.size']
        })
        
        fig.show()
        
        if html_out:
            fig.write_html(html_out, include_plotlyjs="cdn")

class GrapeNodes(object):
    def __init__(self,fpath='nodelist.csv',logged_nodes=None):
        """
        Create an object with information about known Grape1 nodes from a nodelist.csv.

        fpath:        path to nodelist.csv
        logged_nodes: list of nodes we have data for. This can be obtained from DataInventory.logged_nodes.
        """
        # Read in node list:
        print('READ IN NODE LIST')
        nodes_df = pd.read_csv(fpath)
        nodes_df = nodes_df.rename(columns={'Node #': 'Node_Number'})
        nodes_df = nodes_df.set_index('Node_Number')
        
        self.nodes_df = nodes_df

        
        if logged_nodes:
            nodes_df = self.update_status(logged_nodes)
        
    def update_status(self,logged_nodes):
        """
        Updates the nodes_df dataframe with with information regarding which nodes we have data from.

        logged_nodes: list of nodes we have data for. This can be obtained from DataInventory.logged_nodes.
        """
        nodes_df = self.nodes_df
        
        nodes_df['Status'] = np.where((nodes_df.index.isin(logged_nodes)), "Data logged", "No data logged")
        self.nodes_df = nodes_df
        return nodes_df
    
    def status_table(self):
        """
        Returns the nodes_df data frame with nodes that we have data for highlighted in green.
        """
        # Highlight rows in green for stations that we have data from.
        nodes_df = self.nodes_df.copy()
        color    = (nodes_df['Status'] == 'Data logged').map({True: 'background-color: palegreen', False: ''})
        nodes_df = nodes_df.style.apply(lambda s: color)
        return nodes_df
    
    def plot_map(self,color="Status",projection='albers usa',
            width=1200,height=900):
        """
        Use plotly to generate a map of Grape1 nodes.
        """
        nodes_df = self.nodes_df
        # Map nodes:
        fig = px.scatter_geo(nodes_df, "Latitude", "Longitude",
                             color=color, # which column to use to set the color of markers
                             hover_name=nodes_df["Callsign"], # column added to hover information
                             projection = projection,
                             width = width, height = height,
                             )
        fig.show()

class Filter(object):
    def __init__(self,N=6,Tc_min = 3.3333,btype='low',fs=1.):
        """
        Generate a digital filter that can be applied to the data.

        This routine uses the scipy.signal.butter Butterworth filter.

        Parameters
        ----------
        N:      Filter order.
        Tc_min: Cuttoff in minutes. Scalar value for 'low' and 'high'
                filter btypes; 2-element iterable for 'bandpass' and 
                'bandstop' filter btypes.
        fs:     Sampling frequency of the digital system in samples/sec.
        """
        Wn     = (1./(np.array(Tc_min)*60.))
        
        if np.size(Wn) == 2:
            Wn = Wn[::-1]
            
        #Wn    = (1000, 5000)    # 3 dB Cutoff Frequency in Hz
               # Choose 'bandpass' or 'bandstop'

        b, a = signal.butter(N, Wn, btype, fs=fs)
        
        self.fs = fs
        self.Wn = Wn
        self.a  = a
        self.b  = b
        
    def filter_data(self,data):
        """
        Apply the filter using scipy.signal.filtfilt to data.

        data: Vector of data to be filtered.
        """
        try:
            filtered = signal.filtfilt(self.b,self.a,data)
        except Exception as err:
            print('Filter error... returning NaNs.')
            print('   Error: {!s}'.format(err))
            filtered = data*np.nan

        return filtered
    
    def plotResponse(self):
        """
        Plot the magnitude and phase response of the filter.
        """
        fs = self.fs
        Wn = self.Wn
        a  = self.a
        b  = self.b
        
        w, h = signal.freqz(b, a,worN=2**16)
        f = (fs/2)*(w/(np.pi))        
        
        plt.figure(figsize=(12,8))
        plt.subplot(211)
        plt.plot(f, 20 * np.log10(abs(h)))
        plt.xscale('log')
        plt.title('Butterworth Filter Frequency Response')
        plt.xlabel('Frequency [Hz]')
        plt.ylabel('Amplitude [dB]')
        plt.grid(which='both', axis='both')
        if np.size(Wn) == 1:
            plt.axvline(Wn, color='green')    # cutoff frequency
        else:            
            plt.axvline(Wn[0], color='green') # cutoff frequency
            plt.axvline(Wn[1], color='green') # cutoff frequency

        plt.ylim(-30,0)

        plt.subplot(212)
        plt.plot(f, np.unwrap(np.angle(h)))
        plt.xscale('log')
        plt.title('Butterworth Filter Phase Response')
        plt.xlabel('Frequency [Hz]')
        plt.ylabel('Phase [rad]')
        plt.grid(which='both', axis='both')
        if np.size(Wn) == 1:
            plt.axvline(Wn, color='green')    # cutoff frequency
        else:            
            plt.axvline(Wn[0], color='green') # cutoff frequency
            plt.axvline(Wn[1], color='green') # cutoff frequency

        plt.tight_layout()

class Grape1Data(object):
    def __init__(self,node=None,freq=None,sTime=None,eTime=None,data_path='data',data_file='data',
                 lat=None,lon=None,call_sign=None,
                 solar_lat=None,solar_lon=None,
                 inventory=None,grape_nodes=None,
                 data=None,meta=None):

        if data is None and meta is None:
            self.__load_raw(node,freq,sTime,eTime=eTime,data_path=data_path,
                     lat=lat,lon=lon,call_sign=call_sign,solar_lat=solar_lat,solar_lon=solar_lon,
                     inventory=inventory,grape_nodes=grape_nodes)
        else:
            self.data = data
            self.meta = meta
        
    def __load_raw(self,node,freq,sTime,eTime,data_path,
                 lat,lon,call_sign,solar_lat,solar_lon,inventory,grape_nodes):
        
        if inventory is None:
            inventory = DataInventory(data_path=data_path)
        
        # Make temporary copy of dataframe.
        dft   = inventory.df.copy()

        # Select rows with selected frequency
        tf    = dft['Frequency'] == freq
        dft   = dft[tf].copy()
        
        # Select rows matching node number.
        tf    = dft['Node'] == node
        dft   = dft[tf].copy()

        if sTime is None:
            sTime = min(dft['Datetime'])

        if eTime is None:
            eTime = max(dft['Datetime'])        

        # Expand time range of loading files, or you might miss
        # files you need. Strict time limits are applied later in this
        # routine after the data has been loaded.
        sTime_load  = sTime - datetime.timedelta(days=1)
        eTime_load  = eTime + datetime.timedelta(days=1)

        # Select rows matching time range.
        tf    = np.logical_and(dft['Datetime'] >= sTime_load, dft['Datetime'] < eTime_load)
        dft   = dft[tf].copy()
        dft   = dft.sort_values('Datetime')

        # Load data from every data file available for node/frequency/date range.
        df_raw = []
        for rinx,row in tqdm(dft.iterrows(),total=len(dft),dynamic_ncols=True,desc='Loading Raw Data'):
            fname = row['Filename']
            fpath = os.path.join(data_path,fname)

            # Get metadata header.
            with open(fpath,'r') as fl:
                lines = fl.readlines()

            md_list = []
            for line in lines:
                lst = line.lstrip().strip('\n')
                if lst[0] == '#':
                    md_list.append(lst)

                # Get call sign from file metadata if not specified.
                if lst.startswith('# Callsign'):
                    if call_sign is None:
                        call_sign = lst.split()[-1].upper()

                if lat is None or lon is None:
                    if lst.startswith('# Lat, Long, Elv'):
                        tmp = lst[26:].split(',')
                        lat = float(tmp[0])
                        lon = float(tmp[1])

            df_load = pd.read_csv(fpath, comment = '#', parse_dates=[0])
            if len(df_load) == 0: continue

            # Remove the center frequency offset from the frequency column.
            
            df_load['Freq'] = df_load['Freq'].astype(float)
            print('freq type=',type(freq))
            freq = float(freq)
            df_load['Freq'] = df_load['Freq']-freq
            df_raw.append(df_load)

        df_raw  = pd.concat(df_raw,ignore_index=True)
        df_raw  = df_raw.sort_values('UTC')

        # Enforce sTime/eTime
        tf      = np.logical_and(df_raw['UTC'] >= sTime, df_raw['UTC'] < eTime)
        df_raw  = df_raw[tf].copy()
     
        # Generate a label for each Node
        if (call_sign is None) and (grape_nodes is not None):
            if node in grape_nodes.nodes_df.index: # Check to see if node is in current node list. If not, return ''
                call_sign = grape_nodes.nodes_df.loc[node,'Callsign']
            else:
                call_sign = ''
        else:
            call_sign = ''
        
        # Get latitude and longitude
        if (lat is None) and (grape_nodes is not None):
            if node in grape_nodes.nodes_df.index:
                lat = grape_nodes.nodes_df.loc[node,'Latitude']
        
        if (lon is None) and (grape_nodes is not None):
            if node in grape_nodes.nodes_df.index:
                lon = grape_nodes.nodes_df.loc[node,'Longitude']

        if solar_lat is None:
            solar_lat = lat

        if solar_lon is None:
            solar_lon = lon

        # Store data into dictionaries.
        data = {}
        data['raw']          = {}
        data['raw']['df']    = df_raw
        data['raw']['label'] = 'Raw Data'
        self.data = data
        
        label     = '{:0.1f} MHz N{:07d} {!s}'.format(freq/1e6,node,call_sign)

        meta = {}
        meta['label']       = label
        meta['freq']        = freq
        meta['node']        = node
        meta['call_sign']   = call_sign
        meta['lat']         = lat
        meta['lon']         = lon
        meta['solar_lat']   = solar_lat
        meta['solar_lon']   = solar_lon
        self.meta      = meta

    def process_data(self,profile='standard'):
        tic_0 = datetime.datetime.now()
        print('Processing data using "{!s}" profile...'.format(profile))
        print('')
        if profile == 'standard':
            print('Computing Solar Local Time on raw data...')
            tic = datetime.datetime.now()
            self.calculate_solar_time('raw')
            toc = datetime.datetime.now()
            print('  Solar Time Computation Time: {!s}'.format(toc-tic))
        
            resample_rate = datetime.timedelta(seconds=1)
            filter_order  = 6
            Tc_min        = 3.3333
            btype         = 'low'

            print('Resampling data with {!s} second cadence...'.format(resample_rate.total_seconds()))
            tic = datetime.datetime.now()
            self.resample_data(resample_rate=resample_rate,
                              data_set_in='raw',data_set_out='resampled')
            toc = datetime.datetime.now()
            print('  Resampling Time: {!s}'.format(toc-tic))

            print('Computing Solar Local Time on resampled...')
            tic = datetime.datetime.now()
            self.calculate_solar_time('resampled')
            toc = datetime.datetime.now()
            print('  Solar Time Computation Time: {!s}'.format(toc-tic))
            
            # Convert Vpk to Power_dB
            print('dB Conversion')
            tic = datetime.datetime.now()
            self.data['resampled']['df']['Power_dB'] = 20*np.log10( self.data['resampled']['df']['Vpk'])
            toc = datetime.datetime.now()
            print('  dB Conversion Time: {!s}'.format(toc-tic))
            
            print('Filtering data with {!s} minute low-pass Butterworth filter...'.format(Tc_min))
            tic = datetime.datetime.now()
            self.filter_data(N=filter_order,Tc_min=Tc_min,btype=btype)
            toc = datetime.datetime.now()
            print('  Filtering Time: {!s}'.format(toc-tic))

        elif profile == '5min_mean':
            data_set_in = 'raw'
            data_set    = 'resampled'
            xkeys       = ['LMT','UTC']
            params      = ['Freq','Power_dB']

            resample_rate = datetime.timedelta(minutes=5)
            print('Resampling data with {!s} minute cadence...'.format(resample_rate.total_seconds()/60.))
            tic = datetime.datetime.now()
            self.resample_data(resample_rate=resample_rate,method='mean',
                              data_set_in=data_set_in,data_set_out=data_set)
            toc = datetime.datetime.now()
            print('  Resampling Time: {!s}'.format(toc-tic))
            print()

            print('Computing Solar Local Time on resampled...')
            tic = datetime.datetime.now()
            self.calculate_solar_time(data_set)
            toc = datetime.datetime.now()
            print('  Solar Time Computation Time: {!s}'.format(toc-tic))
            print()

            # Convert Vpk to Power_dB
            print('dB Conversion')
            tic = datetime.datetime.now()
            self.data[data_set]['df']['Power_dB'] = 20*np.log10( self.data[data_set]['df']['Vpk'])
            toc = datetime.datetime.now()
            print('  dB Conversion Time: {!s}'.format(toc-tic))
            print()

            for xkey in xkeys:
                for param in params:
                    print('Processing: {!s} - {!s}'.format(xkey,param))
                    print('Compute Time-Date-Parameter (TDP) Array')
                    tic = datetime.datetime.now()
                    tdp = self.calculate_timeDateParameter_array(data_set,param,xkey=xkey)
                    toc = datetime.datetime.now()
                    print('  Time-Date-Parameter Time: {!s}'.format(toc-tic))
                    print()

                    tdp_key = self.get_tdp_key(param,xkey)
                    self.data[data_set][tdp_key] = tdp

        toc_0 = datetime.datetime.now()
        print('')
        print('Total Processing Time: {!s}'.format(toc_0-tic_0))
    
    def resample_data(self,resample_rate,on='UTC',method='linear_interp',
                          data_set_in='raw',data_set_out='resampled'):
        
        df   = self.data[data_set_in]['df'].copy()

        if len(df) == 0:
            rs_df = df.copy()
        else:
            # Create the list of datetimes that we want to resample to.
            # Find the start and end times of the array.
            sTime = df['UTC'].min()
            eTime = df['UTC'].max()

            tzinfo= sTime.tzinfo

            # Break
            sYr  = sTime.year
            sMon = sTime.month
            sDy  = sTime.day
            sHr  = sTime.hour
            sMin = sTime.minute
            sSec = sTime.second
            resample_sTime = datetime.datetime(sYr,sMon,sDy,sHr,sMin,sSec,tzinfo=tzinfo)

            eYr  = eTime.year
            eMon = eTime.month
            eDy  = eTime.day
            eHr  = eTime.hour
            eMin = eTime.minute
            eSec = eTime.second
            resample_eTime = datetime.datetime(eYr,eMon,eDy,eHr,eMin,eSec,tzinfo=tzinfo)

            # Remove LMT column if it exists because it cannot be resampled.
            if 'LMT' in df.keys():
                df = df.drop('LMT',axis=1)

            cols        = df.keys()
            df          = df.set_index(on) # Need to make UTC column index for interpolation to work.
            df          = df.drop_duplicates()

            df          = df[~df.index.duplicated(keep='first')] # Make sure there are no duplicated indices.

            rs_df       = df.resample(resample_rate,origin=resample_sTime)
            if method == 'mean': 
                rs_df = rs_df.mean()
            else:
                rs_df = rs_df.interpolate(method='linear')

            rs_df       = rs_df.copy()
            rs_df[on]   = rs_df.index
            rs_df.index = np.arange(len(rs_df)) 

            # Put Columns back in original order.
            rs_df       = rs_df[cols].copy()
        
        tmp          = {}
        tmp['df']    = rs_df
        tmp['label'] = 'Resampled Data (dt = {!s} s)'.format(resample_rate.total_seconds())
        tmp['Ts']    = resample_rate.total_seconds()
        self.data[data_set_out] = tmp

    def filter_data(self,N,Tc_min,btype,
                    data_set_in='resampled',data_set_out='filtered',
                    params=['Freq','Vpk','Power_dB']):
        
        df     = self.data[data_set_in]['df'].copy()

        # Get sample rate of data set.
        Ts     = self.data[data_set_in].get('Ts')
        if Ts is None:
            Ts_arr = np.unique(np.diff(df['UTC']))
            if len(Ts_arr) != 1:
                raise Exception("{!s} is not evenly sampled. Cannot apply filter.".format(data_set_in))
            Ts   = (Ts_arr[0]).total_seconds()

        # Convert sample rate to sampling frequency.
        fs   = 1./Ts

        filt = Filter(N=N,Tc_min=Tc_min,btype=btype,fs=fs)
        
        for param in params:
            if param not in df.keys():
                continue
            df[param] = filt.filter_data(df[param])
        
        tmp          = {}
        tmp['df']    = df
        tmp['label'] = 'Butterworth Filtered Data\n(N={!s}, Tc={!s} min, Type: {!s})'.format(N, Tc_min, btype)
        self.data[data_set_out] = tmp                            

    def calculate_solar_time(self,data_set,solar_lon=None):
        if solar_lon is None:
            solar_lon = self.meta.get('solar_lon')
        else:
            self.meta['solar_lon'] = solar_lon

        df = self.data.get(data_set)['df']
        df['LMT'] = df['UTC'].progress_apply(solar.solar_time,lon=solar_lon)

        # Set columns so UTC and LMT lead.
        keys = list(df.keys())
        keys.remove('UTC')
        keys.remove('LMT')
        keys = ['UTC','LMT'] + keys
        df   = df[keys]
        self.data[data_set]['df'] = df

    def calculate_timeDateParameter_array(self,data_set,param='Freq',xkey='LMT'):
        df          = self.data[data_set]['df']
        time_vec    = df[xkey]

        # Calculate bin size.
        dt_hr       = (time_vec.diff().mean().total_seconds())/3600.
        hour_bins   = np.arange(0,24+dt_hr,dt_hr)

        print('Splitting {!s} into dates...'.format(xkey))
        dates       = time_vec.progress_apply(gl.datetime2date)
        date_bins   = list(set(dates))
        date_bins.sort()
        date_bins   = np.array(date_bins)

        print('Splitting {!s} into decimal hours...'.format(xkey))
        hours       = time_vec.progress_apply(gl.decimal_hours)

        # Rearrange Data into a 2D Array
        print('Filling timeDateParameter Array...')
        tdp_arr = np.zeros( (len(date_bins), len(hour_bins)) )*np.nan
        for rinx, row in tqdm(df.iterrows(),total=len(df),dynamic_ncols=True):
            val         = row[param]
            date_inx    = np.where(dates.loc[rinx] == date_bins)[0][0]
            t_bin_inx   = np.digitize(hours.loc[rinx],hour_bins)

            tdp_arr[date_inx,t_bin_inx] = val

        # Put array into xarray.
        xr_xkey = '{!s}_Date'.format(xkey)
        xr_ykey = '{!s}_Hour'.format(xkey)

        crds    = {}
        crds[xr_xkey]	= date_bins
        crds[xr_ykey]   = hour_bins
        tdp_da          = xr.DataArray(tdp_arr,crds,dims=[xr_xkey,xr_ykey])

        tdp_key         = self.get_tdp_key(param,xkey)

        # Save back to object
        self.data[data_set][tdp_key] = tdp_da

        return tdp_da

    def get_tdp_key(self,param,xkey):
        tdp_key = 'tdp_{!s}_{!s}'.format(param,xkey)
        return tdp_key

    def show_datasets(self):
        keys        = []
        datasets    = []
        for key,dct in self.data.items():
            keys.append(key)

            tmp  = {}
            tmp['label'] = dct.get('label')

            datasets.append(tmp)
        
        datasets = pd.DataFrame(datasets,index=keys)
        return datasets
        
    def plot_timeSeries(self,data_sets=['raw'],
                        sTime=None,eTime=None,
                        xkey='UTC',params=['Freq','Vpk','Power_dB'],
                        ylims = {},
                        plot_kws = [{'ls':'','marker':'.'},{}],
                        overlayTerminator=True,
                        solar_lat=None,solar_lon=None,
                        fig_width=15,panel_height=6):
        
        data_sets = gl.get_iterable(data_sets)
        
        df      = self.data[data_sets[0]]['df']
        if sTime is None:
            sTime = min(df[xkey])
            
        if eTime is None:
            eTime = max(df[xkey])
        
        # Make sure we have the requested parameters.
        params = gl.get_iterable(params)
        params_good = []
        for param in params:
            if param in df.keys():
                params_good.append(param)
        params = params_good
        
        # Start plotting
        ncols   = 1
        nrows   = len(params)
        figsize = (fig_width, nrows*panel_height)
        
        fig = plt.figure(figsize=figsize)       
        axs = []
        for plt_inx,param in enumerate(params):
            ax  = fig.add_subplot(nrows,ncols,plt_inx+1)
            axs.append(ax)

            if overlayTerminator:
                solar_lat = self.meta.get('solar_lat',solar_lat)
                solar_lon = self.meta.get('solar_lon',solar_lon)
                if (solar_lat is not None) and (solar_lon is not None):
                    solar.add_terminator(sTime,eTime,solar_lat,solar_lon,ax,xkey=xkey)
                else:
                    print('Error: Need to provide solar_lat and solar_lon to overlay solar terminator.')

            ax.set_xlim(sTime,eTime)
            if plt_inx != nrows-1:
                ax.set_xticklabels('')
            else:
                fig.autofmt_xdate()
                xprmd  = prm_dict.get(xkey,{})
                xlabel = xprmd.get('label',xkey)
                ax.set_xlabel(xlabel)

            yprmd  = prm_dict.get(param,{})
            ylabel = yprmd.get('label',yprmd)
            ax.set_ylabel(ylabel)
            ylim = ylims.get(param,None)
            if ylim is not None:
                ax.set_ylim(ylim)

            if plt_inx == 0:
                ax.set_title(self.meta.get('label',''))
            ax.set_title('({!s})'.format(letters[plt_inx]),loc='left')
           
        for ds_inx,data_set in enumerate(data_sets):
            for plt_inx,param in enumerate(params):
                ax = axs[plt_inx]
                
                df  = self.data[data_set]['df']
                xx  = df[xkey]
                yy  = df[param]
                
                label   = self.data[data_set].get('label','')
                plot_kw = plot_kws[ds_inx]
                ax.plot(xx,yy,label=label,**plot_kw)

        for plt_inx,param in enumerate(params):
            ax = axs[plt_inx]
            ax.legend(loc='upper right',fontsize='small')
        
        fig.tight_layout()

        return {'fig':fig}

    def plot_timeDateParameter(self,data_set,params=['Freq','Power_dB'],xkey='LMT',
            fig_width=15,panel_height=6):

        # Start plotting
        ncols   = 1
        nrows   = len(params)
        figsize = (fig_width, nrows*panel_height)
        
        fig = plt.figure(figsize=figsize)       
        axs = []
        for plt_inx,param in enumerate(params):
            tdp_key = self.get_tdp_key(param,xkey)
            tdp = self.data[data_set][tdp_key]

            ax  = fig.add_subplot(nrows,ncols,plt_inx+1)
            axs.append(ax)

            xr_xkey = '{!s}_Date'.format(xkey)
            xprmd   = prm_dict.get(xr_xkey)
            xlabel  = xprmd.get('label')

            xr_ykey = '{!s}_Hour'.format(xkey)
            yprmd   = prm_dict.get(xr_ykey)
            ylabel  = yprmd.get('label')

            prmd = prm_dict.get(param)
            vmin = prmd.get('vmin')
            vmax = prmd.get('vmax')
            cmap = prmd.get('cmap')
            plbl = prmd.get('label')

            cbar_kwargs = {}
            cbar_kwargs['label'] = plbl

            ret  = tdp.plot.pcolormesh(xr_xkey,xr_ykey,vmin=vmin,vmax=vmax,cmap=cmap,
                    cbar_kwargs=cbar_kwargs,ax=ax)
            ax.set_ylabel(ylabel)

            if plt_inx != nrows-1:
#                ax.set_xticklabels('')
                ax.set_xlabel('')
            else:
                ax.set_xlabel(xlabel)

            if plt_inx == 0:
                ax.set_title(self.meta.get('label',''))
            ax.set_title('({!s})'.format(letters[plt_inx]),loc='left')

            fig.tight_layout()
        
        return {'fig':fig}

class GrapeMultiplot(object):
    def __init__(self,gds):
        """
        gds: List of Grape1Data objects.
        """

        self.gds = gds

    def multiplot(self,data_set,params=['Freq','Power_dB'],
                    xkey='UTC',
                    sTime=None,eTime=None,
                    ylims=None,
                    color_dct=None,legend=True,
                    solar_lat=None,solar_lon=None,
                    events=None, event_fontdict = {'size':20,'weight':'bold'},
                    plot_GOES=False,GOES_sat_nr=17,GOES_data_dir='data/goes',
                    fig_width=22,panel_height=8):
        """
        Plot a time series with traces from multiple instruments overlaid on the same plot.

        Parameters
        ----------
        data_set:   Name of data set to plot (string)
        params:     List of parameter keys to plot. A new subplot will be created for each param.
        xkey:       X-axis parameter.
                        'UTC' for Coordinated Universal Time
                        'LMT' for Local Mean Time (solar time)
        sTime:      Start time of plot (UTC or LMT datetime object)
        eTime:      End time of plot (UTC or LMT datetime object)
        ylims:      None or dictionary with ylim for each parameter.
                    Example:
                      {'Freq':(-5,5)}
        color_dct:  Dictionary indicating how to color the traces.
                    Example:
                      {'ckey':'lon'} will color the traces according to the lon parameter
                            using the default colormap (viridis) and vmax/min parameters.

                      {'ckey':'lat','cmap':'jet','vmin':-90,'vmax':90} will color the traces
                            according to the lat parameter using the jet colormap with
                            vmin=-90 and vmax=90.
        legend:     Plot legend with name of each receiving station.
        solar_lat:  Latitude for computing sunrise/sunset times.
        solar_lon:  Longitude for computing sunrise/sunset times.

        """

        data = self.gds

        # Sort data objects by specified parameter and set color.
        if color_dct is not None:
            ckey = color_dct.get('ckey')

            # Sort data by ckey.
            vals = [x.meta[ckey] for x in data]
            srt  = np.argsort(vals)[::-1]
            data = [data[x] for x in srt]

            cmap = color_dct.get('cmap','viridis')
            if len(vals) > 0:
                vmin = color_dct.get('vmin',np.min(vals))
                vmax = color_dct.get('vmax',np.max(vals))
            else:
                vmin = -10.
                vmax =  10.

            if vmin == vmax:
                vmin = vmin - 10.
                vmax = vmax + 10.

            norm = mpl.colors.Normalize(vmin=vmin, vmax=vmax)
            mpbl = mpl.cm.ScalarMappable(norm=norm, cmap=cmap)

        # Determine sTime and eTime if not specified.
        if sTime is None or eTime is None:
            xx_xtrm   = [] # Keep track of time extrema.
            for gd in data:
                df_data = gd.data[data_set]['df']
                if len(df_data) == 0:
                    continue

                xx      = df_data[xkey]
                xx_xtrm.append(np.min(xx))
                xx_xtrm.append(np.max(xx))

            if sTime is None:
                sTime = min(xx_xtrm)

            if eTime is None:
                eTime = max(xx_xtrm)

	    
        ncols = 1
        nrows = len(params)
        if plot_GOES:
            nrows += 1

        figsize = (fig_width, nrows*panel_height)
        fig     = plt.figure(figsize=figsize)

        axs = []
        plt_inx = 0
        if plot_GOES:
            plt_inx += 1
            ax   = fig.add_subplot(nrows, ncols, plt_inx)
            ax.set_title('({!s})'.format(letters[plt_inx]),loc='left')
            axs.append(ax)

            goes_data = goes.read_goes(sTime,eTime,sat_nr=GOES_sat_nr,data_dir=GOES_data_dir)
            goes.goes_plot(goes_data,sTime,eTime,ax=ax)
            ax.set_title('NOAA GOES-{:02d}'.format(GOES_sat_nr),loc='right')

            if plt_inx != nrows-1:
                ax.set_xticklabels('')

            if events is not None:
                trans       = mpl.transforms.blended_transform_factory(ax.transData,ax.transAxes)
                for event in events:
                    evt_dtime   = event.get('datetime')
                    evt_label   = event.get('label')
                    evt_color   = event.get('color','0.4')

                    ax.axvline(evt_dtime,lw=1,ls='--',color=evt_color)
                    if evt_label is not None:
                        ax.text(evt_dtime,0.01,evt_label,transform=trans,
                                rotation=90,fontdict=event_fontdict,color=evt_color,
                                va='bottom',ha='right')

        params = gl.get_iterable(params)
        for prm_inx,(param) in enumerate(params):
            plt_inx += 1
            ax   = fig.add_subplot(nrows, ncols, plt_inx)
            axs.append(ax)

            abs_maxes = [] # Keep track of absolute value maxima
            for gd in data:
                df_data = gd.data[data_set]['df']
                if len(df_data) == 0:
                    continue

                label   = gd.meta['label']

                plt_kw  = {}

                xx      = df_data[xkey]
                yy      = df_data[param]

                if not np.all(np.isfinite(yy)):
                    continue

                abs_maxes.append(np.nanmax(np.abs(yy)))
                if color_dct is not None:
                    val     = gd.meta[ckey]
                    plt_kw['color'] = mpbl.cmap(mpbl.norm(val))

                ax.plot(xx,yy,label=label,**plt_kw)

            ax.set_title('({!s})'.format(letters[plt_inx]),loc='left')

            prmd    = prm_dict.get(param,{})
            rtitle  = prmd.get('title')
            if rtitle:
                ax.set_title(rtitle,loc='right')

            ylbl    = prmd.get('label',param)
            ax.set_ylabel(ylbl)

            legend_bbox_to_anchor = (1.04,1)
            if color_dct is not None:
                cb_prmd = prm_dict.get(ckey,{})
                clabel  = cb_prmd.get('label',ckey)
                fig.colorbar(mpbl,ax=ax,label=clabel)
                legend_bbox_to_anchor = (1.2,1)

            if legend:
                ax.legend(bbox_to_anchor=legend_bbox_to_anchor, loc="upper left", borderaxespad=0)

            if len(xx_xtrm) == 0:
                ax.text(0.5,0.5,'No Data',ha='center',transform=ax.transAxes,fontsize=36)
                continue

            ax.set_xlim(sTime,eTime)

            if param == 'Freq':
                abs_max = np.max(abs_maxes)
                ax.set_ylim(-abs_max*1.05,abs_max*1.05)

            # Set ylim from ylims keyword.
            if ylims is not None:
                ylim = ylims.get(param)
                if ylim is not None:
                    ax.set_ylim(ylim)


            if plt_inx != nrows:
                ax.set_xticklabels('')
            else:
                xprmd   = prm_dict.get(xkey,{})
                xlbl    = xprmd.get('label',xkey)
                ax.set_xlabel(xlbl)

            if events is not None:
                trans       = mpl.transforms.blended_transform_factory(ax.transData,ax.transAxes)
                for event in events:
                    evt_dtime   = event.get('datetime')
                    evt_label   = event.get('label')
                    evt_color   = event.get('color','0.4')

                    ax.axvline(evt_dtime,lw=1,ls='--',color=evt_color)
                    if evt_label is not None:
                        ax.text(evt_dtime,0.01,evt_label,transform=trans,
                                rotation=90,fontdict=event_fontdict,color=evt_color,
                                va='bottom',ha='right')

            # Add solar terminator
            if (solar_lat is not None) and (solar_lon is not None):
                solar.add_terminator(sTime,eTime,solar_lat,solar_lon,ax,xkey=xkey)

        date_str = sTime.strftime('%Y %b %d %H:%M UT') + ' - ' + eTime.strftime('%Y %b %d %H:%M UT')            
        title = []
#        title.append('HamSCI Grape PSWS Observations')
        title.append(date_str)
        axs[0].text(0.5,1.1,'\n'.join(title),ha='center',fontsize=24,
                fontweight='bold',transform=axs[0].transAxes)

        fig.tight_layout()
        if plot_GOES:
            gl.adjust_axes(axs[0],axs[-1])

        return {'fig':fig,'axs':axs}
