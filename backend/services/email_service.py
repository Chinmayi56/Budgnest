import asyncio
import logging
import smtplib
from email.message import EmailMessage

from config import settings

logger = logging.getLogger("budgetnest.email")


def _build_message(to_email: str, code: str) -> EmailMessage:
    msg = EmailMessage()
    msg['Subject'] = 'Your BudgetNest Login Verification Code'
    msg['From'] = f'{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>'
    msg['To'] = to_email
    msg.set_content(
        f'Your BudgetNest verification code is {code}. '
        f'It expires in {settings.OTP_EXPIRE_MINUTES} minutes.'
    )
    msg.add_alternative(
        f'''<html><body><h2>BudgetNest</h2><p>Your verification code is:</p>
        <h1 style="letter-spacing:6px">{code}</h1>
        <p>This code expires in {settings.OTP_EXPIRE_MINUTES} minutes. If you did not
        request it, you can safely ignore this email.</p></body></html>''',
        subtype='html',
    )
    return msg


def _send_sync(to_email: str, code: str) -> None:
    if not settings.SMTP_HOST or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        raise RuntimeError(
            'SMTP is not configured. Set SMTP_HOST, SMTP_USERNAME and SMTP_PASSWORD.'
        )

    msg = _build_message(to_email, code)

    # Port 465 is implicit-TLS (SMTP_SSL from the first byte); anything
    # else (587, 25, ...) uses plaintext-then-STARTTLS. Using the wrong
    # one for a given port is a very common cause of the send silently
    # timing out / failing, which previously surfaced to the user as a
    # generic 503 with no clue why.
    try:
        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
                server.ehlo()
                if settings.SMTP_USE_TLS:
                    server.starttls()
                    server.ehlo()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise RuntimeError(
            'SMTP authentication failed. If using Gmail, SMTP_PASSWORD must be a '
            '16-character App Password, not your normal account password.'
        ) from exc
    except (smtplib.SMTPException, OSError) as exc:
        raise RuntimeError(f'Could not send email via SMTP: {exc}') from exc


async def send_login_code_email(to_email: str, code: str) -> None:
    """
    Send the login verification code to `to_email`.

    If SMTP has not been configured (no SMTP_HOST/USERNAME/PASSWORD in the
    environment) this falls back to printing the code to the backend
    console/log instead of raising, as long as
    EMAIL_DEV_CONSOLE_FALLBACK is enabled (the default). This is what
    lets the "Email Code" sign-in flow work immediately in local
    development (e.g. running the project in VS Code) without needing
    real mail credentials on hand. Once real SMTP settings are added to
    backend/.env, this fallback is automatically disabled and real
    emails are sent instead.
    """
    if not settings.SMTP_CONFIGURED:
        if settings.EMAIL_DEV_CONSOLE_FALLBACK:
            banner = "=" * 60
            logger.warning(
                "\n%s\nSMTP is not configured — printing verification code "
                "instead of emailing it (dev fallback).\n"
                "Recipient: %s\nVerification code: %s\n"
                "Set SMTP_HOST / SMTP_USERNAME / SMTP_PASSWORD in backend/.env "
                "to send real emails.\n%s",
                banner, to_email, code, banner,
            )
            return
        raise RuntimeError(
            'SMTP is not configured. Set SMTP_HOST, SMTP_USERNAME and SMTP_PASSWORD.'
        )

    await asyncio.to_thread(_send_sync, to_email, code)
