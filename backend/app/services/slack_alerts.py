"""
Slack alerting service (PRD v2.0).
Sends alerts to Slack webhooks when hallucination spikes are detected.
Free tier: Slack webhooks are free.
"""

import httpx
import structlog

logger = structlog.get_logger()


async def send_slack_alert(
    webhook_url: str,
    message: str,
    color: str = "danger",
) -> bool:
    """
    Send an alert to a Slack webhook.

    Args:
        webhook_url: Slack Incoming Webhook URL
        message: The alert message to send
        color: 'danger' (red), 'warning' (amber), 'good' (green)

    Returns:
        True if sent successfully
    """
    if not webhook_url or not webhook_url.startswith("https://hooks.slack.com/"):
        logger.warning("Invalid Slack webhook URL")
        return False

    payload = {
        "attachments": [
            {
                "color": color,
                "title": "RAGInspector Alert",
                "text": message,
                "footer": "RAGInspector",
                "ts": int(__import__("time").time()),
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            if resp.status_code == 200:
                logger.info("Slack alert sent successfully")
                return True
            else:
                logger.warning(
                    "Slack alert failed",
                    status=resp.status_code,
                    body=resp.text[:200],
                )
                return False
    except Exception as e:
        logger.warning("Slack alert send error", error=str(e))
        return False


def send_slack_alert_sync(
    webhook_url: str,
    message: str,
    color: str = "danger",
) -> bool:
    """Synchronous Slack webhook send for Celery workers."""
    if not webhook_url or not webhook_url.startswith("https://hooks.slack.com/"):
        logger.warning("Invalid Slack webhook URL")
        return False

    payload = {
        "attachments": [
            {
                "color": color,
                "title": "RAGInspector Alert",
                "text": message,
                "footer": "RAGInspector",
                "ts": int(__import__("time").time()),
            }
        ]
    }
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            return resp.status_code == 200
    except Exception as e:
        logger.warning("Slack alert send error", error=str(e))
        return False


def send_hallucination_alert_sync(
    webhook_url: str,
    pipeline_name: str,
    query_text: str,
    grounded_fraction: float | None,
    dashboard_url: str,
) -> bool:
    message = (
        f"*Hallucination detected*\n"
        f"*Pipeline:* {pipeline_name}\n"
        f"*Query:* {query_text[:200]}\n"
        f"*Grounded fraction:* {grounded_fraction if grounded_fraction is not None else 'n/a'}\n"
        f"*Dashboard:* {dashboard_url}"
    )
    return send_slack_alert_sync(webhook_url, message, color="danger")


async def send_daily_summary_alert(
    webhook_url: str,
    user_name: str,
    trustworthiness_score: float,
    total_queries: int,
    hallucination_count: int,
    top_failure_type: str,
    dashboard_url: str,
) -> bool:
    """
    Send a daily summary alert to Slack.
    """
    color = (
        "good"
        if trustworthiness_score >= 80
        else ("warning" if trustworthiness_score >= 60 else "danger")
    )
    message = (
        f"*📊 RAGInspector Daily Summary*\n"
        f"*User:* {user_name}\n"
        f"*AI Trustworthiness Score:* {trustworthiness_score}/100\n"
        f"*Total Queries:* {total_queries}\n"
        f"*Hallucinations Detected:* {hallucination_count}\n"
        f"*Top Failure Type:* {top_failure_type.replace('_', ' ').title()}\n"
        f"*Dashboard:* {dashboard_url}"
    )
    return await send_slack_alert(webhook_url, message, color=color)
