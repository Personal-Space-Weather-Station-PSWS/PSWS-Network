"""
solar.py

Convenience module for select solar calculations and plotting routines.

Written by Nathaniel Frissell, August 2022.
"""

import datetime
import pytz
import numpy as np
import matplotlib as mpl
from . import calcSun
#import calcSun

def solar_time(datetime_utc,lon):
    """
    Convert UTC datetime object into Local Mean Time.

    Parameters
    ----------
    datetime_utc
        Datetime object in UTC.
    lon
        Geographic longitude of observation.

    """
    lmt = datetime_utc + datetime.timedelta(hours=(lon/15.))
    lmt = lmt.replace(tzinfo=None)
    return lmt

def utc_time(datetime_lmt,lon):
    """
    Convert datetime object from Local Mean Time to UTC.

    Parameters
    ----------
    datetime_lmt: Datetime object in Local Mean Time.
    lon:          Geographic longitude of observation.
    """
    utc = datetime_lmt - datetime.timedelta(hours=(lon/15.))
    utc = utc.replace(tzinfo=pytz.UTC)
    return utc

def sunAzEl(dates,lat,lon):
    """
    Return the azimuths and elevation angles of the Sun for
    a list of UTC dates and lat/lon location.

    Parameters
    ----------
    dates:  List of UTC datetime objects.
    lat:    Geographic latitude of location.
    lon:    Geographic longitude of location.
    """
    azs, els = [], []
    for date in dates:
        jd    = calcSun.getJD(date) 
        t     = calcSun.calcTimeJulianCent(jd)
        ut    = ( jd - (int(jd - 0.5) + 0.5) )*1440.
        az,el = calcSun.calcAzEl(t, ut, lat, lon, 0.)
        azs.append(az)
        els.append(el)
    return azs,els

def add_terminator(sTime,eTime,lat,lon,ax,color='0.7',alpha=0.3,xkey='UTC',
        resolution=datetime.timedelta(minutes=1),**kw_args):
    """
    Shade the nighttime region on a time series plot.

    Parameters
    ----------
    sTime:   UTC start time of time series plot in datetime.datetime format
    eTime:   UTC end time of time series plot in datetime.datetime format
    lat:     latitude for solar terminator calculation
    lon:     longitude for solar terminator calculation
    ax:      matplotlib axis object to apply shading to.
    color:   color of nighttime shading
    alpha:   alpha of nighttime shading
    kw_args: additional keywords passed to ax.axvspan
    """
    if xkey == 'LMT':
        sTime = utc_time(sTime,lon)
        eTime = utc_time(eTime,lon)

    xlim_0      = sTime.replace(tzinfo=None)
    xlim_1      = eTime.replace(tzinfo=None)

    sDate = datetime.datetime(sTime.year,sTime.month,sTime.day) - datetime.timedelta(days=1)
    eDate = datetime.datetime(eTime.year,eTime.month,eTime.day) + datetime.timedelta(days=1)

    dates = [sDate]
    while dates[-1] <= eDate:
        dates.append(dates[-1] + resolution)

    azs, els = sunAzEl(dates,lat,lon)

    els     = np.array(els)
    night   = els < 90.
    night   = night.astype(int) # WDE patched 1/20/2025
    term    = np.diff(night)

    # Determine the indices and times where sunrise and sunset occur.
    sr_inx  = np.where(term ==  1)[0] # Sunrise Indices
    ss_inx  = np.where(term == -1)[0] # Sunset Indices

    sr_times    = [dates[x] for x in sr_inx]
    ss_times    = [dates[x] for x in ss_inx]

    # If Local Mean Time requested, convert UTC times to solar times.
    if xkey == 'LMT':
        sr_times = [solar_time(x,lon) for x in sr_times]
        ss_times = [solar_time(x,lon) for x in ss_times]

    # If we are looking at a time period where it is only day or only night.
    if len(sr_times) == 0 and len(ss_times) == 0:
        if np.all(night):
            ss_times = [xlim_0]
            sr_times = [xlim_1]
        else:
            return

    # If we have a time range where there is no sunset, assume that it is night from
    # the beginning of the plot to sunrise time, and day for the rest of the period.
    if len(ss_times) == 0:
        if sr_times[0] > xlim_0:
            ss_times = [xlim_0]

    # If we have a time range where there is no sunrise, assume that it is day from
    # the beginning of the plot to sunset time, and night for the rest of the period.
    if len(sr_times) == 0:
        if ss_times[-1] < xlim_1:
            sr_times = [xlim_1]

    # If the first sunrise occurs after xlim_0, and 
    # if the first sunrise occurs before the first sunset,
    # then make xlim_0 the first sunset.
    if (sr_times[0] > xlim_0) and (sr_times[0] < ss_times[0]):
        ss_times = np.concatenate( ([xlim_0], ss_times) )

    # If the last sunset occurs after xlim_1, and 
    # if the last sunset occurs after the last sunset,
    # then make xlim_1 the last sunrise.
    if (ss_times[-1] > xlim_1) and (sr_times[-1] < ss_times[-1]):
        sr_times = np.concatenate( (sr_times, [xlim_1]) )

    # Iterate through list of sunset, sunrise pairs and shade plot.
    for ss,sr in zip(ss_times,sr_times):
        ax.axvspan(ss,sr,color=color,alpha=alpha,**kw_args) 
