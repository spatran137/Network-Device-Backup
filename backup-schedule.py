#!C:\Program Files\Python36\python.exe

##################################################
## This is to schedule run python programs
## to bypass OS schedulers.
##################################################
## GNU Lesser General Public License v3.0
##################################################
## Author: Patrick Hinson
## Copyright: Copyright 2018, schedule
## Credits: [Patrick Hinson]
## License: GNU Lesser General Public License v3.0
## Version: 1.0.0
## Mmaintainer: Patrick Hinson
## Email: 
## Status: Stable
## Language: python
##################################################

import time
import os
import sys
import schedule
import Python_Network_Backup as backup

def main():
    schedule.every().day.at("17:00").do(backup.mainday)
    schedule.every().day.at("05:00").do(backup.mainday)
    schedule.every().friday.at("16:30").do(backup.mainweek)
    print('Schedule backup is running will backup at 1700 and 0500 each day')
    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except:
        print("BS-Main() Unexpected error:", sys.exc_info()[0])

if __name__ == '__main__':
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        print('exit')

