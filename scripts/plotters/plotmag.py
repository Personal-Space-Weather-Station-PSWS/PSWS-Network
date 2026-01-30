# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
from _bootstrap_django import bootstrap
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.ticker as ticker
import sys
import argparse
import os
from datetime import datetime
import zipfile
from dotenv import load_dotenv

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

env_path = Path(__file__).resolve().parent.parent / 'scripts.env'
load_dotenv(dotenv_path=env_path)
# Django bootstrap to set up environment for Database access
bootstrap()

PLOT_PATH = os.getenv("PLOT_PATH")
LOG_PATH = os.getenv("LOG_PATH")

if not PLOT_PATH:
    raise EnvironmentError("PLOT_PATH not set in scripts.env")
if not LOG_PATH:
    raise EnvironmentError("LOG_PATH not set in scripts.env")

# Then use them:
plot_output_path = os.path.join(PLOT_PATH, "mag")


def writeLog(theMessage):
    timestamp = datetime.now().isoformat()[0:19]
    with open(LOG_PATH, "a") as f:
        f.write(timestamp + " " + theMessage + "\n")


def open_maybe_zip(path):
    """
    Returns:
        file-like object
        filename inside zip (or actual filename)
    """
    if path.endswith(".zip"):
        z = zipfile.ZipFile(path, 'r')
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
        # Handle quoted CSV values with quotechar parameter
        df = pd.read_csv(f, names=names, quotechar='"', skipinitialspace=True)
        bx, by, bz = 'x', 'y', 'z'

    f.close()
    return df, inner_name, bx, by, bz


def plot_magnetometer(path, station, date, lat, lon, grid, nick, instrument_id):
    """
    Plot magnetometer data from a file.

    Args:
        path: Path to magnetometer data file (zip or raw)
        station: Station ID (e.g., 'N000015')
        date: Date string (YYYY-MM-DD)
        lat: Latitude (float or string)
        lon: Longitude (float or string)
        grid: Maidenhead grid
        nick: Station nickname
        instrument_id: Instrument ID

    Returns:
        output_full_path: Path to generated plot file, or None on error
    """
    from apps.stations.models import Station
    from apps.observations.models import Observation
    try:
        writeLog(f'plot_magnetometer called for station {
                 station}, file {path}')

        os.makedirs(plot_output_path, exist_ok=True)

        stationIDstr = station
        instrumentID = instrument_id
        filename = os.path.basename(path)

        df, actual_filename, bx, by, bz = load_dataframe(path)
        parse_success = False

        if isinstance(df['ts'].iloc[0], str):
            df['ts'] = df['ts'].str.strip().str.strip('"')
            writeLog(f"After stripping quotes: {df['ts'].iloc[0]}")

        try:
            df['ts'] = pd.to_datetime(df['ts'], format='%d %b %Y %H:%M:%S')
            parse_success = True
            writeLog(
                "Successfully parsed timestamps with format '%d %b %Y %H:%M:%S'")
        except Exception as e:
            writeLog(f"First parse attempt failed: {str(e)}")
            try:
                df['ts'] = pd.to_datetime(df['ts'])
                parse_success = True
                writeLog(
                    "Successfully parsed timestamps with pandas auto-detection")
            except Exception as e2:
                writeLog(f"Second parse attempt failed: {str(e2)}")

        if not parse_success:
            writeLog("ERROR: Could not parse timestamps")
            return None

        writeLog(f"Date range: {df['ts'].min()} to {df['ts'].max()}")

        df = df.set_index('ts')

        writeLog(f"NaN counts before resampling - x: {df[bx].isna().sum()}, y: {
                 df[by].isna().sum()}, z: {df[bz].isna().sum()}")

        df_avg = df.resample('10min').mean()

        writeLog(f"After resampling (before dropna): {len(df_avg)} rows")
        writeLog(f"NaN counts after resampling - x: {df_avg[bx].isna().sum()}, y: {
                 df_avg[by].isna().sum()}, z: {df_avg[bz].isna().sum()}")

        df_avg = df_avg.dropna(subset=[bx, by, bz], how='all')

        writeLog(f"After resampling: {len(df_avg)} rows")

        if df_avg.empty:
            writeLog(
                "ERROR: No data after resampling. All magnetometer values are NaN.")
            return None

        fig, ax1 = plt.subplots(figsize=(10, 6))

        title_line1 = f"Magnetometer Station {station}  {date}"
        title_line2 = f"lat. {lat}  long {lon}  grid {grid}  Nickname {nick}"

        fig.suptitle(title_line1 + '\n' + title_line2,
                     fontsize=11, ha='center', y=0.98)

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

        for ax in (ax1, ax2, ax3):
            ax.yaxis.set_major_locator(ticker.LinearLocator(20))
            ax.yaxis.set_major_formatter(ticker.ScalarFormatter())
            ax.ticklabel_format(axis='y', style='plain', useOffset=False)

        ax1.grid(True, linestyle=':')
        plt.tight_layout(rect=[0, 0, 1, 0.96])

        output_filename = f"{stationIDstr}_{instrumentID}_{date}_{grid}.png"
        output_full_path = os.path.join(plot_output_path, output_filename)

        writeLog(f'Saving plot as: {output_filename}')
        plt.savefig(output_full_path, dpi=300)
        plt.close('all')

        # Update database
        try:
            writeLog(f'Updating database for station {
                     stationIDstr}, instrument {instrumentID}, file {filename}')

            theStationQS = Station.objects.filter(station_id=stationIDstr)
            if theStationQS.exists():
                station_id = theStationQS.values()[0]['id']

                theObsQS = Observation.objects.filter(
                    station_id=station_id,
                    instrument_id=instrumentID,
                    fileName=actual_filename
                )

                if theObsQS.exists():
                    writeLog(f'Updating observation with plot at: {
                             plot_output_path}/{output_filename}')
                    obs_id = theObsQS.values()[0]["id"]
                    obs_instance = Observation.objects.get(id=obs_id)
                    obs_instance.plotFile = output_filename
                    obs_instance.plotPath = plot_output_path
                    obs_instance.save()
                    writeLog('Database update successful')
                else:
                    writeLog(f'WARNING: No observation found for station {
                             station_id}, instrument {instrumentID}, file {actual_filename}')
            else:
                writeLog(f'WARNING: Station {
                         stationIDstr} not found in database')

        except Exception as e:
            writeLog(f'ERROR updating database: {str(e)}')

        return output_full_path

    except Exception as e:
        writeLog(f'ERROR in plot_magnetometer: {str(e)}')
        import traceback
        writeLog(traceback.format_exc())
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Plot magnetometer data')
    parser.add_argument('path', help='Path to log file OR zip file')
    parser.add_argument('--station', required=True, help='Station ID')
    parser.add_argument('--date', required=True, help='Date (YYYY-MM-DD)')
    parser.add_argument('--lat', required=True, help='Latitude')
    parser.add_argument('--long', required=True, help='Longitude')
    parser.add_argument('--grid', required=True, help='Grid identifier')
    parser.add_argument('--nick', required=True, help='Nickname')
    parser.add_argument('-i', '--instrument',
                        required=True, help='Instrument ID')

    args = parser.parse_args()

    # Call the main plotting function
    result = plot_magnetometer(
        args.path, args.station, args.date,
        args.lat, args.long, args.grid, args.nick,
        args.instrument
    )

    if result:
        print(f"Plot saved to: {result}")
    else:
        print("Plotting failed - check logs")
        sys.exit(1)
