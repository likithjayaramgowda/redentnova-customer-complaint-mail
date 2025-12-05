from __future__ import annotations
import os
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import List


@dataclass(frozen=True)
class SmtpConfig:
    host: str
    port: int
    user: str
    password: str
    mail_from: str


def load_smtp_config() -> SmtpConfig:
    return SmtpConfig(
        host=os.environ["SMTP_HOST"],
        port=int(os.environ.get("SMTP_PORT", "587")),
        user=os.environ["SMTP_USER"],
        password=os.environ["SMTP_PASS"],
        mail_from=os.environ["MAIL_FROM"],
    )


def send_pdf(
    smtp: SmtpConfig,
    to_addrs: List[str],
    subject: str,
    body: str,
    filename: str,
    pdf_bytes: bytes,
) -> None:
    msg = EmailMessage()
    msg["From"] = smtp.mail_from
    msg["To"] = ", ".join(to_addrs)
    msg["Subject"] = subject
    msg.set_content(body)

    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=filename)

    with smtplib.SMTP(smtp.host, smtp.port, timeout=30) as server:
        server.starttls()
        server.login(smtp.user, smtp.password)
        server.send_message(msg)
