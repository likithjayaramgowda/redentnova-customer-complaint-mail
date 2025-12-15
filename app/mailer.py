import os
import smtplib
from email.message import EmailMessage
from typing import List


def send_mail(
    to: List[str],
    subject: str,
    body: str,
    attachment_bytes: bytes,
    attachment_name: str,
):
    if not to:
        raise ValueError("No recipients provided for email.")

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_password = os.environ.get("SMTP_PASSWORD")
    mail_from = os.environ.get("MAIL_FROM", smtp_user)

    if not smtp_user or not smtp_password:
        raise RuntimeError("SMTP_USER or SMTP_PASSWORD not set.")

    msg = EmailMessage()
    msg["From"] = mail_from
    msg["To"] = ", ".join(to)
    msg["Subject"] = subject
    msg.set_content(body)

    msg.add_attachment(
        attachment_bytes,
        maintype="application",
        subtype="pdf",
        filename=attachment_name,
    )

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
