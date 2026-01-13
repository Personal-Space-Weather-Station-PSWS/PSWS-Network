# ----------------------------------------------------------------------------
# Copyright (c) 2026 University of Alabama, Digital Forensics and Control Systems Security Lab (DCSL)
# All rights reserved.
#
# Distributed under the terms of the BSD 3-clause license.
#
# The full license is in the LICENSE file, distributed with this software.
# ----------------------------------------------------------------------------

import os
from datetime import datetime as dt
from datetime import timezone
from sys import argv

def log(message):
    """
    The `log` function appends a message to a log file located at "/var/www/html/triggerManip.log".
    
    :param message: The `log` function you provided takes a `message` parameter, which is a string
    containing the information you want to log. This message will be written to a log file named
    "triggerManip.log" located at "/var/www/html/"
    """
    
    f = open("/var/www/html/triggerManip.log", "a")
    f.write(message + "\n")
    f.close()

def load_logfile(filename):
    """
    The function `load_logfile` attempts to open a specified file in read mode and returns the file
    object, handling IOError exceptions by printing an error message and exiting the program.
    
    :param filename: The `filename` parameter in the `load_logfile` function is a string that represents
    the name of the log file that you want to load and read
    :return: The function `load_logfile` is returning the opened file object `file` if the file is
    successfully opened.
    """
    
    try:
        file= open(filename, "r")
        return file
    except IOError:
        print("Error: " + filename + " not found")
        log("Error: " + filename + " not found")
        exit()

def delete_triggers(filename):
    """
    The function `delete_triggers` reads a log file containing trigger file names, removes the newline
    characters, and then deletes each trigger file from the server.
    
    :param filename: It looks like you have provided a code snippet for a function called
    `delete_triggers` that reads trigger file names from a log file, removes the corresponding trigger
    files from the server, and logs the number of trigger files processed and removed
    """
    
    file= load_logfile(filename)
    triggerfiles= file.readlines()
    num_triggerfiles= len(triggerfiles)
    print("Number of TriggerFiles in File --> " + str(num_triggerfiles))
    log("Number of TriggerFiles in File --> " + str(num_triggerfiles))
    # Strips the newline(\n) character from end of each log entry
    for i in range(num_triggerfiles):
        triggerfiles[i] = triggerfiles[i].strip("\n")
    # Removes each triggerfile from the server
    count=0
    for triggerfile in triggerfiles:
        os.rmdir(triggerfile)
        count+=1
    print("Number of TriggerFiles Removed --> " + str(count))
    log("Number of TriggerFiles Removed --> " + str(count))

def create_triggers(filename):
    """
    The function `create_triggers` reads a log file, extracts trigger file paths, creates directories
    based on these paths, and logs the number of trigger files processed and created.
    
    :param filename: It looks like the code snippet you provided is a function `create_triggers` that
    reads a logfile, processes the trigger files listed in the logfile, and creates directories based on
    the trigger file paths
    """
    
    file= load_logfile(filename)
    triggerfiles= file.readlines()
    num_triggerfiles= len(triggerfiles)
    print("Number of TriggerFiles in File --> " + str(num_triggerfiles))
    log("Number of TriggerFiles in File --> " + str(num_triggerfiles))
    # Strips the newline(\n) character from end of each log entry
    for i in range(num_triggerfiles):
        triggerfiles[i] = triggerfiles[i].strip("\n")
    # Adds each triggerfile based on path in Log for Watchdog to catch
    count=0
    for triggerfile in triggerfiles:
        os.mkdir(triggerfile)
        count+=1
    print("Number of TriggerFiles Created --> " + str(count))
    log("Number of TriggerFiles Created --> " + str(count))

def delete_log(filename):
    """
    The function `delete_log` deletes a specified file and logs the deletion action.
    
    :param filename: The `delete_log` function you provided takes a `filename` as a parameter. This
    function deletes the file with the specified `filename`, prints a message indicating that the file
    has been deleted, and logs this action using the `log` function
    """
    
    os.remove(filename)
    print("Deleted File --> " + filename)
    log("Deleted File --> " + filename)

def main():
    # Checks for Flag and Log File
    try:
        FLAG = argv[1]
        print("Flag used: " + FLAG)
        LOG_FILE= argv[2]
        print("Log File: " + LOG_FILE)
    except(IndexError):
        print("Usage: python3 psws_triggerMANIP.py -FLAG log_file.txt -d(optional)")
        print("Use -h for all possible flags")
        return
    
    # Checks for log deletion upon completion
    try:
        if(argv[3] == "-d"):
            DELETE_LOG= True
        else:
            DELETE_LOG= False
    except IndexError:
        DELETE_LOG= False
    
    TIMESTAMP = dt.now(timezone.utc).isoformat()[0:19]
    print("TriggerManip started at " + TIMESTAMP + " with flag " + FLAG)
    log("TriggerManip started at " + TIMESTAMP + " with flag " + FLAG)
    
    # -r to Rerun trigger files not in db
    if(FLAG == "-r"):
        print("Deleting triggerfiles stored in file --> " + LOG_FILE)
        log("Deleting triggerfiles stored in file --> " + LOG_FILE)
        delete_triggers(LOG_FILE)
        print("Creating new triggerfiles from --> " + LOG_FILE)
        log("Creating new triggerfiles from --> " + LOG_FILE)
        create_triggers(LOG_FILE)
    
    # -c to Clean up trigger files already in db
    elif(FLAG == "-c"):
        print("Deleting triggerfiles stored in file --> " + LOG_FILE)
        log("Deleting triggerfiles stored in file --> " + LOG_FILE)
        delete_triggers(LOG_FILE)
    
    # -h for Flag options
    elif(FLAG == "-h"):
        print("-r \t Rerun Trigger Files")
        print("-c \t Clean up Trigger Files")
        print("-d \t Delete Log File (add after filename)")
        print("-h \t Flag Help")
    
    # Handles Flag Usage Error
    else:
        log("Flag Usage Error: " + FLAG + " not in options")
        print("Usage: python3 psws_triggerMANIP.py -FLAG log_file.txt -d(optional)")
        print("Use -h for all possible flags")
        return
    
    # Deletes Log if prompted in command
    if(DELETE_LOG):
        delete_log(LOG_FILE)
    
    print("TriggerMANIP Complete")
    log("TriggerMANIP Complete")

if __name__ == "__main__":
    main()