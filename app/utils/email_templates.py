import os
from jinja2 import Environment, FileSystemLoader, select_autoescape
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from decouple import config

# Environment variables are loaded via decouple.config() which reads from .env or environment

# Setup Jinja2
template_env = Environment(
    loader=FileSystemLoader("app/templates"),
    autoescape=select_autoescape(["html", "xml"])
)

# def render_email_template(template_name: str, context: dict) -> str:
#     template = template_env.get_template(template_name)
#     return template.render(context)

def render_email_template(template_name: str, context: dict) -> str:
    try:
        template = template_env.get_template(template_name)
        return template.render(context)
    except Exception as e:
        print("Template render error:", e)
        return ""

def send_html_email(to_email: str, subject: str, html_content: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = os.getenv("EMAIL_SENDER")
    msg["To"] = to_email

    msg.attach(MIMEText(html_content, "html"))

    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT"))) as server:
        server.starttls()
        server.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS"))
        server.sendmail(msg["From"], msg["To"], msg.as_string())

def send_welcome_email(to_email: str, user_name: str, otp: str):
    html = render_email_template("welcome_email.html", {
        "user_name": user_name,
        "otp": otp
    })
    
    send_html_email(to_email, "Welcome! Activate Your Account.", html)

def send_password_reset_email(to_email: str, user_name: str, otp: str):
    html = render_email_template("password_reset.html", {
        "user_name": user_name,
        "otp": otp,
        "to_email": to_email
    })
    
    send_html_email(to_email, "Password Reset Instruction.", html)