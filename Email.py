
##################################################
## This is to send emails
## 
##################################################
## GNU Lesser General Public License v3.0
##################################################
## Author: Patrick Hinson
## Copyright: Copyright 2019, email
## Credits: [Patrick Hinson]
## License: GNU Lesser General Public License v3.0
## Version: 1.0.0
## Mmaintainer: Patrick Hinson
## Email: 
## Status: Stable
## Language: python
##################################################

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

def email(mssubject, msfrom, msto, mstext, mshtml, mailserver):
    try:
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = mssubject
        msg['From'] = msfrom
        msg['To'] = msto

        part1 = MIMEText(mstext, 'plain')
        part2 = MIMEText(mshtml, 'html')

        msg.attach(part1)
        msg.attach(part2)

    except:
        exerror = "email() -- Add message parts: ", sys.exc_info()[0]
        print(exerror)

    try:

        s = smtplib.SMTP(mailserver)
        s.sendmail(msfrom, msto, msg.as_string())
        s.quit()

    except:
        exerror = "EMAIL email() -- Send email Unexpected error: ", sys.exc_info()[0]
        print(exerror)