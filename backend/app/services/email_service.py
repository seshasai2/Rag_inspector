"""
Email service for RAGInspector v2.0.
Supports:
1. Resend API (free: 3000 emails/month, no SMTP) — primary
2. SMTP (Gmail/any SMTP) — fallback
3. Console/logging — development fallback

Env vars:
- RESEND_API_KEY: Resend API key (get at https://resend.com)
- SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD: SMTP fallback
"""

from typing import Optional

import structlog

from app.core.config import settings

logger = structlog.get_logger()


async def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """
    Send email using best available provider:
    1. Resend (free, API-based)
    2. SMTP fallback
    3. Console log (dev)

    Returns True if sent successfully.
    """
    # Strategy 1: Resend (free, API-based — no SMTP needed)
    if settings.RESEND_API_KEY:
        return await _send_via_resend(to_email, subject, html_body, text_body)

    # Strategy 2: SMTP fallback
    if settings.SMTP_HOST:
        return await _send_via_smtp(to_email, subject, html_body, text_body)

    # Strategy 3: Console log (development)
    logger.info(
        "Email would be sent (no email provider configured)",
        to=to_email,
        subject=subject,
        html_preview=html_body[:200] if html_body else None,
    )
    return True


async def _send_via_resend(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """Send via Resend API (free tier: 3000 emails/month)."""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=15.0) as client:
            payload = {
                "from": f"RAGInspector <{settings.SMTP_FROM or 'noreply@raginspector.com'}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            if text_body:
                payload["text"] = text_body

            resp = await client.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
            )
            if resp.status_code in (200, 201):
                logger.info("Email sent via Resend", to=to_email, subject=subject)
                return True
            else:
                logger.warning(
                    "Resend API error",
                    status=resp.status_code,
                    body=resp.text[:300],
                    to=to_email,
                )
                return False
    except Exception as e:
        logger.warning("Resend send failed, falling back to SMTP", error=str(e))
        if settings.SMTP_HOST:
            return await _send_via_smtp(to_email, subject, html_body, text_body)
        return False


async def _send_via_smtp(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """Send via SMTP using aiosmtplib (non-blocking for the FastAPI event loop)."""
    try:
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        import aiosmtplib

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM or "noreply@raginspector.com"
        msg["To"] = to_email

        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        if html_body:
            msg.attach(MIMEText(html_body, "html"))

        use_tls = settings.SMTP_PORT == 465
        start_tls = settings.SMTP_PORT == 587
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER or None,
            password=settings.SMTP_PASSWORD or None,
            use_tls=use_tls,
            start_tls=start_tls,
            timeout=15,
        )

        logger.info("Email sent via SMTP", to=to_email, subject=subject)
        return True
    except Exception as e:
        logger.error("SMTP send failed", error=str(e), to=to_email)
        return False


def send_email_sync(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
) -> bool:
    """Synchronous send for Celery workers (httpx sync + stdlib SMTP)."""
    if settings.RESEND_API_KEY:
        try:
            import httpx

            payload = {
                "from": f"RAGInspector <{settings.SMTP_FROM or 'noreply@raginspector.com'}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            if text_body:
                payload["text"] = text_body
            resp = httpx.post(
                "https://api.resend.com/emails",
                json=payload,
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=15.0,
            )
            if resp.status_code in (200, 201):
                logger.info("Email sent via Resend (sync)", to=to_email, subject=subject)
                return True
            logger.warning(
                "Resend API error (sync)",
                status=resp.status_code,
                body=resp.text[:300],
                to=to_email,
            )
        except Exception as e:
            logger.warning("Resend sync send failed", error=str(e), to=to_email)

    if settings.SMTP_HOST:
        try:
            import smtplib
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText

            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.SMTP_FROM or "noreply@raginspector.com"
            msg["To"] = to_email
            if text_body:
                msg.attach(MIMEText(text_body, "plain"))
            if html_body:
                msg.attach(MIMEText(html_body, "html"))
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
                if settings.SMTP_PORT == 587:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(msg["From"], [to_email], msg.as_string())
            logger.info("Email sent via SMTP (sync)", to=to_email, subject=subject)
            return True
        except Exception as e:
            logger.error("SMTP sync send failed", error=str(e), to=to_email)
            return False

    logger.info(
        "Email would be sent (no email provider configured)",
        to=to_email,
        subject=subject,
        html_preview=html_body[:200] if html_body else None,
    )
    return True


# ---- Email Templates ----


def render_verification_email(name: str, verification_url: str) -> str:
    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 32px 24px;">
        <div style="text-align: center; margin-bottom: 32px;">
            <div style="width: 48px; height: 48px; border-radius: 12px; background: #3b82f6; display: inline-flex; align-items: center; justify-content: center; color: white; font-size: 20px; font-weight: bold;">R</div>
            <h1 style="font-size: 24px; margin-top: 16px; color: #1a1a2e;">Verify your email</h1>
        </div>
        <p style="font-size: 16px; color: #4a4a6a; line-height: 1.6;">Hi <strong>{name}</strong>,</p>
        <p style="font-size: 16px; color: #4a4a6a; line-height: 1.6;">Thanks for signing up for RAGInspector! Please verify your email address by clicking the button below.</p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{verification_url}" style="display: inline-block; background: #3b82f6; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">Verify Email Address</a>
        </div>
        <p style="font-size: 14px; color: #8a8aa0; line-height: 1.6;">Or copy and paste this link in your browser:</p>
        <p style="font-size: 13px; color: #3b82f6; word-break: break-all; background: #f5f5ff; padding: 12px; border-radius: 8px;">{verification_url}</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;" />
        <p style="font-size: 12px; color: #a0a0b8; text-align: center;">If you didn't create an account, you can safely ignore this email.</p>
    </div>
    """


def render_welcome_email(name: str, dashboard_url: str) -> str:
    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 32px 24px;">
        <div style="text-align: center; margin-bottom: 32px;">
            <div style="width: 48px; height: 48px; border-radius: 12px; background: #3b82f6; display: inline-flex; align-items: center; justify-content: center; color: white; font-size: 20px; font-weight: bold;">R</div>
            <h1 style="font-size: 24px; margin-top: 16px; color: #1a1a2e;">Welcome to RAGInspector!</h1>
        </div>
        <p style="font-size: 16px; color: #4a4a6a; line-height: 1.6;">Hi <strong>{name}</strong>,</p>
        <p style="font-size: 16px; color: #4a4a6a; line-height: 1.6;">Your email has been verified and you're all set! Here's how to get started:</p>
        <div style="margin: 24px 0;">
            <div style="display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #f8f8ff; border-radius: 8px;">
                <div style="width: 32px; height: 32px; border-radius: 8px; background: #3b82f6; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; flex-shrink: 0;">1</div>
                <div>
                    <p style="font-weight: 600; margin: 0; color: #1a1a2e;">Install the SDK</p>
                    <p style="font-size: 14px; color: #6a6a8a; margin: 4px 0 0;"><code style="background: #e8e8ff; padding: 2px 6px; border-radius: 4px;">pip install raginspector</code></p>
                </div>
            </div>
            <div style="display: flex; gap: 12px; margin-bottom: 16px; padding: 16px; background: #f8f8ff; border-radius: 8px;">
                <div style="width: 32px; height: 32px; border-radius: 8px; background: #3b82f6; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; flex-shrink: 0;">2</div>
                <div>
                    <p style="font-weight: 600; margin: 0; color: #1a1a2e;">Create an API Key</p>
                    <p style="font-size: 14px; color: #6a6a8a; margin: 4px 0 0;">Go to Settings → API Keys in the dashboard</p>
                </div>
            </div>
            <div style="display: flex; gap: 12px; padding: 16px; background: #f8f8ff; border-radius: 8px;">
                <div style="width: 32px; height: 32px; border-radius: 8px; background: #3b82f6; color: white; display: flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px; flex-shrink: 0;">3</div>
                <div>
                    <p style="font-weight: 600; margin: 0; color: #1a1a2e;">Trace your first query</p>
                    <p style="font-size: 14px; color: #6a6a8a; margin: 4px 0 0;">Add <code style="background: #e8e8ff; padding: 2px 6px; border-radius: 4px;">@inspector.trace_retrieval</code> decorators to your RAG pipeline</p>
                </div>
            </div>
        </div>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{dashboard_url}" style="display: inline-block; background: #3b82f6; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">Go to Dashboard</a>
        </div>
        <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;" />
        <p style="font-size: 12px; color: #a0a0b8; text-align: center;">Your first 100 queries are free — no credit card needed.</p>
    </div>
    """


def render_password_reset_email(name: str, reset_url: str) -> str:
    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 32px 24px;">
        <div style="text-align: center; margin-bottom: 32px;">
            <div style="width: 48px; height: 48px; border-radius: 12px; background: #3b82f6; display: inline-flex; align-items: center; justify-content: center; color: white; font-size: 20px; font-weight: bold;">R</div>
            <h1 style="font-size: 24px; margin-top: 16px; color: #1a1a2e;">Reset your password</h1>
        </div>
        <p style="font-size: 16px; color: #4a4a6a; line-height: 1.6;">Hi <strong>{name}</strong>,</p>
        <p style="font-size: 16px; color: #4a4a6a; line-height: 1.6;">We received a request to reset your password. Click the button below to set a new one.</p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{reset_url}" style="display: inline-block; background: #3b82f6; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">Reset Password</a>
        </div>
        <p style="font-size: 14px; color: #8a8aa0; line-height: 1.6;">Or copy and paste this link in your browser:</p>
        <p style="font-size: 13px; color: #3b82f6; word-break: break-all; background: #f5f5ff; padding: 12px; border-radius: 8px;">{reset_url}</p>
        <p style="font-size: 14px; color: #8a8aa0; margin-top: 24px;">This link expires in 1 hour. If you didn't request a password reset, you can safely ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;" />
        <p style="font-size: 12px; color: #a0a0b8; text-align: center;">RAGInspector — Monitor your AI's trustworthiness.</p>
    </div>
    """


def render_alert_email(
    name: str, pipeline_name: str, hallucination_rate: float, threshold: float, dashboard_url: str
) -> str:
    color = "#ef4444" if hallucination_rate > threshold else "#f59e0b"
    return f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 560px; margin: 0 auto; padding: 32px 24px;">
        <div style="text-align: center; margin-bottom: 32px;">
            <div style="width: 48px; height: 48px; border-radius: 12px; background: {color}; display: inline-flex; align-items: center; justify-content: center; color: white; font-size: 24px;">⚠</div>
            <h1 style="font-size: 24px; margin-top: 16px; color: #1a1a2e;">Hallucination Alert</h1>
        </div>
        <p style="font-size: 16px; color: #4a4a6a; line-height: 1.6;">Hi <strong>{name}</strong>,</p>
        <p style="font-size: 16px; color: #4a4a6a; line-height: 1.6;">Your RAG pipeline <strong>{pipeline_name}</strong> has a hallucination rate of <strong style="color: {color};">{hallucination_rate:.1%}</strong>, which exceeds your threshold of {threshold:.0%}.</p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{dashboard_url}" style="display: inline-block; background: {color}; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">Investigate in Dashboard</a>
        </div>
        <hr style="border: none; border-top: 1px solid #eee; margin: 32px 0;" />
        <p style="font-size: 12px; color: #a0a0b8; text-align: center;">RAGInspector v2.0 — AI Trustworthiness Monitoring</p>
    </div>
    """
