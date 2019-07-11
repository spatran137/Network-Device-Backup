#!C:\Program Files\Python\Python36\python.exe

##################################################
## This is to backup network switches
## 
##################################################
## GNU Lesser General Public License v3.0
##################################################
## Author: Patrick Hinson
## Copyright: Copyright 2019, Network Device Backup
## Credits: [Patrick Hinson]
## License: GNU Lesser General Public License v3.0
## Version: 1.0.0
## Mmaintainer: Patrick Hinson
## Email: 
## Status: Stable
## Language: python
##################################################

import paramiko
import time
import os
import sys
import configparser
import csv
import subprocess
import smtplib
import shutil
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import sqlite3
import Email

def config():
    global logfile
    global primarycbackup
    global secondarycbackup
    global ftpbackup
    global elog
    global email_log
    global config_path

    emailtimestr = time.strftime("%Y.%m.%d.%H")
    report = 'email--' + emailtimestr + '.csv'

    #gets the current date and sets it.
    year = time.strftime("%Y")
    month = time.strftime("%m")
    day = time.strftime("%d")

    try:
        #finds the current working dir.
        cwd = os.getcwd()

        #adds the current working dir to the config.ini
        config_path = os.path.join(cwd, "config.ini")

        #reads the config.ini file.
        config = configparser.ConfigParser()
        config.read(config_path)

        #from the config.ini gets the LogFile and Backup Paths.
        logfile = config['LogFile']['Log']
        primarybackupPath = config['BackUp']['primarybackupPath']
        secondarybackupPath = config['BackUp']['secondarybackupPath']
        ftpbackup = config['BackUp']['ftpbackupPath']
        elog = config['Email']['elog']
    except:
        exerror = "config() -- Reed config.ini Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)

    #adds the year month and day to the backup path
    primarycbackup = primarybackupPath + year + '/' + month + '/' + day + '/'
    secondarycbackup = secondarybackupPath + year + '/' + month + '/' + day + '/'
    ftpbackup = ftpbackup + year + '/' + month + '/' + day + '/'

    #creates the folder path if it does not exist
    mkdrfl(primarycbackup)
    mkdrfl(secondarycbackup)
    mkdrfl(ftpbackup)
    email_log = elog + report
    mkdrfl(email_log)

#makes sure that both the dir and file exists and if not this will create them
def mkdrfl(file):
    try:
        directory = os.path.dirname(file)

        if not os.path.exists(directory):
            os.makedirs(directory)

        if not os.path.exists(file):
                open(file, 'w').close()
    except:
        exerror = "mkdrfl() Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)

#writes to the log file
def wlog(note):
    global good
    
    if good == 0:
        mkdrfl(logfile)
        good = 1

    logtimestr = time.strftime("%Y.%m.%d--%H:%M:%S:")
    log = logtimestr + ' ' + str(note)
    try:
        with open(logfile, 'a') as out:
            out.write(log + '\n')
    except:
        exerror = "wlog() -- write to log Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)

#writes to the current backup file
def write_backup_file(input, name, devicetype, location, ip, host):
    try:
        config = configparser.ConfigParser()
        config.read(config_path)
        primary = config['BackupSite']['primary']
        secondary = config['BackupSite']['secondary']
    except:
        exerror = "write_backup_file() -- Reed config.ini Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)
    try:
        if location == secondary:
            primaryfile = primarycbackup + devicetype + '/' + name
            secondaryfile = secondarycbackup + devicetype + '/' + name
            mkdrfl(primaryfile)
            mkdrfl(secondaryfile)

            backup = list()

            for line in input:
                backup.append(line + '\n')

            out = open(primaryfile, "w")
            out.writelines(backup)
            out.close()

            shutil.copy2(primaryfile, secondaryfile)
        elif location == primary:
            primaryfile = primarycbackup + devicetype + "/" + name
            mkdrfl(primaryfile)

            backup = list()

            for line in input:
                backup.append(line + '\n')

            out = open(primaryfile, "w")
            out.writelines(backup)
            out.close()
        email_file(ip, host, location, 'True', 'good', primaryfile)  
    except:
        exerror = "write_backup_file() -- Write backup file Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)
        email_file(ip, host, location, 'True', 'failed', sys.exc_info()[0])

#write a log file that is used to email the errors 
def email_file(ip, host, location, ping, status, error):

    errortime = time.strftime("%Y/%m/%d--%H:%M:%S")

    line = errortime + ',' + ip + ',' + host + ',' + location + ',' + str(ping) + ',' + status + ',' + error
    try:
        with open(email_log, "a") as file:
            file.write(line + '\n')
    except:
        exerror = "email_file() -- Write Faild backup file Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)

#generates and sends the email 
def sendemail():
    #reads the config.ini file.
    try:
        config = configparser.ConfigParser()
        config.read(config_path)

        msfrom = config['Email']['from']
        
        if mode == 'day':
            msto = config['Email']['to']
        elif mode == 'week':
            msto = config['Email']['weekto']

        mssubject = config['Email']['subject']
        mailserver = config['Email']['mailserver']

    except:
        exerror = "email() -- Read config.ini Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)
    try:
        report = list()
        reporttext = str()
        reporthtml = str()
        rcolor = 0
        gcolor = 0
        with open(email_log, newline='') as f:
            reader = csv.reader(f, delimiter=',', quoting=csv.QUOTE_NONE)
            for row in reader:
                errortime = row[0]
                ip = row[1]
                host = row[2]
                location = row[3]
                ping = row[4]
                status = row[5]
                error = row[6]
            
                ltext = '\n' + errortime + ip + '     ' + host + '     ' + location + '     ' + ping + '     ' + status + '     ' + error

                reporttext += ltext
                if status == 'good':
                    error = '<a href="' + error + '">' + host + '</a>'
                    if gcolor == 0:
                        reporthtml += '<tr bgcolor="74d676">'
                        gcolor = 1
                        start = 1
                    elif gcolor == 1:
                        reporthtml += '<tr bgcolor="00b403">'
                        gcolor =0
                        start = 1
                elif status == 'failed':
                    if rcolor == 0:
                        reporthtml += '<tr bgcolor="FFAAAA">'
                        rcolor = 1
                        start = 1
                    elif rcolor == 1:
                        reporthtml += '<tr bgcolor="FF4242">'
                        rcolor =0
                        start = 1
                reporthtml += '<th>' + errortime + '</th>'
                reporthtml += '<th>' + ip + '</th>'
                reporthtml += '<th>' + host + '</th>'
                reporthtml += '<th>' + location + '</th>'
                reporthtml += '<th>' + ping + '</th>'
                reporthtml += '<th>' + status + '</th>'
                reporthtml += '<th>' + error + '</th>'
                reporthtml += '</tr>\n'
                start = 0
            f.close

            text = """IP     Hostname     location     Ping     Status     Error\n""" + str(reporttext)

            html = """
            <html>
                <head>
                <style>
                    table, th, td {
                        border: 1px solid black;
                        border-collapse: collapse;
                        table-layout: auto;
    
                    }
                    th, td {
                        padding: 5px;
                    }
                    th {
                        text-align: left;
                    }
                </style>
                </head>
                <body>
                    <p>Report for python backed up devices only failed jobs.<br><br>
                    <table width="1200">
                        <tr  bgcolor="00904b">
                            <th><font color="white">Time</th>
                            <th><font color="white">IP</th>
                            <th><font color="white">Hostname</th>
                            <th><font color="white">location</th>
                            <th><font color="white">Ping</th>
                            <th><font color="white">Status</th>
                            <th><font color="white">Error/File Location Link</th>
                        </tr>\n""" + str(reporthtml) + """
                    </p>
                </body>
            </html>
            """
        Email.email(mssubject,msfrom,msto,text,html,mailserver)

    except:
        exerror = "email() -- Generate email Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)

#this is what does the scraping from the ssh connection.
def ssh_backup(ip, host, username, password, command, sleep, name, devicetype, enablepass, enablecommand, paging, location, ping, run, input):
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=ip,username=username,password=password)

        remote_connection = ssh_client.invoke_shell()
        remote_connection_data = str()
        recv = bytes()
        go = 1

        ssh_connected = 'Successfully connected'

        wlog(ssh_connected)

        while go > 0:
            if remote_connection.recv_ready():
                recv = remote_connection.recv(99999)
                remote_connection_data += recv.decode('utf-8')

            else:
                continue

            if devicetype == 'edgeswitch':
                remote_connection.send(enablecommand)
                time.sleep(1)
                remote_connection.send(enablepass)
                time.sleep(1)
                remote_connection.send(paging)
                time.sleep(1)
            elif devicetype == 'rfs':
                remote_connection.send(paging)
            elif devicetype == 'ios':
                remote_connection.send(enablecommand)
                time.sleep(1)
                remote_connection.send(enablepass)
                time.sleep(1)
                remote_connection.send(paging)
                time.sleep(1)

            # Clearing output.
            if remote_connection.recv_ready():
                output = remote_connection.recv(80000)

            remote_connection.send(command)
            time.sleep(sleep)
        
            command1 = command[:-1]
            ssh_command = 'Running command ' + command1
            wlog(ssh_command)

            if remote_connection.recv_ready():
                output = remote_connection.recv(80000)
            print(sys.getsizeof(output)) 
            stroutput = str(output)
            aroutput = stroutput.split('\\r\\n')

            if run == 0:
                return aroutput
            elif run == 1:
                cmdoutput = input + aroutput
                valid = validate(cmdoutput, devicetype)

                if valid == 'good':
                    write_backup_file(cmdoutput, name, devicetype, location, ip, host)
                    time.sleep(2)
                    wlog('Competed Write To File')
                    status = 'good'
                    error = 'none'
                else:
                    wlog('Backup failed: ' + valid)
                    name = 'failed--' + name
                    write_backup_file(cmdoutput, name, devicetype, location, ip, host)
                    status = 'failed'
                    error = valid
                    email_file(ip, host, location, ping, status, error)
            go = 0 
        wlog('Task Complete')
        
    except:
        exerror = "ssh_backup() Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)
        email_file(ip, host, location, ping, 'failed', exerror)
        ssh_client.close()
    finally:
        ssh_client.close()


def ssh_ftp(ip, host, username, password, command, sleep, name, devicetype, enablepass, enablecommand, location, ping):
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=ip,username=username,password=password)

        remote_connection = ssh_client.invoke_shell()
        remote_connection_data = str()
        recv = bytes()
        go = 1

        ssh_connected = 'Successfully connected'

        wlog(ssh_connected)

        while go > 0:
            if remote_connection.recv_ready():
                recv = remote_connection.recv(99999)
                remote_connection_data += recv.decode('utf-8')
            else:
                continue
            #this just checks to make sure that the login attempt was not stuck at the password which could mean that the password is wrong.
            if remote_connection_data.endswith('Password:'):
                remote_connection.send("end\n")
                WLog('Something happend need to check the username and password of the script for: ' + host + ' ' + ip)
                #breaks the loop to end the program since the password is likely wrong
                go = 0
                status = 'failed'
                error = 'bad username or password'
                email_file(ip, host, location, ping, status, error)


            remote_connection.send(command)
            remote_connection.send("\n")
            time.sleep(sleep)

            command1 = command[:-1]
            ssh_command = 'Running command ' + command1
            wlog(ssh_command)

            go = 0
            wlog('Task Complete')
            email_file(ip, host, location, 'True', 'good', ftpbackup)
    except:
        exerror = "ssh_ftp() Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)
        email_file(ip, host, location, ping, 'failed', exerror)
        ssh_client.close()
    finally:
        ssh_client.close()

def validate(input, devicetype):
    valid = 'good'
    try:
        if devicetype == 'rfs':
            for item in input:
                if item.startswith('% Ambiguous command:'):
                    valid = item
                elif  item.startswith('Access denied'):
                    valid = item
                    
        elif devicetype == 'edgeswitch':
            for item in input:
                if item.startswith('Authentication Denied.'):
                    valid = item
                elif item.startswith('% Invalid input detected '):
                    valid = item

        elif devicetype == 'airos':
            for item in input:
                if item.startswith('% Ambiguous command:'):
                    valid = item
        return valid
    except:
        exerror = "validate() Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)

def bfilename(devicename, ip, devicetype):
    bftime = time.strftime("%Y.%m.%d__%H_%M_%S")
    year = time.strftime("%Y")
    month = time.strftime("%m")
    day = time.strftime("%d")

    if devicetype == 'sonicwall':
        name = year + '/' + month + '/' + day + '/' + bftime + '_' + devicename + '_' + ip
    else:
        name = bftime + '_' + devicename + '_' + ip + '.txt'
    return name

def ping(host):
    with open(os.devnull, 'w') as DEVNULL:
        try:
            subprocess.check_call(
                ['ping', '-n', '2', '-w', '700', host],
                stdout=DEVNULL,  # suppress output
                stderr=DEVNULL
            )
            is_up = True
            up = 'Ping: Up ' + host
            wlog(up)
            return is_up
        except subprocess.CalledProcessError:
            is_up = False
            return is_up

def login_test(ip,host,location,ping,username,password):
    try:
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh_client.connect(hostname=ip,username=username,password=password)

        remote_connection = ssh_client.invoke_shell()
        remote_connection_data = str()
        recv = bytes()
        go = 1

        ssh_connected = 'Successfully connected'

        wlog(ssh_connected)
        
        status = True
        
        return status

    except:
        exerror = "login_test() Unexpected error:", sys.exc_info()[0]
        #print(exerror)
        wlog(exerror)
        #email_file(ip, host, location, ping, 'failed', 'Failed to login bad username or password')
        ssh_client.close()
        status = False
        return status
    finally:
        ssh_client.close()

def commands(devicetype, enablepass):
    try:
        #reads the config.ini file.
        config = configparser.ConfigParser()
        config.read(config_path)

        remotecommand1 = config[devicetype]['remotecommand1']
        sleeptime1 = int(config[devicetype]['sleeptime1'])
        remotecommand12 = config[devicetype]['remotecommand12']
        sleeptime2 = int(config[devicetype]['sleeptime2'])
        paging = config[devicetype]['paging']
        enablecommand = config[devicetype]['enablecommand']
        if devicetype == 'sonicwall':
            strsonicwall = ''
        else:
            remotecommand1 = remotecommand1 + '\n'
            remotecommand12 = remotecommand12 + '\n'
            paging = paging + '\n'
            enablecommand = enablecommand + '\n'

        if devicetype == 'edgeswitch':
            enablepass = enablepass + '\n'

        return remotecommand1, sleeptime1, remotecommand12, sleeptime2, paging, enablecommand, enablepass
    except:
        exerror = "commands() Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)

def start():

    cwd = os.getcwd()
    #adds the current working dir to the device csv
    csvpath = os.path.join(cwd, "device.csv")
    
    try:
        with open(csvpath, newline='') as f:
            reader = csv.reader(f, delimiter=',', quoting=csv.QUOTE_NONE)
            for row in reader:

                ip = row[0]
                host = row[1]
                devicetype = row[2]
                location = row[3]
                username = row[4]
                password = row[5]
                enablepass = row[6]

                start = 'Loading: ' + host + ' ' + ip
        
                wlog(start)
                rping = ping(ip)

                if rping == True:
                    rlt = login_test(ip,host,location,rping,username,password)
                    
                    if rlt == True:
                        wlog('Backup Job for ' + host + '  --  ' + ip + ' is starting')
                        print(ip + ' ' + host + ' is up')
                        remotecommand1, sleeptime1, remotecommand12, sleeptime2, paging, enablecommand, enablepass = commands(devicetype, enablepass)
                        name = bfilename(host, ip, devicetype)
                        name = str(name)

                        if devicetype == 'sonicwall':
                            remotecommand1 = remotecommand1 + name + '.exp' #need to add year mounth day to the variable string from the FTP path
                            remotecommand12 = remotecommand12 + name + '.txt'
                            ssh_ftp(ip,host,username,password, remotecommand1, sleeptime1, name, devicetype, enablepass, enablecommand, location, rping)
                            ssh_ftp(ip,host,username,password, remotecommand12, sleeptime2, name, devicetype, enablepass, enablecommand, location, rping)  
                        else:
                            cmdoutput = ''

                            cmdoutput = ssh_backup(ip,host,username,password, remotecommand1, sleeptime1, name, devicetype, enablepass, enablecommand, paging, location, rping, 0, cmdoutput)
                            ssh_backup(ip,host,username,password, remotecommand12, sleeptime2, name, devicetype, enablepass, enablecommand, paging, location, rping, 1, cmdoutput)    
        
                        wlog('Backup Job for ' + host + '  --  ' + ip + ' is complete.\n')
                    elif rlt == False:
                        print(ip + ' ' + host + ' Bad Username or Passowrd')
                        wlog(ip + ' ' + host + ' Bad Username or Passowrd\n')
                        email_file(ip, host, location, rping, 'failed', 'Bad Username or Passowrd')
                else:
                    print(ip + ' ' + host + ' is down')
                    wlog(ip + ' ' + host + ' is down\n')
                    email_file(ip, host, location, rping, 'failed', 'device was not reachable')
                    
    except:
        exerror = "Start() Unexpected error:", sys.exc_info()[1]
        print(exerror)
        wlog(exerror)
    
    sendemail()

            
def main(ran):
    global mode
    mode = ran
    try:
        stime = time.strftime("%Y/%m/%d %H:%M:%S")
        print(stime + ' Starting Backup Jobs')
        global good
        good = 0
        config()
        start()
        etime = time.strftime("%Y/%m/%d %H:%M:%S")
        print(etime + ' End of Backup Jobs')
    except:
        exerror = "PNB-Main() Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)

def mainday():
    try:
        main('day')
    except:
        exerror = "mainday() Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)
    
def mainweek():
    try:
        main('week')
    except:
        exerror = "mainweek() Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)

if __name__ == '__main__':
    try:
        main('day')
    except (KeyboardInterrupt, SystemExit):
        raise
    except:
        exerror = "__main__ Unexpected error:", sys.exc_info()[0]
        print(exerror)
        wlog(exerror)
