# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
import json
import os
from django.shortcuts import redirect, render, get_object_or_404
import pytz
from datetime import datetime, timedelta, timezone
from django.urls import path
from django.utils.dateparse import parse_datetime
from django.conf import settings
from . import views
import zipfile
from stations.models import Station
from observations.models import Observation
from instruments.models import Instrument
from instrumenttypes.models import InstrumentType
from observations.tables import ObservationTable
from statistics import mean 

# Declaration of cutoff hours for station status
ONLINE_CUT_OFF_HOURS = settings.ONLINE_CUT_OFF_HOURS
POSSIBLY_ONLINE_CUT_OFF_HOURS = settings.POSSIBLY_ONLINE_CUT_OFF_HOURS
RETIREMENT_CUT_OFF_HOURS = settings.RETIREMENT_CUT_OFF_HOURS


# Display more detailed information about a station
def station_analysis(request, id=None):
    station = get_object_or_404(Station, id=id)

    #mag_stations = Station.objects.all()
    table = ObservationTable(Observation.objects.filter(station_id=id))
    table.paginate(page=request.GET.get("page", 1), per_page=8)
    return render(request, 'station_analysis.html', {
        'station': station,
        'table': table,
        'show_map': False
        })

def updateStatus():
    #Update Station status of all stations before displaying
    AliveCutoff = datetime.now(timezone.utc) - timedelta(hours=onlineCutoffHours)
    DeadCutoff = datetime.now(timezone.utc) - timedelta(hours=possiblyOnlineCutoffHours)
    for instance in Station.objects.all():
        if (instance.last_alive is None):
            instance.last_alive = datetime(2000,1,1,tzinfo=timezone.utc)
        if (instance.last_alive < DeadCutoff):
            instance.station_status = "Offline"
        elif (instance.last_alive < AliveCutoff):
            instance.station_status = "PossiblyOnline"
        else:
            instance.station_status = "Online"
        instance.save()

def display_graphs(request):
    mapbox_access_token = settings.MAPBOX_ACCESS_TOKEN
    datasets = None
    msg = ''
    start_datetime_str = ''
    start_converted = ''
    end_converted = ''

    if request.method == 'POST':
        # Get start date and station IDs from the form data
        start_datetime_str = request.POST.get('startDatetime')
        station_ids_str = request.POST.get('stationIds')
        station_ids = json.loads(station_ids_str) if station_ids_str else []

        utc = pytz.UTC
        start_converted = utc.localize(datetime.strptime(start_datetime_str, '%Y-%m-%dT%H:%M'))
        print('received data:', start_datetime_str, station_ids)

        if start_datetime_str and station_ids:
            #start_converted = parse_datetime(start_datetime_str)
            # Set end datetime as start + 24 hours (1 day) + a little extra in case observation ends late
            #end_converted = start_converted + timedelta(days=1)
            # Set end datetime as start + 24 hours (1 day) + a little extra in case observation ends late
            end_converted = start_converted + timedelta(days=0.9999) # same day but 11:59:30 PM
            #convert to proper format
            # start_converted = utc.localize(datetime.strptime(start, '%Y-%m-%dT%H:%M'))
            # end_converted = start_converted + timedelta(days=0.9)
            if start_converted:
                # Prepare data for plotting
                datasets = []
                for id in station_ids:
                    ts=[]
                    xs=[]
                    ys=[]
                    zs=[]
                    name=""
                    try:
                        station = get_object_or_404(Station, id=int(id))
                        name=station.nickname
                        address=station.city+' '+station.state
                        ob=Observation.objects.filter(station_id=int(id))
                        # Choices are: band, centerFrequency, dataRate, dataType, endDate, fileName, id, instrument, instrument_id, path, size, startDate, station, station_id
                    except:
                        ob=None
                    if ob!=None:
                        for o in ob.all():
                            file_extension=o.fileName[-4:]
                            if (o.startDate.date()>=start_converted.date()) and (o.endDate.date()<=end_converted.date()) and file_extension=='.zip':
                                path=('/').join(o.path.split('/')[:-1])+'/'+o.fileName
                                print('path =', path)
                                try:
                                    with zipfile.ZipFile(path) as zf:
                                        for file in zf.namelist():
                                            with zf.open(file) as f:
                                                try:
                                            # switch file format
                                            # line=f.readlines()[0]
                                            # print(line)
                                            # continue
                                            #case 1 b'{ "ts":"14 Nov 2022 00:00:00", "rt":16.56, "lt":29.56, "x":-44.0088, "y":0.9507, "z":-18.7339, "rx":-390, "ry":8, "rz":-166, "Tm": 47.8397 }\n'
                                            #case 2 ,x is [3] "15 Nov 2022 07:58:00", 17.62, 34.44, 3936.0, -253.3, 2800.0, 2952, -190, 2100, 4836.96948
                                            #case 3 , x is [2]'"14 Nov 2022 00:00:00", 17.81, -38.2493, -18.8440, -14.1587, -28, -14, -10, 44.9286\n' 
                                            #case 4 ['{ "ts":"22 Nov 2022 00:00:01"', ' "rt":13.44', ' "x":-38.340', ' "y":-18.920', ' "z":-13.707', ' "rx":-5751', ' "ry":-2838', ' "rz":-2056', ' "Tm": 44.89760 }\n']
                                            #case 5 [' Time: 07 Dec 2022 00:00:00', ' rTemp: 10.19', ' lTemp: 12.38', ' x: 47.307', ' y: -0.507', ' z: -14.800', ' rx: 3548', ' ry: -38', ' rz: -1110\n']
                                            # switch format issue 4  float error ['"22 Nov 2022 16:59:45"', ' 13.75', ' -93129.3', ' 0.0', ' 0.0', ' -139694', ' 0', ' 0', ' 93129.33333\n']
                                                    data=f.readlines()
                                                    if len(data)>0:
                                                        totalcount=0
                                                        check_case=0
                                                        if str(data[0],'UTF-8')[0]=='{' and len(str(data[0],'UTF-8').split(','))==10:
                                                            check_case=1
                                                        elif str(data[0],'UTF-8')[0]=='{' and len(str(data[0],'UTF-8').split(','))==9:
                                                            check_case=4
                                                        elif len(str(data[0],'UTF-8').split(','))==9 and str(data[0],'UTF-8')[1]=='T':
                                                            check_case=5
                                                        elif len(str(data[0],'UTF-8').split(','))==10:
                                                            check_case=2
                                                        elif len(str(data[0],'UTF-8').split(','))==9:
                                                            check_case=3
                                                        linecount=xx=yy=zz=0
                                                        for d in data:  #sum and take avg of minutes data
                                                            totalcount+=1
                                                            d=str(d,'UTF-8')
                                                            ds=d.split(',')
                                                            linecount+=1
                                                            if check_case==1:
                                                                t=ds[0][8:-4]
                                                                realtime=utc.localize(datetime.strptime(t, '%d %b %Y %H:%M'))
                                                                if realtime>end_converted:
                                                                    break
                                                                xx+=float(ds[3][5:])
                                                                yy+=float(ds[4][5:])
                                                                zz+=float(ds[5][5:])

                                                            elif check_case==4:
                                                                t=ds[0][8:-4]
                                                                realtime=utc.localize(datetime.strptime(t, '%d %b %Y %H:%M'))
                                                                if realtime>end_converted:
                                                                    break
                                                                xx+=float(ds[2][5:])
                                                                yy+=float(ds[3][5:])
                                                                zz+=float(ds[4][5:])
                                                        
                                                            elif check_case==5:
                                                                t=ds[0][7:-4]
                                                                print('case 5',t)
                                                                realtime=utc.localize(datetime.strptime(t, '%d %b %Y %H:%M'))
                                                                if realtime>end_converted:
                                                                    break
                                                                xx+=float(ds[3][4:])
                                                                yy+=float(ds[3][4:])
                                                                zz+=float(ds[3][4:])
                                              
                                                            elif check_case==3:
                                                                t=ds[0][1:-4]
                                                                realtime=utc.localize(datetime.strptime(t, '%d %b %Y %H:%M'))
                                                                if realtime>end_converted:
                                                                    break
                                                                xx+=float(ds[3][1:])
                                                                yy+=float(ds[4][1:])
                                                                zz+=float(ds[5][1:])
                                                 
                                                            elif check_case==2 :
                                                                t=ds[0][1:-4]
                                                                realtime=utc.localize(datetime.strptime(t, '%d %b %Y %H:%M'))
                                                                if realtime>end_converted:
                                                                    break
                                                                xx+=float(ds[3][1:])
                                                                yy+=float(ds[4][1:])
                                                                zz+=float(ds[5][1:])
                                                     
                                                            if linecount==60: #take only averaged every 60s data
                                                                # selected_time=['00:00','06:00','12:00','18:00','23:59'] #only show selected time
                                                                t=t[-5:]
                                                                # if t in selected_time:
                                                                #     ts.append(t)
                                                                # else:
                                                                #     ts.append('0')
                                                                # t=datetime.strptime(t, '%d %b %Y %H:%M')
                                                                ts.append(t)
                                                                xs.append(xx/60)
                                                                ys.append(yy/60)
                                                                zs.append(zz/60)
                                                                xx=yy=zz=linecount=0
                                                            elif len(data)-totalcount==0 : #tail condition, if the data reaches the end but not 60
                                                                # if t in selected_time:
                                                                #     ts.append(t)
                                                                # else:
                                                                #     ts.append('0')
                                                                t=t[-5:]
                                                                ts.append(t)
                                                                xs.append(xx/linecount)
                                                                ys.append(yy/linecount)
                                                                zs.append(zz/linecount)
                                                                xx=yy=zz=linecount=0 
                                               
                                                except Exception as e: 
                                                    print(check_case)
                                                    print(e)
                                                    print(str(data[0],'UTF-8')[0])
                                except Exception as e: 
                                    print(e)
                    else:
                        print("not found!")
                    print(len(xs))

                    print(id)
                    print(name)
                    if len(xs)>1:
                        # print(xs[0:20])
                        if (abs(xs[0])/10<10):
                            xs=[x*1000 for x in xs]
                            ys=[y*1000 for y in ys]
                            zs=[z*1000 for z in zs]
                        # print(xs[0:20])
                        x_m=mean(xs)
                        y_m=mean(ys)
                        z_m=mean(zs)
                        # print(x_m)
                        xs=[x -x_m for x in xs]
                        ys=[y - y_m for y in ys]
                        zs=[z- z_m for z in zs]
                        # print(xs[0:20])
                        if id=='28': 
                            xxs=[z for z in zs]
                            zs=xs
                            xs=xxs
                        if id=='33':
                            temp=xs
                            xs=[z*-1 for z in zs]
                            zs=temp
                        if id=='4':
                            xs=[x*0.01 for x in xs]
                            ys=[y*0.01 for y in ys]
                            zs=[z*0.01 for z in zs]
                        if id=='3':
                            xs=[-10*x for x in xs]
                            ys=[-10*y for y in ys]
                            zs=[10*z for z in zs]
                            temp=xs
                            xs=zs
                            zs=temp
                        if id=='32':
                            ys=[y*-1 for y in ys]
                            temp=xs
                            xs=[z*-1 for z in zs]
                            zs=temp
                        datasets.append({'station_id': id, 'station_name':name,'station_address':address,'ts':ts,'xs':xs,'ys':ys,'zs':zs}) 
                        msg = 'Data plotted for selected stations on ' + start_datetime_str
                    else:
                        # Handle invalid date format
                        msg = 'Invalid date format.'
                else:
                    # If no date or stations provided
                    msg = 'Please select a date and at least one station.'
            else:
                # For GET request, you can redirect back or handle accordingly
                return redirect('analysis_map')

    return render(request, 'display_graphs.html', {
        'mapbox_access_token': mapbox_access_token,
        'datasets': datasets,
        'message': msg,
        'start': start_converted,
        'end': end_converted,
        'show_map': False,  # do not show the map when graphs are plotted
    })

def analysis_map(request):
    mapbox_access_token = settings.MAPBOX_ACCESS_TOKEN
    date_stations = None
    start_datetime_str = ''
    msg = ''

    if request.method == 'POST':
        # get start date from form data
        start_datetime_str = request.POST.get('start_datetime')
        if start_datetime_str:
            start_datetime = parse_datetime(start_datetime_str)
            #start_datetime -= timedelta(days=.1) # start slightly early in case observation starts early
            # Set end datetime as start + 24 hours (1 day) + a little extra in case observation ends late
            end_datetime = start_datetime + timedelta(days=1)
            # start_converted = utc.localize(datetime.strptime(start, '%Y-%m-%dT%H:%M'))
            # end_converted = start_converted + timedelta(days=0.9)
            if start_datetime:
                # filter observations based on the date
                observations_in_range = Observation.objects.filter(startDate__gte=start_datetime, endDate__lte=end_datetime)
                station_ids_with_observations = observations_in_range.values_list('station_id', flat=True).distinct()
                # filter stations that have observations in the given date range
                date_stations = Station.objects.filter(id__in=station_ids_with_observations, instrument__instrumenttype=3)
                msg = 'Stations active on ' + start_datetime_str
            else:
                # invalid date format
                date_stations = []
        else:
            # if no date provided, returnempty list
            date_stations = []
    
        return render(request, 'analysis_map.html', {
            'mapbox_access_token': mapbox_access_token,
            'selected_date': start_datetime_str,
            'date_stations': date_stations,
            'message' : msg,
            'show_map': True,  # show the map when graphs not present
        })
    
    return render(request, 'analysis_map.html', {
        'mapbox_access_token': mapbox_access_token,
        'date_stations': date_stations,
        'message' : msg,
        'show_map': True,  # show the map when graphs not present
    })  # no date yet