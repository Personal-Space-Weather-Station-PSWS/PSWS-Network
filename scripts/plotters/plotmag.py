# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import sys
import argparse
import os
from datetime import datetime
import zipfile

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Django bootstrap to set up environment for Database access
from _bootstrap_django import bootstrap 
bootstrap() 

from observations.models import Observation
from stations.models import Station

def writeLog(theMessage):
    timestamp = datetime.now().isoformat()[0:19]
    with open("/var/log/watchdog/watchdog.log", "a") as f:
        f.write(timestamp + " " + theMessage + "\n")


def open_maybe_zip(path):
    """
    Returns:
        file-like object
        filename inside zip (or actual filename)
    """
    if path.endswith(".zip"):
        z = zipfile.ZipFile(path, 'r')
        # Use first file in archive
        name = z.namelist()[0]
        f = z.open(name)
        return f, name
    else:
        return open(path, 'rb'), os.path.basename(path)


def load_dataframe(path):
    f, inner_name = open_maybe_zip(path)

    first = f.read(1)
    f.seek(0)

    if first == b'{':
        df = pd.read_json(f, lines=True)
        bx, by, bz = 'x', 'y', 'z'
    else:
        names = ['ts', 'rt', 'lt', 'x', 'y', 'z', 'rx', 'ry', 'rz', 'Tm']
        df = pd.read_csv(f, names=names)
        bx, by, bz = 'x', 'y', 'z'

    f.close()
    return df, inner_name, bx, by, bz


# ---------------------------------------------------
# MAIN WORKFLOW
# ---------------------------------------------------
def main(path, station, date, lat, lon, grid, nick, event_src_path=None, instrument_id=None):
    plot_output_path = "/psws/psws/media/plots/mag"

    if event_src_path:
        writeLog('plotmag called with event: ' + event_src_path)
        stationIDstr = event_src_path.rsplit('/')[-2]
        instrumentID = event_src_path.rsplit('_#')[1]
        filename = event_src_path.rsplit('_#')[0].rsplit('/')[-1]
    else:
        stationIDstr = station
        instrumentID = instrument_id
        filename = os.path.basename(path)

    writeLog(f'Processing magnetometer data for station {stationIDstr}')

    df, actual_filename, bx, by, bz = load_dataframe(path)

    df['ts'] = pd.to_datetime(df['ts'], format='%d %b %Y %H:%M:%S')
    df = df.set_index('ts')
    df_avg = df.resample('10min').mean().dropna()

    fig, ax1 = plt.subplots(figsize=(10, 6))

    title_line1 = f"Magnetometer Station {station}  {date}"
    title_line2 = f"lat. {lat}  long {lon}  grid {grid}  Nickname {nick}"

    fig.suptitle(title_line1 + '\n' + title_line2, fontsize=11, ha='center', y=0.98)

    ax1.plot(df_avg.index, df_avg[bx], color='tab:red', label='Bx')
    ax1.set_ylabel('Bx (nT)', color='tab:red')
    ax1.tick_params(axis='y', labelcolor='tab:red')

    ax2 = ax1.twinx()
    ax2.plot(df_avg.index, df_avg[by], color='tab:blue', label='By')
    ax2.set_ylabel('By (nT)', color='tab:blue')
    ax2.tick_params(axis='y', labelcolor='tab:blue')

    ax3 = ax1.twinx()
    ax3.spines['right'].set_position(('outward', 60))
    ax3.plot(df_avg.index, df_avg[bz], color='tab:green', label='Bz')
    ax3.set_ylabel('Bz (nT)', color='tab:green')
    ax3.tick_params(axis='y', labelcolor='tab:green')

    ax1.set_xlabel('Time (UTC)')
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    ax1.xaxis.set_major_locator(mdates.HourLocator(interval=2))
    fig.autofmt_xdate()

    start_of_day = df_avg.index[0].normalize()
    end_of_day = start_of_day + pd.Timedelta(days=1)
    ax1.set_xlim((start_of_day, end_of_day))

    ax1.yaxis.set_major_locator(ticker.MultipleLocator(10))
    ax2.yaxis.set_major_locator(ticker.MultipleLocator(10))
    ax3.yaxis.set_major_locator(ticker.MultipleLocator(10))

    ax1.grid(True, linestyle=':')
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    output_filename = f"{stationIDstr}_{instrumentID}_{date}_{grid}.png"
    output_full_path = os.path.join(plot_output_path, output_filename)

    writeLog(f'Saving plot as: {output_filename}')
    plt.savefig(output_full_path, dpi=300)
    plt.close('all')

    try:
        writeLog(f'Updating database for station {stationIDstr}, instrument {instrumentID}, file {filename}')

        theStationQS = Station.objects.filter(station_id=stationIDstr)
        if theStationQS.exists():
            station_id = theStationQS.values()[0]['id']

            theObsQS = Observation.objects.filter(
                station_id=station_id,
                instrument_id=instrumentID,
                fileName=actual_filename  
            )

            if theObsQS.exists():
                writeLog(f'Updating observation with plot at: {plot_output_path}/{output_filename}')
                obs_id = theObsQS.values()[0]["id"]
                obs_instance = Observation.objects.get(id=obs_id)
                obs_instance.plotFile = output_filename
                obs_instance.plotPath = plot_output_path
                obs_instance.save()
                writeLog('Database update successful')
                print("Database update successful")
            else:
                writeLog(f'WARNING: No observation found for station {station_id}, instrument {instrumentID}, file {actual_filename}')
                print(f'WARNING: No observation found in database')
        else:
            writeLog(f'WARNING: Station {stationIDstr} not found in database')
            print(f'WARNING: Station not found in database')

    except Exception as e:
        writeLog(f'ERROR updating database: {str(e)}')
        print(f'ERROR updating database: {str(e)}')



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plot magnetometer data')
    parser.add_argument('path', help='Path to log file OR zip file')
    parser.add_argument('--station', required=True, help='Station ID')
    parser.add_argument('--date', required=True, help='Date (YYYY-MM-DD)')
    parser.add_argument('--lat', required=True, help='Latitude')
    parser.add_argument('--long', required=True, help='Longitude')
    parser.add_argument('--grid', required=True, help='Grid identifier')
    parser.add_argument('--nick', required=True, help='Nickname')
    parser.add_argument('-e', '--event', help='Event source path from watchdog')
    parser.add_argument('-i', '--instrument', help='Instrument ID (required if not using event)')

    args = parser.parse_args()

    main(
        args.path, args.station, args.date,
        args.lat, args.long, args.grid, args.nick,
        args.event, args.instrument
    )
