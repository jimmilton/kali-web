"""WPScan JSON output parser."""

import json
import logging
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
    ParsedCredential,
    ParseOutput,
)

logger = logging.getLogger(__name__)


class WPScanParser(BaseParser):
    """Parser for WPScan JSON output."""

    tool_name = "wpscan"
    creates_assets = True
    creates_vulnerabilities = True
    creates_credentials = True

    # WPScan doesn't provide severity, estimate based on vuln type
    VULN_TYPE_SEVERITY = {
        "rce": VulnerabilitySeverity.CRITICAL.value,
        "sqli": VulnerabilitySeverity.CRITICAL.value,
        "sql injection": VulnerabilitySeverity.CRITICAL.value,
        "file upload": VulnerabilitySeverity.CRITICAL.value,
        "arbitrary file": VulnerabilitySeverity.HIGH.value,
        "xss": VulnerabilitySeverity.MEDIUM.value,
        "csrf": VulnerabilitySeverity.MEDIUM.value,
        "lfi": VulnerabilitySeverity.HIGH.value,
        "rfi": VulnerabilitySeverity.CRITICAL.value,
        "ssrf": VulnerabilitySeverity.HIGH.value,
        "idor": VulnerabilitySeverity.MEDIUM.value,
        "information disclosure": VulnerabilitySeverity.LOW.value,
        "default": VulnerabilitySeverity.MEDIUM.value,
    }

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse WPScan JSON output."""
        result = ParseOutput()

        try:
            # Find JSON in output (WPScan may have non-JSON prefix/suffix)
            json_start = output.find("{")
            json_end = output.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = output[json_start:json_end]
                data = json.loads(json_str)
                self._process_scan_data(data, result)
            else:
                result.errors.append("No valid JSON found in output")
        except json.JSONDecodeError as e:
            result.errors.append(f"JSON parse error: {e}")
        except Exception as e:
            result.errors.append(f"Error processing WPScan output: {e}")
            logger.exception(f"Error processing WPScan output: {e}")

        logger.info(
            f"WPScan parsing complete: {len(result.assets)} assets, "
            f"{len(result.vulnerabilities)} vulnerabilities"
        )

        return result

    def _process_scan_data(self, data: dict, result: ParseOutput) -> None:
        """Process complete WPScan JSON data."""
        target_url = data.get("target_url", "")

        # Create target asset
        if target_url:
            parsed = urlparse(target_url)
            result.assets.append(
                ParsedAsset(
                    type=AssetType.URL.value,
                    value=target_url,
                    metadata={
                        "wordpress": True,
                        "scheme": parsed.scheme,
                        "netloc": parsed.netloc,
                    },
                    tags=["wpscan", "wordpress"],
                )
            )

        # Process version info
        version_info = data.get("version", {})
        if version_info:
            wp_version = version_info.get("number", "")
            if wp_version:
                result.assets[0].metadata["wordpress_version"] = wp_version
                result.assets[0].metadata["version_status"] = version_info.get("status", "")

            # Process version vulnerabilities
            for vuln in version_info.get("vulnerabilities", []):
                self._add_vulnerability(vuln, result, target_url, "WordPress Core")

        # Process main theme
        main_theme = data.get("main_theme", {})
        if main_theme:
            self._process_component(main_theme, result, target_url, "theme")

        # Process plugins
        plugins = data.get("plugins", {})
        for plugin_name, plugin_data in plugins.items():
            self._process_component(plugin_data, result, target_url, "plugin", plugin_name)

        # Process themes
        themes = data.get("themes", {})
        for theme_name, theme_data in themes.items():
            self._process_component(theme_data, result, target_url, "theme", theme_name)

        # Process users
        users = data.get("users", {})
        for username, user_data in users.items():
            self._add_user(username, user_data, result, target_url)

        # Process password attack results
        password_attack = data.get("password_attack", {})
        for username, password in password_attack.items():
            result.credentials.append(
                ParsedCredential(
                    username=username,
                    password=password,
                    service="wordpress",
                    url=target_url,
                    credential_type="password",
                    metadata={"source": "wpscan-bruteforce"},
                    asset_value=target_url,
                    asset_type=AssetType.URL.value,
                )
            )

    def _process_component(
        self,
        component: dict,
        result: ParseOutput,
        target_url: str,
        component_type: str,
        name: str = None,
    ) -> None:
        """Process a WordPress component (plugin/theme)."""
        slug = component.get("slug", name or "unknown")
        version = component.get("version", {})
        version_number = version.get("number", "") if isinstance(version, dict) else str(version)

        # Add component info to metadata
        component_info = {
            "type": component_type,
            "slug": slug,
            "version": version_number,
            "location": component.get("location", ""),
            "latest_version": component.get("latest_version", ""),
            "outdated": component.get("outdated", False),
        }

        # Process vulnerabilities
        for vuln in component.get("vulnerabilities", []):
            self._add_vulnerability(
                vuln, result, target_url, f"{component_type.title()}: {slug}"
            )

    def _add_vulnerability(
        self,
        vuln: dict,
        result: ParseOutput,
        target_url: str,
        component: str,
    ) -> None:
        """Add a vulnerability from WPScan data."""
        title = vuln.get("title", "Unknown Vulnerability")
        vuln_type = vuln.get("vuln_type", "")

        # Determine severity based on title/type
        severity = self._estimate_severity(title, vuln_type)

        # Get references
        references = []
        refs = vuln.get("references", {})
        for ref_type, ref_list in refs.items():
            if isinstance(ref_list, list):
                references.extend(ref_list)
            elif isinstance(ref_list, str):
                references.append(ref_list)

        # Extract CVE IDs
        cve_ids = refs.get("cve", [])
        if isinstance(cve_ids, str):
            cve_ids = [cve_ids]
        cve_ids = [f"CVE-{cve}" if not cve.upper().startswith("CVE-") else cve for cve in cve_ids]

        # Get CVSS if available
        cvss = vuln.get("cvss", {})
        cvss_score = None
        cvss_vector = None
        if cvss:
            cvss_score = cvss.get("score")
            cvss_vector = cvss.get("vector")

        result.vulnerabilities.append(
            ParsedVulnerability(
                title=title,
                severity=severity,
                description=f"WordPress vulnerability in {component}: {title}",
                cvss_score=cvss_score,
                cvss_vector=cvss_vector,
                cve_ids=cve_ids,
                references=references,
                template_id=vuln.get("wpvulndb", {}).get("id"),
                tags=["wpscan", "wordpress", vuln_type] if vuln_type else ["wpscan", "wordpress"],
                metadata={
                    "component": component,
                    "vuln_type": vuln_type,
                    "fixed_in": vuln.get("fixed_in", ""),
                },
                asset_value=target_url,
                asset_type=AssetType.URL.value,
            )
        )

    def _add_user(
        self,
        username: str,
        user_data: dict,
        result: ParseOutput,
        target_url: str,
    ) -> None:
        """Add a discovered WordPress user."""
        result.credentials.append(
            ParsedCredential(
                username=username,
                service="wordpress",
                url=target_url,
                credential_type="username",
                metadata={
                    "id": user_data.get("id"),
                    "slug": user_data.get("slug"),
                    "confidence": user_data.get("confidence", 0),
                },
                asset_value=target_url,
                asset_type=AssetType.URL.value,
            )
        )

    def _estimate_severity(self, title: str, vuln_type: str) -> str:
        """Estimate severity based on vulnerability title and type."""
        title_lower = title.lower()
        vuln_type_lower = vuln_type.lower() if vuln_type else ""

        for keyword, severity in self.VULN_TYPE_SEVERITY.items():
            if keyword in title_lower or keyword in vuln_type_lower:
                return severity

        return self.VULN_TYPE_SEVERITY["default"]


# Register the parser
register_parser("wpscan_parser", WPScanParser)
