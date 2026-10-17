"""Send transactional email (password resets) through whichever provider is configured.

Resend (RESEND_API_KEY) or any SMTP server (SMTP_HOST, e.g. Brevo, Gmail, Mailgun). With neither set the
feature is simply off: nothing is sent and the UI does not offer "forgot password".
"""
import asyncio
import logging
import smtplib
from email.message import EmailMessage

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailError(Exception):
    pass


async def send_email(to: str, subject: str, text: str) -> None:
    if settings.RESEND_API_KEY:
        await _send_resend(to, subject, text)
    elif settings.SMTP_HOST:
        await asyncio.to_thread(_send_smtp, to, subject, text)
    else:
        raise EmailError("No email provider is configured")


async def _send_resend(to: str, subject: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
            json={"from": settings.MAIL_FROM, "to": [to], "subject": subject, "text": text},
        )
    if response.status_code >= 300:
        raise EmailError(f"Resend answered {response.status_code}: {response.text[:200]}")


def _send_smtp(to: str, subject: str, text: str) -> None:
    message = EmailMessage()
    message["From"] = settings.MAIL_FROM
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    try:
        if settings.SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15)
        with server:
            if settings.SMTP_PORT != 465 and settings.SMTP_STARTTLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailError(f"SMTP failed: {exc}") from exc
