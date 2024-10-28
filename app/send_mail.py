import os
from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig

# from dotenv import load_dotenv
# load_dotenv('.env')

class Envs:
    MAIL_USERNAME = "mutestimo72@gmail.com"
    MAIL_PASSWORD = "rxel mxsb fsbm qgpv"
    MAIL_FROM = "mutestimo72@gmail.com"
    MAIL_PORT = int(587)
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_FROM_NAME = "KCCA KLA CONNECT"

    # MAIL_USERNAME = "shpt@kcca.go.ug"
    # MAIL_PASSWORD = "Kcca12345"
    # MAIL_FROM = "shpt@kcca.go.ug"
    # MAIL_PORT = int(587)
    # MAIL_SERVER = "mail.kcca.go.ug"
    # MAIL_FROM_NAME = "KCCA KLA CONNECT"

    # MAIL_USERNAME = config('MAIL_USERNAME')
    # MAIL_PASSWORD = config('MAIL_PASSWORD')
    # MAIL_FROM = config('MAIL_FROM')
    # MAIL_PORT = int(config('MAIL_PORT'))
    # MAIL_SERVER = config('MAIL_SERVER')
    # MAIL_FROM_NAME = config('MAIN_FROM_NAME')


conf = ConnectionConfig(
    MAIL_USERNAME=Envs.MAIL_USERNAME,
    MAIL_PASSWORD=Envs.MAIL_PASSWORD,
    MAIL_FROM_NAME=Envs.MAIL_FROM_NAME,
    MAIL_FROM=Envs.MAIL_FROM,
    MAIL_PORT=Envs.MAIL_PORT,
    MAIL_SERVER=Envs.MAIL_SERVER,
    MAIL_SSL_TLS=False,
    MAIL_STARTTLS=True,
    USE_CREDENTIALS=True,
)

async def send_email_async(subject: str, email_to: str, body: str):
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=body,
        subtype='html',
    )
    
    fm = FastMail(conf)
    await fm.send_message(message, template_name='email.html')

async def send_email_async_test():
    message = MessageSchema(
        subject="Hello World",
        recipients=['mutestimo72@gmail.com'],
        body="THis is a test",
        subtype='html',
    )
    
    fm = FastMail(conf)
    await fm.send_message(message, template_name='email.html')

def send_email_background(background_tasks: BackgroundTasks, subject: str, body: str, email_to: str):
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=body,
        subtype='html',
    )
    fm = FastMail(conf)
    background_tasks.add_task(
       fm.send_message, message, template_name='email.html')