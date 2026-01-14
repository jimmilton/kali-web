"""Nikto JSON output parser."""

import json
import logging
from typing import Optional

from app.models.asset import AssetType
from app.models.job import Job
from app.models.vulnerability import VulnerabilitySeverity
from app.tools.parsers import register_parser
from app.tools.parsers.base import (
    BaseParser,
    ParsedAsset,
    ParsedVulnerability,
    ParseOutput,
)

logger = logging.getLogger(__name__)


class NiktoParser(BaseParser):
    """Parser for Nikto JSON output."""

    tool_name = "nikto"
    creates_assets = True
    creates_vulnerabilities = True

    # OSVDB to severity mapping (higher OSVDB IDs are generally less severe)
    # This is a rough heuristic since Nikto doesn't provide severity
    def _get_severity(self, osvdb: str, message: str) -> str:
        """Determine severity based on OSVDB ID and message content."""
        message_lower = message.lower()

        # Critical indicators
        if any(word in message_lower for word in [
            "remote code execution", "rce", "command injection",
            "sql injection", "arbitrary file", "root", "admin access"
        ]):
            return VulnerabilitySeverity.CRITICAL.value

        # High indicators
        if any(word in message_lower for word in [
            "authentication bypass", "directory traversal", "path traversal",
            "file inclusion", "xss", "cross-site", "credentials",
            "password", "sensitive", "backup", "database"
        ]):
            return VulnerabilitySeverity.HIGH.value

        # Medium indicators
        if any(word in message_lower for word in [
            "disclosure", "information", "version", "outdated",
            "deprecated", "header", "cookie", "clickjacking"
        ]):
            return VulnerabilitySeverity.MEDIUM.value

        # Low indicators
        if any(word in message_lower for word in [
            "allowed", "methods", "options", "trace", "etag"
        ]):
            return VulnerabilitySeverity.LOW.value

        return VulnerabilitySeverity.INFO.value

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse Nikto JSON output."""
        result = ParseOutput()

        try:
            # Nikto can output various JSON formats
            data = json.loads(output)

            # Handle array format
            if isinstance(data, list):
                for item in data:
                    self._process_host(item, result)
            # Handle object format
            elif isinstance(data, dict):
                # Check if it's wrapped in a hosts array
                if "hosts" in data and isinstance(data["hosts"], list):
                    for host in data["hosts"]:
                        self._process_host(host, result)
                else:
                    # Single host object - process directly
                    self._process_host(data, result)

        except json.JSONDecodeError as e:
            result.errors.append(f"JSON parse error: {e}")
            logger.error(f"Failed to parse Nikto JSON: {e}")

        logger.info(
            f"Nikto parsing complete: {len(result.assets)} assets, "
            f"{len(result.vulnerabilities)} vulnerabilities"
        )
        return result

    def _process_host(self, host_data: dict, result: ParseOutput) -> None:
        """Process a single host's results."""
        # Get host info
        ip = host_data.get("ip", host_data.get("host", ""))
        hostname = host_data.get("hostname", "")
        port = host_data.get("port", 80)
        banner = host_data.get("banner", "")

        if not ip and not hostname:
            return

        target = hostname or ip

        # Create host asset
        result.assets.append(
            ParsedAsset(
                type=AssetType.HOST.value if self._is_ip(target) else AssetType.DOMAIN.value,
                value=target,
                metadata={
                    "ip": ip,
                    "hostname": hostname,
                    "port": port,
                    "banner": banner,
                },
                tags=["nikto"],
            )
        )

        # Process vulnerabilities
        vulns = host_data.get("vulnerabilities", host_data.get("items", []))
        for vuln in vulns:
            self._process_vulnerability(vuln, target, port, result)

    def _process_vulnerability(
        self, vuln: dict, target: str, port: int, result: ParseOutput
    ) -> None:
        """Process a single vulnerability."""
        # Extract fields (Nikto uses various field names)
        vuln_id = vuln.get("id", vuln.get("OSVDB", ""))
        message = vuln.get("msg", vuln.get("message", vuln.get("description", "")))
        method = vuln.get("method", "GET")
        uri = vuln.get("uri", vuln.get("url", ""))
        references = vuln.get("references", [])

        if isinstance(vuln_id, int):
            vuln_id = str(vuln_id)

        if not message:
            return

        # Determine severity
        severity = self._get_severity(vuln_id, message)

        # Build references list
        if isinstance(references, str):
            references = [references] if references else []

        # Add OSVDB reference if applicable
        if vuln_id and vuln_id.isdigit():
            references.append(f"https://osvdb.org/{vuln_id}")

        # Create vulnerability
        result.vulnerabilities.append(
            ParsedVulnerability(
                title=f"Nikto: {message[:100]}..." if len(message) > 100 else f"Nikto: {message}",
                severity=severity,
                description=message,
                evidence=f"URI: {uri}\nMethod: {method}" if uri else None,
                references=references,
                template_id=f"nikto:{vuln_id}" if vuln_id else None,
                tags=["nikto"],
                metadata={
                    "nikto_id": vuln_id,
                    "method": method,
                    "uri": uri,
                    "port": port,
                },
                asset_value=target,
                asset_type=AssetType.HOST.value if self._is_ip(target) else AssetType.DOMAIN.value,
            )
        )

    def _is_ip(self, host: str) -> bool:
        """Check if host is an IP address."""
        import re
        ipv4_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        return bool(re.match(ipv4_pattern, host))


# Register the parser
register_parser("nikto_parser", NiktoParser)
