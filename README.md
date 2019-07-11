[![Build Status](https://travis-ci.org/spatran137/Network-Device-Backup.svg?branch=master)](https://travis-ci.org/spatran137/Network-Device-Backup)

# Python-Network-Backup
Python-Network-Backup is a simple python network backup tool that is currently compatible with with Ubiquiti EdgeSwitch, Ubiquiti AirOS, Motorola RFS, and SonicWall.  The current method of backup is an ssh session that then scraps the running configuration from the shell.  However, for SonicWalls the script will run a backup to FTP.

Also at this time this is only compatible to run on Windows.  In the future I want to make it be able to run on Windows or Linux.  Also there is currently no method to pass username/password for network share access so the user account that the script is running under will have to have access without passing username/password.  This is also something that I am wanting to add.

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes. See deployment for notes on how to deploy the project on a live system.

### Limitations

There are a few limitation in this version:

1. must be ran on Windows due to how it was writen
2. currently backup store locations must be the full UNC path even if it is to the local machine
3. currently the way it was writen the store location must not require additional username/password

### Prerequisites

Here are the pacages that will need to be installed/used in this project:

```
configparser==3.5.0
paramiko==2.3.1
schedule==0.4.3
```
```
pip install -r (the path to where requirements.txt is located)
```
### Installing

Once you have the prerequisites complete you will need to modify the config.ini:

Set the location were the log file is to be stored:
```
[LogFile]
Log=\\windows_computer\share\log.txt
```

Set the backup and FTP locations UNC path.
```
[BackUp]
primarybackupPath=\\windows_computer\share\
secondarybackupPath=\\windows_computer\share\
ftpbackupPath=
```
Set the variables for the site locations to either the primary or secondary site.
```
[BackupSite]
primary=lmw
secondary=lme
```
Set email settings.
```
[Email]
elog=\\windows_computer\share\
to=email@yourdomain.com
from=Python_Backup-Tool@yourdomain.com
subject=Python Backup Tool Report
mailserver=mail.yourdomain.com
```

Now that the config.ini has been modified you need to add your devices to the device.csv:



End with an example of getting some data out of the system or using it for a little demo

## Built With

* [paramiko](http://www.dropwizard.io/1.0.2/docs/) - The web framework used
* [configparser](https://maven.apache.org/) - Dependency Management
* [schedule](https://rometools.github.io/rome/) - Used to generate RSS Feeds

## Authors

* **Patrick Hinson** - *Initial work* - [spatran137](https://github.com/spatran137)


## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details

## Acknowledgments

* Hat tip to anyone who's code was used
* Inspiration
* etc
