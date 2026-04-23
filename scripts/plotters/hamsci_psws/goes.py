#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Full license can be found in LICENSE.txt
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""GOES module

A module for working with GOES data.

Module Author:: N.A. Frissell, 6 Sept 2014
    Updated 14 August 2022

Key Functions
--------------------------------------------------------
read_goes       download GOES data
goes_plot       plot GOES data
classify_flare  convert GOES data to string classifier
flare_value     convert string classifier to lower bound
find_flares     find flares in a certain class
--------------- ----------------------------------------

"""

import logging
logging.basicConfig(level=logging.INFO)
import os
import datetime
import fnmatch
import re
import glob
import requests
from bs4 import BeautifulSoup
import calendar

import matplotlib
from matplotlib import pyplot as plt

import numpy as np
import pandas as pd

import netCDF4
import warnings

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

goes_table = []


def add_months(sourcedate,months=1):
    """Add 1 month to a datetime object.

    Parameters
    ----------
    sourcedate : datetime

    months : Optional[int]

    """
    month   = int(sourcedate.month - 1 + months)
    year    = int(sourcedate.year + month / 12)
    month   = int(month % 12 + 1)
    day     = min(sourcedate.day,calendar.monthrange(year,month)[1])
    return datetime.date(year,month,day)

def ut_hours(dt_obj):
    ut_hr   = dt_obj.hour + dt_obj.minute/60. + dt_obj.second/3600.
    return ut_hr

def dtGreg_to_datetime(dtg):
    pdt = datetime.datetime(dtg.year,dtg.month,dtg.day,dtg.hour,dtg.minute,dtg.second)
    return pdt

def download_url(url,pattern=None,data_dir=None,sTime=None,eTime=None):
    """
    Scrape URL for links and download files matching a pattern.

    URL:        Base URL to scrape for links.
    pattern:    pattern to match filenames to be downloaded
    data_dir:   path to save files

    Returns:
        file_paths: list of paths of downloaded files
    """

    if sTime is not None:
        sDate = datetime.datetime(sTime.year,sTime.month,sTime.day)

    if eTime is not None:
        eDate = datetime.datetime(eTime.year,eTime.month,eTime.day)

    page        = requests.get(url)
    soup        = BeautifulSoup(page.text,'html.parser')

    # Parse all links on webpage and save all that match the filename pattern
    # for the files we want to a download list.
    dl_list = []
    for node in soup.find_all('a'):
        href = node.get('href')
        if href is None:
            continue

        if pattern is not None:
            if not fnmatch.fnmatch(href,pattern):
                continue

        # Remove any days that are not between the requested start time
        # and end time.
        if sTime is not None or eTime is not None:
            match = re.search('_d\d{8}',href) # Search the file name for a date pattern.
            if match:
                date = datetime.datetime.strptime(match.group(0),'_d%Y%m%d')
                
                if sTime is not None:
                    if date < sDate:
                        continue

                if eTime is not None:
                    if date > eDate:
                        continue

        dl_list.append(href)

    # Download each of the files in the download list.
    file_paths = []
    for dl in dl_list:
        req = requests.get(url+'/'+dl,stream=True)
        if req.status_code == 200:
            file_path = os.path.join(data_dir,dl)
            file_paths.append(file_path)

            # Only download if the file does not already exist locally.
            if not os.path.exists(file_path):
                logging.info('Downloading {0}...'.format(dl))
                with open(file_path,'wb') as fl:
                    fl.write(req.content)
            else:
                logging.info('Using Cached File {0}...'.format(dl))
        else:
            logging.info('   Download ERROR.')
    return file_paths

def read_goes(sTime,eTime=None,sat_nr=15,data_dir='data_goes'):
    """Download GOES X-Ray Flux data from the NOAA FTP Site and return a
    dictionary containing the metadata and a dataframe.

    Parameters
    ----------
    sTime : datetime.datetime
        Starting datetime for data.
    eTime : Optional[datetime.datetime]
        Ending datetime for data.  If None, eTime will be set to sTime
        + 1 day.
    sat_nr : Optional[int]
        GOES Satellite number.  Defaults to 15.
        A list of GOES satellites and their operational time periods is
        available at https://www.noaasis.noaa.gov/GOES/goes_overview.html.

    Returns
    -------
    Dictionary containing metadata, pandas dataframe with GOES data.

    Notes
    -----
    Data is downloaded from
    ftp://satdat.ngdc.noaa.gov/sem/goes/data/avg/2014/08/goes15/netcdf/

    Currently, 1-m averaged x-ray spectrum in two bands
    (0.5-4.0 A and 1.0-8.0 A).

    Example
    -------
        goes_data = read_goes(datetime.datetime(2014,6,21))
      
    written by N.A. Frissell, 6 Sept 2014

    """

    if eTime is None: eTime = sTime + datetime.timedelta(days=1)

    # Download Files from NOAA Data Servers ########################################
    if data_dir.endswith('/'): data_dir = data_dir[:-1]
    
    try:
        os.makedirs(data_dir)
    except:
        pass

    if sat_nr < 16:
    # Use this section for downloading section for GOES satellites < 16.
    # Determine which months of data to download.
        ym_list     = [datetime.date(sTime.year,sTime.month,1)]
        eMonth      = datetime.date(eTime.year,eTime.month,1)
        while ym_list[-1] < eMonth:
            ym_list.append(add_months(ym_list[-1]))

        #rem_file    = '/sem/goes/data/avg/2014/08/goes15/netcdf/g15_xrs_1m_20140801_20140831.nc' #Example file.
        file_paths  = []
        for myTime in ym_list:

            #Check to see if we already have a matching file...
            local_files = glob.glob(os.path.join(data_dir,'g{sat_nr:02d}_xrs_1m_{year:d}{month:02d}*.nc'.format(year=myTime.year,month=myTime.month,sat_nr=sat_nr)))
            if len(local_files) > 0:
                logging.info('Using locally cached file: {0}'.format(local_files[0]))
                file_paths.append(local_files[0])
                continue

            # Build URL, download webpage.
            url         = 'https://satdat.ngdc.noaa.gov/sem/goes/data/avg/{year:d}/{month:02d}/goes{sat_nr:d}/netcdf'.format(year=myTime.year,month=myTime.month,sat_nr=sat_nr)
            pattern     = 'g*_xrs_1m_*'
            file_paths  = file_paths + download_url(url,pattern,data_dir)

        # Load data into memory. #######################################################
        df_xray     = None
        df_orbit    = None

        data_dict   = {}
        data_dict['metadata']               = {}
        data_dict['metadata']['variables']  = {}

        df_orbit    = []
        df_xray     = []
        for file_path in file_paths:
            nc = netCDF4.Dataset(file_path)

            #Put metadata into dictionary.
            fn  = os.path.basename(file_path)
            data_dict['metadata'][fn] = {}
            md_keys = ['NOAA_scaling_factors','archiving_agency','creation_date','end_date',
                       'institution','instrument','originating_agency','satellite_id','start_date','title']
            for md_key in md_keys:
                try:
                    data_dict['metadata'][fn][md_key] = getattr(nc,md_key)
                except:
                    pass

            #Store Orbit Data
            tt = nc.variables['time_tag_orbit']
            jd = np.array(netCDF4.num2date(tt[:],tt.units))

            orbit_vars = ['west_longitude','inclination']
            data    = {}
            for var in orbit_vars:
                # Silence warning: UserWarning: WARNING: missing_value not used since it cannot be safely cast to variable data type
                # We remove the missing_value flags later in the code, so we can ignore this warning.
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore')
                    data[var] = nc.variables[var][:]
            
            df_tmp = pd.DataFrame(data,index=jd)
            df_orbit.append(df_tmp)

            #Store X-Ray Data
            tt = nc.variables['time_tag']
            jd = np.array(netCDF4.num2date(tt[:],tt.units))

            myVars = ['A_QUAL_FLAG','A_NUM_PTS','A_AVG','B_QUAL_FLAG','B_NUM_PTS','B_AVG']
            data = {}
            for var in myVars:
                # Silence warning: UserWarning: WARNING: missing_value not used since it cannot be safely cast to variable data type
                # We remove the missing_value flags later in the code, so we can ignore this warning.
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore')
                    data[var] = nc.variables[var][:]
            
            df_tmp = pd.DataFrame(data,index=jd)
            df_xray.append(df_tmp)

            #Store info about units
            for var in (myVars+orbit_vars):
                data_dict['metadata']['variables'][var] = {}
                var_info_keys = ['description','dtype','long_label','missing_value','nominal_max','nominal_min','plot_label','short_label','units']
                for var_info_key in var_info_keys:
                    try:
                        data_dict['metadata']['variables'][var][var_info_key] = getattr(nc.variables[var],var_info_key)
                    except:
                        pass

        # Concatenate dataframes from each file into single dataframes.
        df_xray     = pd.concat(df_xray)
        df_orbit    = pd.concat(df_orbit)

        # Set -99999 to NaN.
        keys    = ['A_AVG','B_AVG']
        for key in keys:
            tf  = df_xray[key]  == -99999
            df_xray[key][tf]    = np.nan

        # Strictly enforce time limits.
        df_xray     = df_xray[np.logical_and(df_xray.index >= sTime,df_xray.index < eTime)]
        df_orbit    = df_orbit[np.logical_and(df_orbit.index >= sTime,df_orbit.index < eTime)]

        df_orbit['longitude']   = -1*df_orbit['west_longitude']
        del df_orbit['west_longitude']

        df_xray = pd.concat([df_xray,df_orbit],axis=1)
        for key in df_orbit.keys():
            df_xray[key].fillna(method='ffill',inplace=True)

        df_xray['ut_hrs']   = df_xray.index.map(ut_hours)
        df_xray['slt_mid']  = (df_xray['ut_hrs'] + df_xray['longitude']/15.) % 24.

        data_dict['xray']   = df_xray
        data_dict['orbit']  = df_orbit

        data_dict['xray'].index  = [dtGreg_to_datetime(x) for x in data_dict['xray'].index]
        data_dict['orbit'].index = [dtGreg_to_datetime(x) for x in data_dict['orbit'].index]
    else:
        sDate = datetime.datetime(sTime.year,sTime.month,sTime.day)
        eDate = datetime.datetime(eTime.year,eTime.month,eTime.day)

        dates = [sDate]
        while dates[-1] < eDate:
            dates.append(dates[-1] + datetime.timedelta(days=1))

        all_files_downloaded = True
        local_files   = []
        missing_dates = []
        for date in dates:
            result = glob.glob(os.path.join(data_dir,'sci_xrsf-l2-avg1m_g{sat_nr:02d}_d{year:d}{month:02d}{day:02d}*.nc'.format(year=date.year,month=date.month,day=date.day,sat_nr=sat_nr)))

            if len(result) > 0:
                local_files = local_files + result
            else:
                all_files_downloaded = False
                missing_dates.append(date)

        if all_files_downloaded:
            logging.info('Using locally cached files for {!s} - {!s}.'.format(sTime.strftime('%Y %b %d'),eTime.strftime('%Y %b %d')))
            file_paths = local_files
        else:
            yrMonths    = list(set([(x.year,x.month) for x in dates])) # Find unique months.
            file_paths  = []
            for year,month in yrMonths:
                #url        = 'https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/goes16/l2/data/xrsf-l2-avg1m_science/2019/01/'
                url         = 'https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/goes{sat_nr:d}/l2/data/xrsf-l2-avg1m_science/{year:d}/{month:02d}/'.format(year=year,month=month,sat_nr=sat_nr)
                pattern     = 'sci_xrsf-l2-avg1m*.nc'
                file_paths  = file_paths + download_url(url,pattern,data_dir,sTime=sTime,eTime=eTime)

        # Load data into memory. #######################################################
        df_xray     = None

        data_dict   = {}
        data_dict['metadata']               = {}
        data_dict['metadata']['variables']  = {}

        df_xray     = []
        for file_path in file_paths:
            nc = netCDF4.Dataset(file_path)

            #Put metadata into dictionary.
            fn  = os.path.basename(file_path)
            data_dict['metadata'][fn] = {}
            md_keys = ['id','NOAA_scaling_factors','archiving_agency','creation_date','end_date',
                       'institution','instrument','originating_agency','satellite_id','start_date','title']

            for md_key in md_keys:
                try:
                    data_dict['metadata'][fn][md_key] = getattr(nc,md_key)
                except:
                    pass
            data_dict['metadata'][fn]['satellite_id'] = 'GOES-{:02d}'.format(sat_nr)

            #Store X-Ray Data
            tt = nc.variables['time']
            jd = np.array(netCDF4.num2date(tt[:],tt.units))

            myVars = {'xrsa_flag':'A_QUAL_FLAG','xrsa_num':'A_NUM_PTS','xrsa_flux':'A_AVG','xrsb_flag':'B_QUAL_FLAG','xrsb_num':'B_NUM_PTS','xrsb_flux':'B_AVG'}
            data = {}
            for var in myVars.keys():
                # Silence warning: UserWarning: WARNING: missing_value not used since it cannot be safely cast to variable data type
                # We remove the missing_value flags later in the code, so we can ignore this warning.
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore')
                    data[var] = nc.variables[var][:]
            
            df_tmp = pd.DataFrame(data,index=jd)
            df_xray.append(df_tmp)

            #Store info about units
            for var,oldVar in myVars.items():
                data_dict['metadata']['variables'][oldVar] = {}
                var_info_keys = ['long_name','_FillValue','valid_min','valid_max','plot_label','short_label','units']
                for var_info_key in var_info_keys:
                    try:
                        data_dict['metadata']['variables'][oldVar][var_info_key] = getattr(nc.variables[var],var_info_key)
                    except:
                        pass

                if oldVar == 'A_AVG':
                    data_dict['metadata']['variables'][oldVar]['short_label'] = 'xs fx'
                    data_dict['metadata']['variables'][oldVar]['long_label']  = 'x-ray (0.05-0.4 nm) irradiance'

                if oldVar == 'B_AVG':
                    data_dict['metadata']['variables'][oldVar]['short_label'] = 'xl fx'
                    data_dict['metadata']['variables'][oldVar]['long_label']  = 'x-ray (0.1-0.8 nm) irradiance'

        # Concatenate dataframes from each file into single dataframes.
        df_xray     = pd.concat(df_xray)

        # Set Bad Data to NaN
        keys    = [('xrsa_flux','xrsa_flag'), ('xrsb_flux','xrsb_flag')]
        for prm_key,flag_key in keys:
            tf  = df_xray[flag_key]  == 1 # Flag of 1 means bad data
            df_xray.loc[tf,prm_key]    = np.nan

        # Set column names to be compatible with old format GOES data.
        df_xray     = df_xray.rename(columns=myVars).copy()

        # Strictly enforce time limits.
        df_xray     = df_xray[np.logical_and(df_xray.index >= sTime,df_xray.index < eTime)]

        if nc.orbital_slot == 'GOES-West':
            longitude = -137.
        elif nc.orbital_slot == 'GOES-East':
            longitude = -75.

        df_xray['ut_hrs']   = df_xray.index.map(ut_hours)
        df_xray['slt_mid']  = (df_xray['ut_hrs'] + longitude/15.) % 24.

        data_dict['xray']   = df_xray

        data_dict['xray'].index  = [dtGreg_to_datetime(x) for x in data_dict['xray'].index]

    return data_dict

def goes_plot_hr(goes_data,ax,var_tags = ['B_AVG'],xkey='ut_hr',xlim=(0,24),ymin=1e-9,ymax=1e-2,
        legendSize=10,legendLoc=None,labels=None,**kwargs):
    """Plot GOES X-Ray Data.

    Parameters
    ----------
    goes_data   : dict
        data dictionary returned by read_goes()
    ax          : matplotlib.axes
    var_tags    : List of variables, i.e. ['A_AVG','B_AVG']
        'A_AVG' --> X-Ray (0.05-0.4 nm) Irradiance [W/m^2]
        'B_AVG' --> X-Ray (0.1 -0.8 nm) Irradiance [W/m^2]
    ymin : Optional[float]
        Y-Axis minimum limit
    ymax : Optional[float]
        Y-Axis maximum limit
    legendSize : Optional[int]
        Character size of the legend
    legendLoc : Optional[ ]

    Returns
    -------
    fig : matplotlib.figure
        matplotlib figure object that was plotted to

    Notes
    -----
    If a matplotlib figure currently exists, it will be modified
    by this routine.  If not, a new one will be created.

    Written by Nathaniel Frissell 2014 Sept 06

    """
    xx  = goes_data['xray'][xkey]
    for var_inx,var_tag in enumerate(var_tags):
        if labels is None:
            label   = goes_data['metadata']['variables'][var_tag]['long_label']
        else:
            label   = labels[var_inx]
        ax.plot(xx,goes_data['xray'][var_tag],label=label,**kwargs)

    ax.set_xlim(xlim)

    #Label Flare classes
    trans = matplotlib.transforms.blended_transform_factory(ax.transAxes, ax.transData)
    classes = ['A', 'B', 'C', 'M', 'X']
    decades = [  8,   7,   6,   5,   4]

    for cls,dec in zip(classes,decades):
        ax.text(1.01,2.5*10**(-dec),cls,transform=trans,fontdict={'size':14})

    #Format the y-axis
    ax.set_ylabel(r'W m$^{-2}$')
    ax.set_yscale('log')
    ax.set_ylim(1e-9,1e-2)

#    minor_ticks = np.array([1e-9,1e-8,1e-7,1e-6,1e-5,1e-4,1e-3,1e-2])
#    ax.set_yticks(minor_ticks,minor=True)
#
#    minor_ticks = np.array([])
#    ax.set_xticks(minor_ticks,minor=True)
#
#    ax.minorticks_on()
#    ax.grid(True,which='minor')
    ax.grid(True,which='major')
    ax.legend(prop={'size':legendSize},numpoints=1,loc=legendLoc)

    file_keys = list(goes_data['metadata'].keys()) 
    file_keys.remove('variables')
    file_keys.sort()
    md      = goes_data['metadata'][file_keys[-1]]
    title   = ' '.join([md['institution'],md['satellite_id'],'-',md['instrument']])
#    ax.set_title(title)

def goes_plot(goes_data,sTime=None,eTime=None,var_tags = ['B_AVG'],labels=None,ymin=1e-9,ymax=1e-2,legendSize=None,legendLoc=None,ax=None,**kwargs):
    """Plot GOES X-Ray Data.

    Parameters
    ----------
    goes_data : dict
        data dictionary returned by read_goes()
    sTime : Optional[datetime.datetime]
        object for start of plotting.
    eTime : Optional[datetime.datetime]
        object for end of plotting.
    ymin : Optional[float]
        Y-Axis minimum limit
    ymax : Optional[float]
        Y-Axis maximum limit
    legendSize : Optional[int]
        Character size of the legend
    legendLoc : Optional[ ]
    ax : Optional[ ]

    Returns
    -------
    fig : matplotlib.figure
        matplotlib figure object that was plotted to

    Notes
    -----
    If a matplotlib figure currently exists, it will be modified
    by this routine.  If not, a new one will be created.

    Written by Nathaniel Frissell 2014 Sept 06

    """
    if ax is None:
        fig     = plt.figure(figsize=(10,6))
        ax      = fig.add_subplot(111)
    else:
        fig     = ax.get_figure()

    if sTime is None: sTime = goes_data['xray'].index.min()
    if eTime is None: eTime = goes_data['xray'].index.max()

    xx = goes_data['xray'].index
    for var_inx,var_tag in enumerate(var_tags):
        if labels is None:
            label   = goes_data['metadata']['variables'][var_tag]['long_label']
        else:
            label   = labels[var_inx]
        ax.plot(xx,goes_data['xray'][var_tag],label=label,**kwargs)

#    #Format the x-axis
#    if eTime - sTime > datetime.timedelta(days=1):
#        ax.xaxis.set_major_formatter(
#                matplotlib.dates.DateFormatter('%H%M\n%d %b %Y')
#                )
#    else:
#        ax.xaxis.set_major_formatter(
#                matplotlib.dates.DateFormatter('%H%M')
#                )

    sTime_label = sTime.strftime('%Y %b %d')
    eTime_label = eTime.strftime('%Y %b %d')
    if sTime_label == eTime_label:
        time_label = sTime_label
    else:
        time_label = sTime_label + ' - ' + eTime_label

#    ax.set_xlabel('\n'.join([time_label,'Time [UT]']))
    ax.set_xlim(sTime,eTime)

    #Label Flare classes
    trans = matplotlib.transforms.blended_transform_factory(ax.transAxes, ax.transData)
    classes = ['A', 'B', 'C', 'M', 'X', '']
    decades = [  8,   7,   6,   5,   4,  3]

    size    = matplotlib.rcParams['ytick.labelsize']
    for cls,dec in zip(classes,decades):
        ax.text(1.01,10**(-dec),cls,transform=trans,fontdict={'size':size},va='center')
        ax.axhline(10**(-dec),ls='--',color='0.8')

    #Format the y-axis
    ax.set_ylabel(r'W m$^{-2}$')
    ax.set_yscale('log')
    ax.set_ylim(1e-9,1e-2)

    ax.grid()
    if legendSize is None:
        legendSize = matplotlib.rcParams['legend.fontsize']
    ax.legend(prop={'size':legendSize},numpoints=1,loc=legendLoc)

    file_keys = list(goes_data['metadata'].keys()) 
    file_keys.remove('variables')
    file_keys.sort()
    md      = goes_data['metadata'][file_keys[-1]]
    title   = ' '.join([md['institution'],md['satellite_id'],'-',md['instrument']])
#    ax.set_title(title)

def __split_sci(value):
    """Split scientific notation into (coefficient,power).
    This is a private function that currently only works on scalars.

    Parameters
    ----------
    value :
        numerical value

    Returns
    -------
    coefficient : float

    Written by Nathaniel Frissell 2014 Sept 07

    """
    s   = '{0:e}'.format(value)
    s   = s.split('e')
    return (float(s[0]),float(s[1]))


def classify_flare(value):
    """Convert GOES X-Ray flux into a string flare classification.
    You should use the 1-8 Angstrom band for classification [1] 
    (B_AVG in the NOAA data files).

    A 0.001 W/m**2 measurement in the 1-8 Angstrom band is classified as an X10 flare..

    This function currently only works on scalars.

    Parameters
    ----------
    value :
        numerical value of the GOES 1-8 Angstrom band X-Ray Flux in W/m^2.

    Returns
    -------
    flare_class : string
        class of solar flare

    References
    ----------
    [1] http://www.spaceweatherlive.com/en/help/the-classification-of-solar-flares

    Example
    -------
        flare_class = classify_flare(0.001)

    Written by Nathaniel Frissell 2014 Sept 07

    """
    coef, power = __split_sci(value)

    if power < -7:
        letter  = 'A'
        coef    = value / 1e-8
    elif power >= -7 and power < -6:
        letter  = 'B'
    elif power >= -6 and power < -5:
        letter  = 'C'
    elif power >= -5 and power < -4:
        letter  = 'M'
    elif power >= -4:
        letter  = 'X'
        coef    = value / 1.e-4

    flare_class = '{0}{1:.1f}'.format(letter,coef)
    return flare_class


def flare_value(flare_class):
    """Convert a string solar flare class [1] into the lower bound in W/m**2 of the 
    1-8 Angstrom X-Ray Band for the GOES Spacecraft.

    An 'X10' flare = 0.001 W/m**2.

    This function currently only works on scalars.

    Parameters
    ----------
    flare_class : string
        class of solar flare (e.g. 'X10')

    Returns
    -------
    value : float
        numerical value of the GOES 1-8 Angstrom band X-Ray Flux in W/m**2.

    References
    ----------
    [1] See http://www.spaceweatherlive.com/en/help/the-classification-of-solar-flares

    Example
    -------
        value = flare_value('X10')

    Written by Nathaniel Frissell 2014 Sept 07

    """
    flare_dict  = {'A':-8, 'B':-7, 'C':-6, 'M':-5, 'X':-4} 
    letter      = flare_class[0]
    power       = flare_dict[letter.upper()]
    coef        = float(flare_class[1:])
    value       = coef * 10.**power
    return value


def find_flares(goes_data,window_minutes=60,min_class='X1',sTime=None,eTime=None,tmp_dir='data'):
    """Find flares of a minimum class in a GOES data dict created by read_goes().
    This works with 1-minute averaged GOES data.

    Classifications are based on the 1-8 Angstrom X-Ray Band for the GOES Spacecraft.[1]

    Parameters
    ----------
    goes_data : dict
        GOES data dict created by read_goes()
    window_minutes : Optional[int]
        Window size to look for peaks in minutes.
        I.E., if window_minutes=60, then no more than 1 flare will be found 
        inside of a 60 minute window.
    min_class : Optional[str]
        Only flares >= to this class will be reported. Use a
        format such as 'M2.3', 'X1', etc.
    sTime : Optional[datetime.datetime]
        Only report flares at or after this time.  If None, the earliest
        available time in goes_data will be used.
    eTime : Optional[datetime.datetime]
        Only report flares before this time.  If None, the last
        available time in goes_data will be used.

    Returns
    -------
    flares : Pandas dataframe listing:
        * time of flares
        * GOES 1-8 Angstrom band x-ray flux
        * Classification of flare

    References
    ----------
    [1] See http://www.spaceweatherlive.com/en/help/the-classification-of-solar-flares

    Example
    -------
        sTime       = datetime.datetime(2014,1,1)
        eTime       = datetime.datetime(2014,6,30)
        sat_nr      = 15 # GOES15
        goes_data   = read_goes(sTime,eTime,sat_nr)
        flares = find_flares(goes_data,window_minutes=60,min_class='X1')

    Written by Nathaniel Frissell 2014 Sept 09

    """
    df  = goes_data['xray']

    if sTime is None: sTime = df.index.min()
    if eTime is None: eTime = df.index.max()

    # Figure out when big solar flares are.
    time_delta      = datetime.timedelta(minutes=window_minutes)
    time_delta_half = datetime.timedelta( minutes=(window_minutes/2.) )

    window_center = [sTime + time_delta_half ]
    while window_center[-1] < eTime:
        window_center.append(window_center[-1] + time_delta)

    b_avg = df['B_AVG']

    keys = []
    for win in window_center:
        sWin = win - time_delta_half
        eWin = win + time_delta_half

        try:
            idx_max = b_avg[sWin:eWin].idxmax()
            if idx_max is np.nan:
                continue
            keys.append(idx_max)
        except:
            pass
        
    df_win      = pd.DataFrame({'B_AVG':b_avg[keys]})

    flares      = df_win[df_win['B_AVG'] >= flare_value(min_class)]

    # Remove flares that are really window edges instead of local maxima.
    drop_list = []
    for inx_0,key_0 in enumerate(flares.index):
        if inx_0 == len(flares.index)-1: break

        inx_1   = inx_0 + 1
        key_1   = flares.index[inx_1]

        flare_0 = np.unique(flares['B_AVG'][key_0])
        flare_1 = np.unique(flares['B_AVG'][key_1])

        arg_min = np.argmin([flare_0,flare_1])
        key_min = [key_0,key_1][arg_min]

        vals_between = b_avg[key_0:key_1]

        if np.unique(flares['B_AVG'][key_min]) <= vals_between.min():
            drop_list.append(key_min)

    if drop_list != []:
        flares  = flares.drop(drop_list)
    flares  = flares.copy()
    flares['class'] = list(map(classify_flare,flares['B_AVG']))

    return flares


if __name__ == '__main__':

    # Flare Classification Test ####################################################
    print('')
    print('Flare classification test.')
    flares = ['A5.5', 'B4.0', 'X11.1']
    values = [5.5e-8, 4.0e-7, 11.1e-4]

    test_results = []
    for flare,value in zip(flares,values):
        print(('  Testing classify_flare() with {0} ({1:.1e} W/m**2) flare...'.format(flare,value)))

        test_flare = classify_flare(value)
        print(('    classify_flare({0:.1e}) = {1}'.format(value,test_flare)))
        test_results.append(flare == test_flare)

    if np.all(test_results):
        print('CONGRATULATIONS: Test passed for classify_flare()!')
    else:
        print('WARNING: classify_flare() failed self-test.')

    print('')
    test_results = []
    for flare,value in zip(flares,values):
        print(('  Testing flare_value() with {0} ({1:.1e} W/m**2) flare...'.format(flare,value)))
        test_value = flare_value(flare)
        print(('    flare_value({0}) = {1:.1e}'.format(test_flare,value)))
        test_results.append(value == test_value)

    if np.all(test_results):
        print('CONGRATULATIONS: Test passed for flare_value()!')
    else:
        print('WARNING: flare_value() failed self-test.')
    print('')

    # Flare finding and plotting test. #############################################
#    sTime       = datetime.datetime(2014,1,1)
#    eTime       = datetime.datetime(2014,6,30)
#    sat_nr      = 15

    sTime       = datetime.datetime(2021,10,28)
    eTime       = datetime.datetime(2021,10,29)
    sat_nr      = 17

    goes_data   = read_goes(sTime,eTime,sat_nr)

    output_dir  = 'data_goes'
    try:
        os.makedirs(output_dir)
    except:
        pass

    flares      = find_flares(goes_data,min_class='C1')

    with open(os.path.join(output_dir,'flares.txt'),'w') as fl:
        fl.write(flares.to_string())

    for key,flare in flares.iterrows():
        filename = key.strftime('goes_%Y%m%d_%H%M.png')
        filepath = os.path.join(output_dir,filename)

        fig     = plt.figure()
        ax      = fig.add_subplot(111)
        label   = '{0} Class Flare @ {1}'.format(flare['class'],key.strftime('%H%M UT'))
        ax.plot(key,flare['B_AVG'],'o',label=label)

        plot_sTime  = key - datetime.timedelta(hours=12)
        plot_eTime  = key + datetime.timedelta(hours=12)
        goes_plot(goes_data,ax=ax,sTime=plot_sTime,eTime=plot_eTime)

        fig.savefig(filepath,bbox_inches='tight')
        fig.clf()

    flares_str = """
Thank you for testing the goes.py module.  If everything worked, you should find a 
set of plots for all x-class flares from 1Jan2014 - 30Jun2014 in your data/goes.
A list of the flares is given below.  This should match the flares.txt file in the same
directory as your plots.

                     B_AVG     class
2014-01-07 18:32:00  0.000125  X1.2
2014-02-25 00:49:00  0.000497  X5.0
2014-03-29 17:48:00  0.000101  X1.0
2014-04-25 00:27:00  0.000139  X1.4
2014-06-10 11:42:00  0.000222  X2.2
2014-06-10 12:52:00  0.000155  X1.5
2014-06-11 09:06:00  0.000100  X1.0
"""

    print(flares_str)
    print(('Your data/goes: {0}'.format(output_dir)))
