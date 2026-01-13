import os
from datetime import datetime as dt
from datetime import timezone
import sys
import time

def writeLog(theMessage):
    timestamp = dt.now(timezone.utc).isoformat()[0:19]
    f = open("/var/www/html/graphing.log", "a")
    f.write(timestamp + " " + theMessage + "\n")
    f.close()


if __name__ == "__main__":
    print("Graphing") 
    writeLog("STARTING Graphing for " + sys.argv[1])
    time.sleep(120)
    writeLog("COMPLETED Graphing for " + sys.argv[1])
    
