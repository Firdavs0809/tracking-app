"""SMTP email tasks (runs in Celery worker — sync smtplib)."""

import os
import smtplib
from email.message import EmailMessage
from typing import Sequence

from celery_app import app


@app.task(name="tasks.send_email_smtp", bind=True, max_retries=3)
def send_email_smtp(
    self,
    subject: str,
    body_plain: str,
    to_addresses: Sequence[str],
    from_address: str | None = None,
) -> str:
    """
    Send mail via SMTP (STARTTLS on 587 or plain on 1025 for Mailpit dev).
    Env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
    """
    host = os.environ.get("SMTP_HOST", "localhost")
    port = int(os.environ.get("SMTP_PORT", "1025"))
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    from_addr = from_address or os.environ.get("SMTP_FROM", "noreply@localhost")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addresses)
    msg.set_content(body_plain)

    try:
        with smtplib.SMTP(host, port, timeout=30) as smtp:
            if os.environ.get("SMTP_USE_TLS", "").lower() in ("1", "true", "yes"):
                smtp.starttls()
            if user:
                smtp.login(user, password or "")
            smtp.send_message(msg)
    except OSError as exc:
        raise self.retry(exc=exc, countdown=60) from exc

    return f"sent:{subject}"
