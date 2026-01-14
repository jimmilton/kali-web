"""Integration services for external platforms (Slack, Jira, Discord)."""

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class SlackService:
    """Service for sending Slack notifications via webhooks."""

    @staticmethod
    async def send_message(
        webhook_url: str,
        message: str,
        *,
        blocks: Optional[list] = None,
        attachments: Optional[list] = None,
    ) -> bool:
        """
        Send a message to Slack via webhook.

        Args:
            webhook_url: Slack incoming webhook URL
            message: Plain text message (fallback)
            blocks: Optional Slack Block Kit blocks
            attachments: Optional Slack attachments

        Returns:
            True if successful, False otherwise
        """
        payload: dict[str, Any] = {"text": message}

        if blocks:
            payload["blocks"] = blocks
        if attachments:
            payload["attachments"] = attachments

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(webhook_url, json=payload)

                if response.status_code == 200:
                    logger.info("Slack message sent successfully")
                    return True
                else:
                    logger.error(f"Slack webhook failed: {response.status_code} - {response.text}")
                    return False
        except httpx.TimeoutException:
            logger.error("Slack webhook timed out")
            return False
        except Exception as e:
            logger.exception(f"Failed to send Slack message: {e}")
            return False

    @staticmethod
    def format_vulnerability_message(
        title: str,
        severity: str,
        project_name: str,
        asset: Optional[str] = None,
        url: Optional[str] = None,
    ) -> dict:
        """Format a vulnerability notification for Slack."""
        severity_emoji = {
            "critical": ":rotating_light:",
            "high": ":warning:",
            "medium": ":large_orange_diamond:",
            "low": ":large_blue_diamond:",
            "info": ":information_source:",
        }

        severity_color = {
            "critical": "#dc2626",
            "high": "#f97316",
            "medium": "#eab308",
            "low": "#22c55e",
            "info": "#3b82f6",
        }

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{severity_emoji.get(severity.lower(), ':bug:')} New {severity.upper()} Vulnerability",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Title:*\n{title}"},
                    {"type": "mrkdwn", "text": f"*Project:*\n{project_name}"},
                ],
            },
        ]

        if asset:
            blocks.append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Asset:*\n{asset}"},
                ],
            })

        if url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Details"},
                        "url": url,
                    },
                ],
            })

        return {
            "text": f"New {severity} vulnerability: {title}",
            "blocks": blocks,
            "attachments": [{"color": severity_color.get(severity.lower(), "#6b7280")}],
        }

    @staticmethod
    def format_job_completion_message(
        tool_name: str,
        status: str,
        project_name: str,
        assets_created: int = 0,
        vulnerabilities_found: int = 0,
        url: Optional[str] = None,
    ) -> dict:
        """Format a job completion notification for Slack."""
        status_emoji = {
            "completed": ":white_check_mark:",
            "failed": ":x:",
            "cancelled": ":no_entry:",
        }

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{status_emoji.get(status, ':gear:')} Job {status.title()}: {tool_name}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Project:*\n{project_name}"},
                    {"type": "mrkdwn", "text": f"*Status:*\n{status.title()}"},
                ],
            },
        ]

        if status == "completed" and (assets_created > 0 or vulnerabilities_found > 0):
            blocks.append({
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Assets Created:*\n{assets_created}"},
                    {"type": "mrkdwn", "text": f"*Vulnerabilities:*\n{vulnerabilities_found}"},
                ],
            })

        if url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "View Job"},
                        "url": url,
                    },
                ],
            })

        return {
            "text": f"Job {status}: {tool_name} in {project_name}",
            "blocks": blocks,
        }


class JiraService:
    """Service for creating Jira issues."""

    def __init__(
        self,
        base_url: str,
        email: str,
        api_token: str,
    ):
        """
        Initialize Jira service.

        Args:
            base_url: Jira instance URL (e.g., https://your-domain.atlassian.net)
            email: User email for authentication
            api_token: Jira API token
        """
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token

    async def create_issue(
        self,
        project_key: str,
        summary: str,
        description: str,
        issue_type: str = "Bug",
        priority: Optional[str] = None,
        labels: Optional[list[str]] = None,
        components: Optional[list[str]] = None,
        custom_fields: Optional[dict] = None,
    ) -> Optional[dict]:
        """
        Create a Jira issue.

        Args:
            project_key: Jira project key (e.g., "SEC")
            summary: Issue title
            description: Issue description (supports Jira markdown)
            issue_type: Issue type (Bug, Task, Story, etc.)
            priority: Priority level (Highest, High, Medium, Low, Lowest)
            labels: List of labels
            components: List of component names
            custom_fields: Additional custom fields

        Returns:
            Created issue data or None if failed
        """
        url = f"{self.base_url}/rest/api/3/issue"

        fields: dict[str, Any] = {
            "project": {"key": project_key},
            "summary": summary,
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": description}],
                    }
                ],
            },
            "issuetype": {"name": issue_type},
        }

        if priority:
            fields["priority"] = {"name": priority}

        if labels:
            fields["labels"] = labels

        if components:
            fields["components"] = [{"name": c} for c in components]

        if custom_fields:
            fields.update(custom_fields)

        payload = {"fields": fields}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    auth=(self.email, self.api_token),
                    headers={"Content-Type": "application/json"},
                )

                if response.status_code == 201:
                    data = response.json()
                    logger.info(f"Created Jira issue: {data.get('key')}")
                    return data
                else:
                    logger.error(f"Failed to create Jira issue: {response.status_code} - {response.text}")
                    return None
        except httpx.TimeoutException:
            logger.error("Jira API request timed out")
            return None
        except Exception as e:
            logger.exception(f"Failed to create Jira issue: {e}")
            return None

    async def test_connection(self) -> bool:
        """Test the Jira connection."""
        url = f"{self.base_url}/rest/api/3/myself"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    auth=(self.email, self.api_token),
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Jira connection test failed: {e}")
            return False

    @staticmethod
    def format_vulnerability_description(
        severity: str,
        description: Optional[str],
        evidence: Optional[str],
        remediation: Optional[str],
        cvss_score: Optional[float],
        cve_ids: Optional[list[str]],
        references: Optional[list[str]],
    ) -> str:
        """Format a vulnerability for Jira description."""
        parts = []

        parts.append(f"h2. Severity: {severity.upper()}")

        if cvss_score:
            parts.append(f"*CVSS Score:* {cvss_score}")

        if cve_ids:
            parts.append(f"*CVE IDs:* {', '.join(cve_ids)}")

        if description:
            parts.append("\nh2. Description")
            parts.append(description)

        if evidence:
            parts.append("\nh2. Evidence")
            parts.append("{code}")
            parts.append(evidence[:2000])
            parts.append("{code}")

        if remediation:
            parts.append("\nh2. Remediation")
            parts.append(remediation)

        if references:
            parts.append("\nh2. References")
            for ref in references[:10]:
                parts.append(f"* [{ref}|{ref}]")

        return "\n".join(parts)


class DiscordService:
    """Service for sending Discord notifications via webhooks."""

    @staticmethod
    async def send_message(
        webhook_url: str,
        content: str,
        *,
        embeds: Optional[list] = None,
        username: str = "Kwebbie",
    ) -> bool:
        """
        Send a message to Discord via webhook.

        Args:
            webhook_url: Discord webhook URL
            content: Message content
            embeds: Optional embed objects
            username: Bot username to display

        Returns:
            True if successful, False otherwise
        """
        payload: dict[str, Any] = {
            "content": content,
            "username": username,
        }

        if embeds:
            payload["embeds"] = embeds

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(webhook_url, json=payload)

                if response.status_code in [200, 204]:
                    logger.info("Discord message sent successfully")
                    return True
                else:
                    logger.error(f"Discord webhook failed: {response.status_code} - {response.text}")
                    return False
        except httpx.TimeoutException:
            logger.error("Discord webhook timed out")
            return False
        except Exception as e:
            logger.exception(f"Failed to send Discord message: {e}")
            return False

    @staticmethod
    def format_vulnerability_embed(
        title: str,
        severity: str,
        project_name: str,
        description: Optional[str] = None,
        asset: Optional[str] = None,
        url: Optional[str] = None,
    ) -> dict:
        """Format a vulnerability notification embed for Discord."""
        severity_color = {
            "critical": 0xdc2626,
            "high": 0xf97316,
            "medium": 0xeab308,
            "low": 0x22c55e,
            "info": 0x3b82f6,
        }

        embed = {
            "title": f":bug: New {severity.upper()} Vulnerability",
            "color": severity_color.get(severity.lower(), 0x6b7280),
            "fields": [
                {"name": "Title", "value": title, "inline": False},
                {"name": "Project", "value": project_name, "inline": True},
                {"name": "Severity", "value": severity.upper(), "inline": True},
            ],
        }

        if asset:
            embed["fields"].append({"name": "Asset", "value": asset, "inline": False})

        if description:
            embed["description"] = description[:500]

        if url:
            embed["url"] = url

        return embed
