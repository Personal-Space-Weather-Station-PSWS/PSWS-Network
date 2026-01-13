# ----------------------------------------------------------------------------
# Copyright (c) 2024 University of Alabama
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------

from datetime import datetime as dt
from datetime import timezone
import pymysql
import os

def log(message):
    """
    The function `log` appends a message to a log file located at "/var/www/html/audit.log".
    
    :param message: The `log` function you provided takes a `message` parameter, which is a string containing the information you want to log. This function appends the message to a log file located at "/var/www/html/audit.log"
    """
        
    LOG_PATH="audit.log"
    f = open(LOG_PATH, "a")
    f.write(message + "\n")
    f.close()

def load_db(dbhost, dbuser, dbpasswd, dbname):
    """
    The function `load_db` connects to a MySQL database using the provided host, user, password, and database name.
    
    :param dbhost: The `dbhost` parameter in the `load_db` function is the hostname or IP address of the database server to which you want to connect
    :param dbuser: The `dbuser` parameter in the `load_db` function is the username used to connect to the database. It is typically a string that represents the username of the database user who has permission to access the specified database
    :param dbpasswd: The `dbpasswd` parameter in the `load_db` function is used to specify the password required to connect to the database. This password is typically used for authentication purposes to ensure that only authorized users can access the database. Make sure to keep this password secure and not expose it in any public or
    :param dbname: The `dbname` parameter in the `load_db` function represents the name of the database that you want to connect to. This is the database where you want to establish a connection using the provided host, user, and password credentials
    :return: The function `load_db` is returning a connection to a MySQL database using the provided host, user, password, and database name.
    """

    db=pymysql.connect(host= dbhost, user= dbuser, password=dbpasswd, database=dbname)
    return db

def fetch_STATIONsubdirs(path):
    """
    The function `fetch_STATIONsubdirs` scans a given directory for subdirectories whose names start with either 'N' or 'S' and returns a list of those subdirectories.
    
    :param path: The `fetch_STATIONsubdirs` function you provided seems to be incomplete. It looks like you are trying to fetch subdirectories in a given path that start with either 'N' or 'S'. However, the `os` module and the path variable are not imported or defined in the code
    :return: The function `fetch_STATIONsubdirs` returns a list of subdirectories within the specified `path` that have names starting with either 'N' or 'S'.
    """
    
    subdirs=[]
    for subdir in os.scandir(path):
        subdir_path= os.path.join(subdir)
        # The line `if(subdir_path.split("/")[-1][0] == 'N' or subdir_path.split("/")[-1][0] == 'S'):` is checking if the first character of the last component of the `subdir_path` matches either 'N' or 'S'. Here is a breakdown of what each part of the line is doing:
        if(subdir_path.split("/")[-1][0] == 'N' or subdir_path.split("/")[-1][0] == 'S'):
            subdirs.append(subdir_path)
    return subdirs

def fetch_trigger_files(path):
    """
    The function fetches trigger files from a specified directory based on a specific condition.
    
    :param path: The `path` parameter in the `fetch_trigger_files` function is the directory path where you want to search for trigger files. This function will scan the specified directory and return a list of trigger files whose names start with the letter 'c'
    :return: The function `fetch_trigger_files` returns a list of file names that start with the letter "c" in the specified directory path.
    """

    trigger_files= []
    for tf in os.scandir(path):
        # The line `if(tf.name[0] in {"c"}):` is checking if the first character of the file name (`tf.name`) is equal to the letter 'c'.
        if(tf.name[0] in {"c"}):
            trigger_files.append(tf.name)
    return trigger_files

def obs_exists(db, obs, station_id):
    """
    The function `obs_exists` checks if a specific observation file exists for a given station ID in a database.
    
    :param db: The `db` parameter is likely a database connection object that allows you to interact with a database. In this case, it seems to be used to execute a SQL query to check if a specific observation file exists for a given station ID in a table named `observations_observation`
    :param obs: The `obs` parameter in the `obs_exists` function represents the filename of an observation file. This function is designed to check if a specific observation file exists in the database for a given `station_id`
    :param station_id: The `station_id` parameter is likely a unique identifier for a weather station where observations are recorded. It is used in the `obs_exists` function to query the database for a specific observation file (`obs`) associated with a particular station
    :return: the result of the SQL query executed on the database. The result will be the records from the observations_observation table where the station_id matches the provided station_id and the filename matches the provided obs.
    """

    cursor= db.cursor()
    result= cursor.execute("SELECT * FROM observations_observation WHERE station_id='" + station_id + "' AND filename='" + obs +"'")
    return result

def main():
    # Environmental Variables
    HOST= "[redacted]"
    USER= "[redacted]"
    PASSWD= "[redacted]"
    DB= "[redacted]"
    PSWS_DB= load_db(HOST, USER, PASSWD, DB)

    timestamp = dt.now(timezone.utc).isoformat()[0:19]
    print("Observation Audit Started At: " + timestamp)
    log("Observation Audit Started At: " + timestamp)
    log("")

    rootdirs= {'/home/', '/home/stations/'}
    for rootdir in rootdirs:
        station_dirs= fetch_STATIONsubdirs(rootdir)
        for dir in station_dirs:
            log("looking in directory --> " + dir)
            tfs= fetch_trigger_files(dir)
            if(len(tfs)==0):
                log("no trigger files in " + dir)
                log("")
            for tf in tfs:
                obs_name= tf[1:20]
                station_id= dir[-3:]
                log("trigger file found --> " + tf)
                log("looking in database for --> "+ obs_name + " under STATION_ID: " + station_id)
                if(obs_exists(PSWS_DB, obs_name, station_id)):
                    log(obs_name + " --> FOUND")
                    log("")
                else:
                    log(obs_name + " --> NOT FOUND")
                    log("")
    
    print("Audit Finished")
    log("")
            
    

if __name__ == "__main__":
    main()