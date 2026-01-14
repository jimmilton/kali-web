"""Burp Suite XML output parser for importing external scan results."""

import base64
import logging
import xml.etree.ElementTree as ET
from typing import Optional
from urllib.parse import urlparse

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


class BurpParser(BaseParser):
    """Parser for Burp Suite XML export files."""

    tool_name = "burp"
    creates_assets = True
    creates_vulnerabilities = True
    creates_credentials = False

    # Map Burp severity to our severity levels
    SEVERITY_MAP = {
        "information": VulnerabilitySeverity.INFO.value,
        "low": VulnerabilitySeverity.LOW.value,
        "medium": VulnerabilitySeverity.MEDIUM.value,
        "high": VulnerabilitySeverity.HIGH.value,
        "critical": VulnerabilitySeverity.CRITICAL.value,
    }

    # Map Burp confidence to severity adjustment
    CONFIDENCE_MAP = {
        "certain": 0,
        "firm": 0,
        "tentative": -1,  # Reduce severity for tentative findings
    }

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse Burp Suite XML output."""
        result = ParseOutput()
        seen_urls = set()

        try:
            # Handle BOM and encoding issues
            if output.startswith('\ufeff'):
                output = output[1:]

            root = ET.fromstring(output)

            # Process issues (Burp Scanner format)
            for issue in root.findall('.//issue'):
                self._process_issue(issue, result, seen_urls)

            # Process items (Burp HTTP history export format)
            for item in root.findall('.//item'):
                self._process_item(item, result, seen_urls)

        except ET.ParseError as e:
            result.errors.append(f"XML parse error: {e}")
            logger.error(f"Failed to parse Burp XML: {e}")
        except Exception as e:
            result.errors.append(f"Error processing Burp output: {e}")
            logger.exception(f"Error processing Burp output: {e}")

        logger.info(
            f"Burp parsing complete: {len(result.assets)} assets, "
            f"{len(result.vulnerabilities)} vulnerabilities"
        )

        return result

    def _process_issue(
        self, issue: ET.Element, result: ParseOutput, seen_urls: set
    ) -> None:
        """Process a Burp Scanner issue element."""
        # Get basic info
        name = self._get_text(issue, "name")
        host = self._get_text(issue, "host")
        path = self._get_text(issue, "path")
        location = self._get_text(issue, "location")
        severity = self._get_text(issue, "severity").lower()
        confidence = self._get_text(issue, "confidence").lower()
        issue_type = self._get_text(issue, "type")

        # Build URL
        host_elem = issue.find("host")
        protocol = "https" if host_elem is not None and host_elem.get("ip") else "http"
        if host_elem is not None:
            ip = host_elem.get("ip", "")
            if ip:
                protocol = "https" if "443" in str(host_elem.text) else "http"

        url = f"{protocol}://{host}{path}" if host else ""

        if not url or not name:
            return

        # Create URL asset if not seen
        if url not in seen_urls:
            seen_urls.add(url)
            parsed = urlparse(url)
            result.assets.append(
                ParsedAsset(
                    type=AssetType.URL.value,
                    value=url,
                    metadata={
                        "host": host,
                        "path": path,
                        "scheme": parsed.scheme,
                    },
                    tags=["burp", "imported"],
                )
            )

        # Get detailed information
        issue_background = self._get_text(issue, "issueBackground")
        issue_detail = self._get_text(issue, "issueDetail")
        remediation_background = self._get_text(issue, "remediationBackground")
        remediation_detail = self._get_text(issue, "remediationDetail")

        # Get request/response
        request_elem = issue.find(".//request")
        response_elem = issue.find(".//response")

        request = None
        response = None

        if request_elem is not None:
            is_base64 = request_elem.get("base64", "false").lower() == "true"
            if request_elem.text:
                request = self._decode_content(request_elem.text, is_base64)

        if response_elem is not None:
            is_base64 = response_elem.get("base64", "false").lower() == "true"
            if response_elem.text:
                response = self._decode_content(response_elem.text, is_base64)
                # Truncate large responses
                if len(response) > 5000:
                    response = response[:5000] + "\n... [truncated]"

        # Build description
        description = ""
        if issue_background:
            description = self._strip_html(issue_background)
        if issue_detail:
            description += f"\n\nDetails:\n{self._strip_html(issue_detail)}"

        # Build remediation
        remediation = ""
        if remediation_background:
            remediation = self._strip_html(remediation_background)
        if remediation_detail:
            remediation += f"\n\n{self._strip_html(remediation_detail)}"

        # Map severity
        mapped_severity = self.SEVERITY_MAP.get(severity, VulnerabilitySeverity.INFO.value)

        # Get references
        references = []
        refs = issue.find("references")
        if refs is not None and refs.text:
            # Extract URLs from HTML-formatted references
            import re
            urls = re.findall(r'href=["\']([^"\']+)["\']', refs.text)
            references.extend(urls)

        # Create vulnerability
        result.vulnerabilities.append(
            ParsedVulnerability(
                title=name,
                severity=mapped_severity,
                description=description.strip() if description else None,
                remediation=remediation.strip() if remediation else None,
                references=references,
                template_id=f"burp-{issue_type}" if issue_type else None,
                request=request[:5000] if request else None,
                response=response,
                tags=["burp", "imported"],
                metadata={
                    "issue_type": issue_type,
                    "confidence": confidence,
                    "location": location,
                    "host": host,
                    "path": path,
                },
                asset_value=url,
                asset_type=AssetType.URL.value,
            )
        )

    def _process_item(
        self, item: ET.Element, result: ParseOutput, seen_urls: set
    ) -> None:
        """Process a Burp HTTP history item (for HTTP history exports)."""
        # Get URL components
        host = self._get_text(item, "host")
        port = self._get_text(item, "port")
        protocol = self._get_text(item, "protocol")
        path = self._get_text(item, "path")

        if not host:
            return

        # Build URL
        if port and port not in ["80", "443"]:
            url = f"{protocol}://{host}:{port}{path}"
        else:
            url = f"{protocol}://{host}{path}"

        # Create URL asset if not seen
        if url not in seen_urls:
            seen_urls.add(url)
            result.assets.append(
                ParsedAsset(
                    type=AssetType.URL.value,
                    value=url,
                    metadata={
                        "host": host,
                        "port": port,
                        "protocol": protocol,
                        "path": path,
                        "method": self._get_text(item, "method"),
                        "status": self._get_text(item, "status"),
                        "mimetype": self._get_text(item, "mimetype"),
                    },
                    tags=["burp", "imported", "http-history"],
                )
            )

    def _get_text(self, element: ET.Element, tag: str) -> str:
        """Get text content of a child element."""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return ""

    def _decode_content(self, content: str, is_base64: bool) -> str:
        """Decode content, optionally from base64."""
        if is_base64:
            try:
                return base64.b64decode(content).decode("utf-8", errors="replace")
            except Exception:
                return content
        return content

    def _strip_html(self, text: str) -> str:
        """Strip HTML tags from text."""
        import re
        # Remove HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        clean = clean.replace("&lt;", "<")
        clean = clean.replace("&gt;", ">")
        clean = clean.replace("&amp;", "&")
        clean = clean.replace("&quot;", '"')
        clean = clean.replace("&#39;", "'")
        clean = clean.replace("&nbsp;", " ")
        # Normalize whitespace
        clean = re.sub(r'\s+', ' ', clean)
        return clean.strip()


# Register the parser
register_parser("burp_parser", BurpParser)
