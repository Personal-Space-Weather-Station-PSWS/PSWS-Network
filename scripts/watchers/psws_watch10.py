# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------
# PSWS Watchdog - watches selected directories for creation of named subdirectories
# When the subdirectory is created, it means that a data upload is complete and
# ready to be cross-referenced into the PSWS database.
# Author: Cole Robbins, University of Alabama, 2021-2022
# Modifications by W. Engelke, May-July 2022, to add other functions & data types

# isort: skip_file
# ruff: noqa


from _bootstrap_django import bootstrap
import os
import sys
import time
import glob
import re
import subprocess
from pathlib import Path
from datetime import datetime as dt
from datetime import timezone

import pytz
import digital_rf as drf
from dotenv import load_dotenv
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers.polling import PollingObserver

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "psws"))  # Add project root to sys.path

env_path = REPO_ROOT / "scripts" / "scripts.env"
load_dotenv(dotenv_path=env_path)
bootstrap()


LOG_PATH = os.getenv("LOG_PATH")
PYTHON_EXECUTABLE = os.getenv("PYTHON_EXECUTABLE", sys.executable)

if not LOG_PATH:
    raise EnvironmentError("LOG_PATH not set in scripts.env")

print(f"Using Python executable: {PYTHON_EXECUTABLE}")


def writeLog(theMessage):
    timestamp = dt.now(timezone.utc).isoformat()[0:19]
    f = open(LOG_PATH, "a")
    f.write(timestamp + " " + theMessage + "\n")
    f.close()


def get_size(start_path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(start_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            # skip if it is symbolic link
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    return total_size


class UploadEvent(PatternMatchingEventHandler):

    def on_created(self, event):
        print('event!')

        if event.src_path.rsplit('/')[-1] == 'm_Test':
            print("Test trigger seen!")
            writeLog("Test file seen at  " + event.src_path)
            print("Located at " + event.src_path)
            os.rmdir(event.src_path)
            print("Removed directory:" + event.src_path)
            time.sleep(1)
            return

        # Begin by identifying if continuous or not
        writeLog("trigger event:" + event.src_path)
        print("UPLOAD trigger at local time: " + dt.now().isoformat())

        try:
            instrumentNo = event.src_path.split("_#")[1]
            writeLog("Instrument number found at -> " +
                     event.src_path.split("_#")[1])
            print("Instrument number found at -> " +
                  event.src_path.split("_#")[1])
        except:
            print("ERROR, parsing failure, the '_#' not found")
            writeLog("ERROR - parsing failure, the '_#' not found")
            return

        writeLog("conditional string -> " + event.src_path.rsplit('/')[-1][0])

        # processing for Grape 1 Legacy (G1L) (fldigi) upload
        if event.src_path.rsplit('/')[-1][0] == 'g':
            writeLog("processing Grape 1 Legacy trigger:" + event.src_path)
            print('G1L trigger', event.src_path)
            observation_no = event.src_path.rsplit(
                '/')[-1][1:len(event.src_path)]
            observation_no = observation_no.rsplit('_#')[0]
            print("Observation#=" + observation_no)
            writeLog("Observation#=" + observation_no)
            path = "/".join(event.src_path.rsplit('/')
                            [:-1]) + '/csvData/' + observation_no
            writeLog("Path generated -> " + path)
            obsSize = get_size(path)
            stationID = observation_no.rsplit('_')[1]

            # if this is the 8-character node number, remove the leading zero
            if len(stationID) == 8:
                stationID = stationID[0] + stationID[2:8]
            writeLog("Station#=" + stationID)
            print("StationID=", stationID)
            instrumentID = event.src_path.rsplit('_#')[1]
            writeLog("Instrument#=" + instrumentID)
            trigger = event.src_path.rsplit('/')[4]
            writeLog("trigger=" + trigger)

            # Use PYTHON_EXECUTABLE environment variable
            cmd = f'{PYTHON_EXECUTABLE} psws_addCSV.py {
                path} {stationID} {instrumentID} {trigger}'
            writeLog("call to psws_addCSV cmd=" + cmd)
            print("psws_addCSV cmd:", cmd)
            os.system(cmd)

            # prepare command for plotting
            cmd = f'{PYTHON_EXECUTABLE} plotfldigi1.py -f {
                path} -e {event.src_path} -p /psws/psws/media/plots'
            writeLog('plot command=' + cmd)
            return

        # processing for Continuous type upload (Grape 1 DRF, including rx888)
        if event.src_path.rsplit('/')[-1][0] == 'c':
            writeLog("Processing trigger:" + event.src_path)
            observation_no = event.src_path.rsplit('/')[-1][1:20]
            path = "/".join(event.src_path.rsplit('/')
                            [:-1]) + '/' + observation_no
            print('path', path, 'observation no', observation_no)
            writeLog("Path generated -> " + path)
            obsSize = get_size(path)
            print("Data size=", obsSize)

            # prepare to get DRF metadata for inclusion into database
            channelPath = path + "/ch0"
            print("channel path=" + channelPath)
            uploadType = 'c'
            metadata_dir = channelPath + "/metadata"
            start_idx = 0

            try:
                dmr = drf.DigitalMetadataReader(metadata_dir)
                start_idx = dmr.get_bounds()[0]
                print("Start:", start_idx)
            except IOError as e:
                writeLog(
                    "IO error accessing digital metadata, path=" + metadata_dir)
                writeLog(str(e))
                return

            fields = dmr.get_fields()
            writeLog("Available fields are <%s>" % (str(fields)))
            print("Available DRF metadata fields are <%s>" % (str(fields)))
            freq_list = []

            # get list of center frequencies in this spectrum (often just 1)
            data_dict = dmr.read(start_idx, start_idx +
                                 2, "center_frequencies")
            writeLog("Center freq list:")
            for x in list(data_dict)[0:1]:
                freq_list = data_dict[x]
            print("Freq list:", freq_list)

            print('sample_rate_numerator:', dmr.read(
                start_idx, start_idx + 2, "sample_rate_numerator"))

            s_r_dict = dmr.read(start_idx, start_idx + 2,
                                "sample_rate_numerator")
            fkey, fval = next(iter(s_r_dict.items()))
            print('s_r_dict fkey fval', fkey, fval)
            dataRate = fval

            if not (os.path.isfile(channelPath + '/drf_properties.h5')):
                writeLog("DRF Properties file missing!")
                return

            if not (os.path.exists(channelPath)):
                writeLog(
                    "Channel path does not exist! Might be issue with parsing of trigger file name.")
                return

            if not (os.path.exists(channelPath + '/metadata/dmd_properties.h5')):
                writeLog("DMD Properties file missing!")
                return

            # Getting start time and end time
            drf_data = drf.DigitalRFReader(path)
            startDate, endDate = drf_data.get_bounds('ch0')
            print("bounds:", startDate, endDate)
            writeLog("Got Bounds")

            # All needed fields for insertion
            if uploadType == 'c':
                centerFrequency = freq_list[0]
            datapath = path
            fileName = observation_no
            station_id = path.rsplit('/')[-2]
            print("startDate:", startDate)
            print("dataRate:", dataRate)
            myTimestamp = startDate / dataRate

            startDate = dt.fromtimestamp(
                myTimestamp, tz=pytz.UTC).strftime('%Y-%m-%dT%H:%M')
            print("Start date:" + startDate)
            myTimestamp = endDate / dataRate
            endDate = dt.fromtimestamp(
                myTimestamp, tz=pytz.UTC).strftime('%Y-%m-%dT%H:%M')
            print("End date:" + endDate)

            # Use PYTHON_EXECUTABLE
            command = f"{PYTHON_EXECUTABLE} psws_addOBS.py {dataRate} {obsSize} {
                fileName} {datapath} {station_id} {instrumentNo} {startDate} {endDate}"
            for this_freq in freq_list:
                command = command + " " + str(this_freq)

            print("Issuing command:" + command)
            writeLog("Issuing command:" + command)
            args = command.split()
            subprocess.run(args)
            writeLog("Issued syscommand:" + command)

            try:
                writeLog("Trigger graphing  program")
                # Use PYTHON_EXECUTABLE for plotting
                graph_command = f"ts {PYTHON_EXECUTABLE} /var/www/html/plotspectrum_v8.py -e {
                    event.src_path} -p /psws/psws/media/plots"

                writeLog("Running graph_command ----> " + graph_command)
                os.system(graph_command)
                writeLog("Graphing command run!")

                # Removes target directory
                os.rmdir(event.src_path)
                writeLog("Removed directory:" + event.src_path)

            except Exception as ex:
                print("Exception: ", str(ex))
                writeLog("Exception: " + str(ex))

        # processing for "m" (magnetometer) type upload
# processing for "m" (magnetometer) type upload
        elif event.src_path.rsplit('/')[-1][0] == 'm':
            try:
                from apps.stations.models import Station
            except ImportError:
                from stations.models import Station
            mag_dir = '/'.join(event.src_path.rsplit('/')[:-1]) + '/magData'
            writeLog("Path generated -> " + mag_dir)

            station_id = mag_dir.rsplit('/')[-2]
            endDate = event.src_path[-16:]

            try:
                station_obj = Station.objects.filter(
                    station_id=station_id).first()
                if not station_obj:
                    writeLog(f"ERROR: Station {station_id} not found.")
                else:
                    # Gather candidates
                    candidates = glob.glob(os.path.join(mag_dir, "*.zip")) + \
                        glob.glob(os.path.join(mag_dir, "*.csv")) + \
                        glob.glob(os.path.join(mag_dir, "*.json"))

                    for fpath in sorted(candidates):
                        date_str = None
                        m = re.search(r"(\d{4}-\d{2}-\d{2})",
                                      os.path.basename(fpath))
                        date_str = m.group(1) if m else endDate[0:10]

                        # SUBPROCESS CALL STARTS HERE
                        # Construct path to the plotmag script relative to REPO_ROOT
                        plotmag_script = os.path.join(
                            REPO_ROOT, "scripts", "plotters", "plotmag.py")

                        plot_cmd = [
                            PYTHON_EXECUTABLE,
                            plotmag_script,
                            fpath,
                            "--station", station_id,
                            "--date", date_str,
                            "--lat", str(station_obj.latitude),
                            "--long", str(station_obj.longitude),
                            "--grid", station_obj.grid,
                            "--nick", station_obj.nickname,
                            "-i", instrumentNo
                        ]

                        writeLog(f"Executing: {' '.join(plot_cmd)}")

                        # Run the script; capture=True allows you to log errors if it fails
                        result = subprocess.run(
                            plot_cmd, capture_output=True, text=True)

                        if result.returncode != 0:
                            writeLog(f"Plotting failed: {result.stderr}")
                        else:
                            writeLog(f"Plotting successful: {result.stdout}")

            except Exception as e:
                writeLog(f"ERROR in magnetometer processing: {str(e)}")

            os.rmdir(event.src_path)
            return

        else:
            writeLog("ERROR. Unrecognized upload type: " +
                     event.src_path.rsplit('/')[-1][0])
            return


if __name__ == "__main__":
    print("starting watchdog, v10 (corrected)")
    writeLog("Watchdog 10 starting (corrected)")

    root = sys.argv[1] if len(sys.argv) > 1 else "/psws/home"
    root = os.path.abspath(root)

    print("Starting watchdog (polling, non-recursive S*/N*/T*)")
    writeLog("Watchdog polling starting at " + root)

    observer = PollingObserver(timeout=10.0)
    handler = UploadEvent()

    # Watch each existing S*, N*, T* directory directly under /psws/home
    for entry in os.scandir(root):
        if entry.is_dir() and entry.name[0] in ("T", "S", "N"):
            print("Watching:", entry.path)
            observer.schedule(handler, entry.path, recursive=False)

    observer.start()
    print("observer started")
    writeLog("Watchdog polling observer started")

    try:
        while True:
            time.sleep(2)
    finally:
        print("Stopping observer")
        observer.stop()
        observer.join()
