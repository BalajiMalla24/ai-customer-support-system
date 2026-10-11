import asyncio
import os
import smtplib
from email.message import EmailMessage


def _is_enabled() -> bool:
    return os.getenv("EMAIL_SMTP_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}


def _send_sync(to_email: str, subject: str, body: str):
    host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASS", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", user or os.getenv("SUPPORT_EMAIL_FROM", "support@shopeasy.local"))

    if not user or not password:
        raise RuntimeError("SMTP credentials are missing. Set SMTP_USER and SMTP_PASS.")

    msg = EmailMessage()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(host, port, timeout=12) as server:
        server.ehlo()
        if os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}:
            server.starttls()
            server.ehlo()
        server.login(user, password)
        server.send_message(msg)


async def send_smtp_email(to_email: str, subject: str, body: str) -> tuple[bool, str | None]:
    if not _is_enabled():
        return False, "SMTP disabled"

    try:
        await asyncio.to_thread(_send_sync, to_email, subject, body)
        return True, None
    except Exception as e:
        return False, str(e)
