import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import email.utils
from os.path import basename
import time
import sys

sender = ""
smtp_username = ""
smtp_host = "smtp.google.com"
password = "" 
smtp_port = 587
specialIdentifier = "Bilal's VIM equiped future-machine"

applications_short_break = 30
long_break_seconds = 8
short_break_seconds = 0.3
max_applications = 490

def generate_and_send_email(subject, body, sender, recipients, resumePath, password):
    msg = MIMEMultipart()
    msg["Importance"] = "High"
    msg["Subject"] = subject
    msg["From"] = f'"{sender}" <{sender}>'
    msg["To"] = ", ".join(recipients)
    msg["Date"] = email.utils.formatdate(localtime=True)
    msg["Message-ID"] = email.utils.make_msgid()
    msg["Return-Path"] = sender
    msg["Reply-To"] = sender

    msg["X-Priority"] = "1"
    msg["X-Mailer"] = specialIdentifier 
    msg["Content-Type"] = 'text/plain; charset="utf-8"'

    with open(resumePath, "rb") as f:
        attached_file = MIMEApplication(f.read(), _subtype="pdf")
        attached_file.add_header(
            "Content-Disposition", "attachment", filename=basename(resumePath)
        )
        msg.attach(attached_file)

    msg.attach(MIMEText(body, "plain"))

    context = ssl.create_default_context()

    with smtplib.SMTP(smtp_host, smtp_port) as smtp_server:
        smtp_server.ehlo()
        smtp_server.starttls(context=context)
        smtp_server.ehlo()
        smtp_server.login(smtp_username, password)
        smtp_server.sendmail(sender, recipients, msg.as_string())

if __name__ == "__main__":
    try:
        if len(sys.argv) != 4:
            print("need arguments, target_emails_list email-template resume_location")
        else:
            with open(sys.argv[1], "r") as targets, open(sys.argv[2], "r") as template:
                subject = body = ""
                current_count = 0
                for line in template:
                    if current_count == 0: subject = line
                    else: body += line
                    current_count = current_count + 1
                template.close()
                current_count = 0
                for target in targets:
                    cur_email = target.strip()
                    recipients = [cur_email]
                    print(f"{current_count}___sending to [{cur_email}]..", end="")
                    try:
                        generate_and_send_email(subject, body, sender, recipients, sys.argv[3], password)
                    except Exception as e:
                        print(f"  ===> email failed: {e}")
                        continue
                    print(f"  ===> application sent", end="")
                    current_count = current_count + 1
                    if current_count >= max_applications:
                        print(f"\n----> reached the limit: {max_applications} applications")
                        targets.close()
                        sys.exit(0)
                    if (current_count % applications_short_break) == 0 and current_count != 0:
                        print(f"\n----> taking a break for {long_break_seconds} secs")
                        time.sleep(long_break_seconds)
                    else:
                        print(f", breaking for {short_break_seconds} secs")
                        time.sleep(short_break_seconds)
                targets.close()
    except FileNotFoundError:
        print("cant open file")
    except Exception as e:
        print(f"An error occurred: {e}")

