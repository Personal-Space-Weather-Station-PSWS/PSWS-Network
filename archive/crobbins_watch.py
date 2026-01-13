import sys
import tarfile
import re
import subprocess

from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

import h5py
import digital_rf as drf
from datetime import datetime

from sqlalchemy import create_engine

from urllib.parse import quote_plus

#connect the database
engine = "[redacted]"

class UploadEvent(PatternMatchingEventHandler):
    def __init__(self, patterns=None):
        super(UploadEvent, self).__init__(patterns=patterns)

    def on_created(self, event):
        #Begin by identifying if continuous or not
        #Then locating the path of the event
        if event.src_path.rsplit('/')[3][0] == 'd':
            print("D!")
            path = event.src_path
            channelPath = event.src_path + "/ch0"
            uploadType = 'd'
        elif event.src_path.rsplit('/')[3][0] == 'c':
            print("C!")
            path = "/" + event.src_path.rsplit('/')[1] + "/" + event.src_path.rsplit('/')[2] \
                    + "/" + event.src_path.rsplit('/')[3]
            channelPath = path + "/ch0"
            uploadType = 'c'
        else:
            print("Error! Neither D or C!")
            return

        #Extracting tar file if a D file        
        if uploadType == 'd':
            #Request ID will be at the end of the path, findall returns a list so need to take the first 
            #(and ideally only) match before stripping the newline
            rID = re.findall("d[0-9]+", path)[0][1:]
            print("Directory Created with ID of " + rID)

            #Now need to grab the location of the tarfile
            datapath = '/' + event.src_path.rsplit('/')[1] + '/' + event.src_path.rsplit('/')[2] + '/tangerine_data/'
            print('datapath:'+datapath)
            #Grep for upload in the folder using the stripped rID
            rawfile = subprocess.check_output('ls ' + datapath + ' | grep d' + rID + '.tar', shell=True)
            #Decode output from bytestring and strip newline
            tar_file = rawfile.decode()[:-1]
            print('tarfile:'+tar_file)
            
            #Now need to set up the tar file
            data = tarfile.open(datapath + tar_file)

            #Take time to calculate size for later before extracting
            size = 0
            for mem in data.getmembers():
                size = size + mem.size

            #Finish extracting tarfile
            data.extractall(path=path) #Extracts to the d# directory
            data.close()
        #Else a C file
        else:
            size = 0
            tar_file = 'none'
            
        #Scrape the metadata from the properties files
        fp = h5py.File(channelPath + '/drf_properties.h5')
        afp = h5py.File(channelPath + '/aux_drf_properties.h5')

        # Getting start time and end time
        drf_data = drf.DigitalRFReader(path)
        startDate, endDate = drf_data.get_bounds('ch0')
        # Converting from Unix time to datetime

        #All needed fields for insertion
        dataRate = fp.attrs.get('sample_rate_numerator')
        centerFrequency = 0 #How to calculate?
        size = size #Calculated earlier
        fileName = tar_file
        path = path
        station_id = path.rsplit('/')[2]
        ### Patch for demo
        station_id = station_id[-1]

        startDate = datetime.fromtimestamp(startDate / dataRate).strftime('%Y-%m-%d %H:%M:%S')
        endDate = datetime.fromtimestamp(endDate / dataRate).strftime('%Y-%m-%d %H:%M:%S')
        
        #Finally, we can insert into the db
        conn = engine.connect()
        statement_prefix = 'INSERT INTO observations_observation '
        
        #OLD Insertion
        #statement_cols = '(dataRate, centerFrequency, size, fileName, path, station_id)'
        #statement_vals_tuple = dataRate, centerFrequency, size, fileName, path, station_id

        #NEW Insertion
        #D insertion

        
        #if uploadType == 'd': 
        #    statement_cols = '(dataRate, centerFrequency, size, fileName, path, station_id, startDate, endDate)'
        #    statement_vals_tuple = dataRate, centerFrequency, size, fileName, path, station_id, startDate, endDate
        #else:
        #    statement_cols = '(dataRate, centerFrequency, size, fileName, path, station_id, startDate)'
        #    statement_vals_tuple = dataRate, centerFrequency, size, fileName, path, station_id, startDate
        
        if uploadType == 'd': 
            statement_cols = '(dataRate, size, fileName, path, station_id, startDate, endDate)'
            statement_vals_tuple = dataRate, size, fileName, datapath, station_id, startDate, endDate
        else:
            statement_cols = '(dataRate, size, fileName, path, station_id, startDate)'
            statement_vals_tuple = dataRate, size, fileName, path, station_id, startDate
            
        statement_vals = str(statement_vals_tuple)
        statement = statement_prefix + statement_cols + ' VALUES ' + statement_vals + ';'
        print(statement)
        conn.execute(statement)
        conn.close()

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else '/home'
    event_handler = UploadEvent(patterns=["N*/d*", "N*/c*/ch0/drf_properties.h5"])
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while observer.isAlive():
            observer.join(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join() 

