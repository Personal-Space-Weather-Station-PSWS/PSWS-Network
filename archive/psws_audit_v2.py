# ----------------------------------------------------------------------------
# Copyright (c) 2024 University of Alabama
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------


import os
from datetime import datetime as dt
from datetime import timezone
import re
from sys import argv

import pymysql
import pymysql.cursors


def log(path, message):
    """
    The function `log` appends a message to a file specified by the `path` parameter.
    
    :param path: The `path` parameter in the `log` function is the file path where you want to write the log message. It should be a string representing the file location on your system where you want to store the log information
    :param message: The `message` parameter in the `log` function is the text that you want to write to the log file specified by the `path` parameter
    """
    
    f = open(path, "a")
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

    db=pymysql.connect(host= dbhost, user= dbuser, password=dbpasswd, database=dbname, cursorclass=pymysql.cursors.DictCursor)
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

def fetch_obs_files(path):
    """
    The `fetch_obs_files` function filters out files in a specified directory path that start with the letter 'O' and returns a list of these observation files.
    
    :param path: The `fetch_obs_files` function you provided scans a specified directory path for files and filters out those whose names start with the letter 'O'. The function then returns a list of these observation files
    :return: The function `fetch_obs_files` returns a list of file names that start with the letter 'O' in the specified directory path.
    """
        
    obs_files= []
    for obs in os.scandir(path):
        # The line `if(obs.name[0] in {"O"}):` in the `fetch_obs_files` function is checking if the first character of the file name (`obs.name`) is equal to the letter 'O'. This condition is used to filter out files that start with the letter 'O' in the specified directory path. If the first character of the file name is 'O', the file name is added to the list of observation files (`obs_files`) that will be returned by the function.
        if(obs.name[0] in {"O"}):
            obs_files.append(obs.name)
    return obs_files

def fetch_db_data(db, station_id):
    """
    This function fetches file names from the observations_observation table in a database based on a given station_id.
    
    :param db: The `db` parameter is typically a connection object to a database. In this case, it seems to be a connection to a MySQL database. The function `fetch_db_data` takes this database connection object and a `station_id` as input parameters. It then executes a SQL query to fetch the
    :param station_id: The `station_id` parameter is used to specify the ID of the station for which you want to fetch data from the database. This ID is typically a unique identifier assigned to each station in the database
    :return: The function `fetch_db_data` returns a list of dictionaries containing the file names of observations associated with the specified `station_id` from the database.
    """

    cursor= db.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT fileName FROM observations_observation WHERE station_id='" + station_id + "'")
    result= cursor.fetchall()
    return result

def obs_exists(db, obs, station_id):
    """
    The function checks if a specific observation file exists for a given station ID in a database.
    
    :param db: The `db` parameter is typically a connection to a database that allows you to interact with it using SQL queries. It is used to execute SQL commands and retrieve data from the database
    :param obs: The `obs` parameter in the `obs_exists` function represents the file name of the observation file you are checking for existence in the database. It is used in the SQL query to search for a specific observation file in the `observations_observation` table based on the `fileName` column
    :param station_id: The `obs_exists` function takes three parameters: `db`, `obs`, and `station_id`. The `station_id` parameter is used to filter the observations based on the station ID when querying the database table `observations_observation`
    :return: the result of the SQL query executed on the database. The result will indicate whether there are any observations with the given file name (`obs`) associated with the specified `station_id` in the `observations_observation` table.
    """
    
    cursor= db.cursor()
    result= cursor.execute("SELECT * FROM observations_observation WHERE station_id='" + station_id + "' AND fileName='" + obs +"'")
    return result

def main():
    # Checks for Flag
    try:
        FLAG = argv[1]
    except(IndexError):
        print("Usage: python3 obs_audit_v2.py -FLAG ")
        print("Use -h for all possible flags")
        return
    
    # Test Environmental Variables
    TESTHOST= "localhost"
    TESTUSER= "root"
    TESTPASSWD= "root"
    TESTDB= "prod"

    # Production Environmental Variables
    HOST= "[readacted]"
    USER= "[redacted]"
    PASSWD= "[redacted]"
    DB= "[redacted]"

    # Other Environmental Variables
    PSWS_DB= load_db(HOST, USER, PASSWD, DB)
    ROOTDIRS= {'/home/', '/home/stations/'}
    TIMESTAMP = dt.now(timezone.utc).isoformat()[0:19]
    BASE_LOG_DIR= "/home/audit_logs/"
    TRIGGERNDB= BASE_LOG_DIR + "trigger_in_db_" + TIMESTAMP[0:10] + ".log"
    TRIGGERDNE= BASE_LOG_DIR + "trigger_not_in_db_" + TIMESTAMP[0:10] + ".log"
    OBSDNE= BASE_LOG_DIR + "obs_not_in_db_" + TIMESTAMP[0:10] + ".log"
    MAGDNE= BASE_LOG_DIR + "mag_not_in_db_" + TIMESTAMP[0:10] +".log"
    NODATA= BASE_LOG_DIR + "no_obs_data_" + TIMESTAMP[0:10] + ".log"
    
    # Checks for log directory. Creates it if DNE
    if(not os.path.isdir(BASE_LOG_DIR)):
        os.mkdir(BASE_LOG_DIR)

    print("Audit Started At: " + TIMESTAMP)
    
    # -a for all audits
    if(FLAG == "-a"):
        # Goes through both jailed and unjailed stations
        for rootdir in ROOTDIRS:
            station_dirs=fetch_STATIONsubdirs(rootdir)

            print("\nStarting Audit in Directory: " + rootdir)
            print("Progress ", end='')

            for dir in station_dirs:
                # Station ID, as reflected in the Database
                station_id=  dir[-6:]


                #############################################                         
                #           Trigger File Audit              #
                #############################################

                # pulls all the trigger files found within station directory
                tfs= fetch_trigger_files(dir)
                for tf in tfs:
                    # Observation Name as reflected in Database
                    obs_name= tf[1:20]
                    
                    # Conditional Logic for determining if the trigger file is reflected within the Database or not
                    if(obs_exists(PSWS_DB, obs_name, station_id)):
                        log(TRIGGERNDB, os.path.abspath(dir) + "/" + tf)
                    else:
                        log(TRIGGERDNE, os.path.abspath(dir) + "/" + tf)
                

                #############################################                         
                #              OBS File Audit               #
                #############################################

                # pulls all the observation data files found within station directory
                obs= fetch_obs_files(dir)
                for ob in obs:
                    # Conditional Logic for determining if the observation data file is not reflected in the database
                    if(not obs_exists(PSWS_DB, ob, station_id)):
                        log(OBSDNE, os.path.abspath(dir) + "/" + ob)
                

                #############################################                         
                #              OBS Data Audit               #
                #############################################

                # pulls all the recorded observations in db for a given station
                db_station_obs= fetch_db_data(PSWS_DB, station_id)
                # pulls all the observation data files found within station directory
                station_obs= fetch_obs_files(dir)

                for ob in db_station_obs:
                    ob_name= ob.get("fileName")
                    if(not ob_name[-4:] == ".zip"):
                        if(not ob_name in station_obs):
                            log(NODATA, "Station: " + dir[-7:] + "\t Observation: " + ob_name)
                
                # Progress Indicator, marching dots
                print(".", end='')
            print()
    
    # -t for trigger file audit only
    elif(FLAG == "-t"):
        # Goes through both jailed and unjailed stations
        for rootdir in ROOTDIRS:
            station_dirs= fetch_STATIONsubdirs(rootdir)

            print("\nStarting Audit in Directory: " + rootdir)
            print("Progress ", end='')

            # Iteration through every station directory
            for dir in station_dirs:
                # Station ID, as reflected in the Database
                station_id= dir[-6:]

                # pulls all the trigger files found within station directory
                tfs= fetch_trigger_files(dir)
                for tf in tfs:
                    # Observation Name as reflected in Database
                    obs_name= tf[1:20]
                    
                    # Conditional Logic for determining if the trigger file is reflected within the Database or not
                    if(obs_exists(PSWS_DB, obs_name, station_id)):
                        log(TRIGGERNDB, os.path.abspath(dir) + "/" + tf)
                    else:
                        log(TRIGGERDNE, os.path.abspath(dir) + "/" + tf)
                
                # Progress Indicator, marching dots
                print(".", end='')
            print()
    
    # -o for OBS file audit only
    elif(FLAG == "-o"):
        # Goes through both jailed and unjailed stations
        for rootdir in ROOTDIRS:
            station_dirs= fetch_STATIONsubdirs(rootdir)

            print("\nStarting Audit in Directory: " + rootdir)
            print("Progress ", end='')

            # Iteration through every station directory
            for dir in station_dirs:
                # Station ID, as reflected in the Database
                station_id= dir[-6:]

                # pulls all the observation data files found within station directory
                obs= fetch_obs_files(dir)
                for ob in obs:
                    # Conditional Logic for determining if the observation data file is not reflected in the database
                    if(not obs_exists(PSWS_DB, ob, station_id)):
                        log(OBSDNE, os.path.abspath(dir) + "/" + ob)
                # Progress Indicator, marching dots
                print(".", end='')
            print()
    
    # -m if for MagData file audit only
    elif(FLAG == "-m"):
        print("Magdata File Audit Unavailable Using psws_audit_v2.py")
    
    # -d for OBS data audit only
    elif(FLAG == "-d"):
        # Goes through both jailed and unjailed stations
        for rootdir in ROOTDIRS:
            station_dirs= fetch_STATIONsubdirs(rootdir)

            print("\nStarting Audit in Directory: " + rootdir)
            print("Progress ", end='')

            for dir in station_dirs:
                # Station ID, as reflected in the Database
                station_id= dir[-6:]

                # pulls all the recorded observations in db for a given station
                db_station_obs= fetch_db_data(PSWS_DB, station_id)
                # pulls all the observation data files found within station directory
                station_obs= fetch_obs_files(dir)

                for ob in db_station_obs:
                    ob_name= ob.get("fileName")
                    if(not ob_name[-4:] == ".zip"):
                        if(not ob_name in station_obs):
                            log(NODATA, "Station: " + dir[-7:] + "\t Observation: " + ob_name)
                # Progress Indicator, marching dots
                print(".", end='')
            print()

    # -z for Magdata audit only
    elif(FLAG == "-z"):
        print("Magdata Audit Unavailable Using psws_audit_v2.py")

    # -h for Flag options
    elif(FLAG == "-h"):
        print("-a \t Run All Audits")
        print("-t \t Run Trigger File Audit")
        print("-o \t Run OBS File Audit")
        print("-m \t Run MagData File Audit")
        print("-d \t Run OBS Data Audit")
        print("-z \t Run Magdata Audit")
        print("-h \t Flag Help")

    # Handles Flag Usage Error
    else:
        print("Usage: python3 obs_audit_v2.py -FLAG ")

    
    FINISHTIME= dt.now(timezone.utc).isoformat()[0:19]
    print("\nAudit Finished At: " + FINISHTIME)

if __name__ == "__main__":
    main()
