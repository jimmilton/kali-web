"""Notification tasks."""

import asyncio
import logging
from typing import Any, Optional

from celery import shared_task

from app.services.integrations import SlackService, DiscordService

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


@shared_task
def send_email_notification(to: str, subject: str, body: str):
    """Send email notification."""
    logger.info(f"Sending email to {to}: {subject}")
    # TODO: Implement email sending with SMTP
    # For now, just log the message
    logger.info(f"Email notification: {subject} - {body[:100]}...")


@shared_task
def send_slack_notification(
    webhook_url: str,
    message: str,
    blocks: Optional[list] = None,
    attachments: Optional[list] = None,
):
    """Send Slack notification."""
    logger.info(f"Sending Slack notification: {message[:50]}...")

    async def _send():
        return await SlackService.send_message(
            webhook_url=webhook_url,
            message=message,
            blocks=blocks,
            attachments=attachments,
        )

    success = run_async(_send())
    if not success:
        logger.error("Failed to send Slack notification")
    return success


@shared_task
def send_discord_notification(
    webhook_url: str,
    content: str,
    embeds: Optional[list] = None,
):
    """Send Discord notification."""
    logger.info(f"Sending Discord notification: {content[:50]}...")

    async def _send():
        return await DiscordService.send_message(
            webhook_url=webhook_url,
            content=content,
            embeds=embeds,
        )

    success = run_async(_send())
    if not success:
        logger.error("Failed to send Discord notification")
    return success


@shared_task
def send_vulnerability_notification(
    webhook_type: str,
    webhook_url: str,
    title: str,
    severity: str,
    project_name: str,
    asset: Optional[str] = None,
    description: Optional[str] = None,
    view_url: Optional[str] = None,
):
    """
    Send a vulnerability notification to configured webhook.

    Args:
        webhook_type: Type of webhook (slack, discord)
        webhook_url: Webhook URL
        title: Vulnerability title
        severity: Severity level
        project_name: Project name
        asset: Associated asset
        description: Vulnerability description
        view_url: URL to view vulnerability details
    """
    logger.info(f"Sending {severity} vulnerability notification for: {title}")

    if webhook_type == "slack":
        formatted = SlackService.format_vulnerability_message(
            title=title,
            severity=severity,
            project_name=project_name,
            asset=asset,
            url=view_url,
        )

        async def _send():
            return await SlackService.send_message(
                webhook_url=webhook_url,
                message=formatted["text"],
                blocks=formatted.get("blocks"),
                attachments=formatted.get("attachments"),
            )

        success = run_async(_send())

    elif webhook_type == "discord":
        embed = DiscordService.format_vulnerability_embed(
            title=title,
            severity=severity,
            project_name=project_name,
            description=description,
            asset=asset,
            url=view_url,
        )

        async def _send():
            return await DiscordService.send_message(
                webhook_url=webhook_url,
                content=f"New {severity} vulnerability found!",
                embeds=[embed],
            )

        success = run_async(_send())

    else:
        logger.warning(f"Unknown webhook type: {webhook_type}")
        return False

    return success


@shared_task
def send_job_completion_notification(
    webhook_type: str,
    webhook_url: str,
    tool_name: str,
    status: str,
    project_name: str,
    assets_created: int = 0,
    vulnerabilities_found: int = 0,
    view_url: Optional[str] = None,
):
    """
    Send a job completion notification to configured webhook.

    Args:
        webhook_type: Type of webhook (slack, discord)
        webhook_url: Webhook URL
        tool_name: Name of the tool that completed
        status: Job status (completed, failed, cancelled)
        project_name: Project name
        assets_created: Number of assets created
        vulnerabilities_found: Number of vulnerabilities found
        view_url: URL to view job details
    """
    logger.info(f"Sending job completion notification: {tool_name} - {status}")

    if webhook_type == "slack":
        formatted = SlackService.format_job_completion_message(
            tool_name=tool_name,
            status=status,
            project_name=project_name,
            assets_created=assets_created,
            vulnerabilities_found=vulnerabilities_found,
            url=view_url,
        )

        async def _send():
            return await SlackService.send_message(
                webhook_url=webhook_url,
                message=formatted["text"],
                blocks=formatted.get("blocks"),
            )

        success = run_async(_send())

    elif webhook_type == "discord":
        status_emoji = {
            "completed": ":white_check_mark:",
            "failed": ":x:",
            "cancelled": ":no_entry:",
        }

        embed = {
            "title": f"{status_emoji.get(status, ':gear:')} Job {status.title()}: {tool_name}",
            "color": 0x22c55e if status == "completed" else 0xdc2626 if status == "failed" else 0xf59e0b,
            "fields": [
                {"name": "Project", "value": project_name, "inline": True},
                {"name": "Status", "value": status.title(), "inline": True},
            ],
        }

        if status == "completed" and (assets_created > 0 or vulnerabilities_found > 0):
            embed["fields"].extend([
                {"name": "Assets Created", "value": str(assets_created), "inline": True},
                {"name": "Vulnerabilities", "value": str(vulnerabilities_found), "inline": True},
            ])

        if view_url:
            embed["url"] = view_url

        async def _send():
            return await DiscordService.send_message(
                webhook_url=webhook_url,
                content=f"Job {status}: {tool_name}",
                embeds=[embed],
            )

        success = run_async(_send())

    else:
        logger.warning(f"Unknown webhook type: {webhook_type}")
        return False

    return success
