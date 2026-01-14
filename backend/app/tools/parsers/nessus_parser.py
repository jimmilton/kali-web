"""Nessus XML output parser for importing external scan results."""

import logging
import xml.etree.ElementTree as ET
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


class NessusParser(BaseParser):
    """Parser for Nessus .nessus XML files."""

    tool_name = "nessus"
    creates_assets = True
    creates_vulnerabilities = True
    creates_credentials = False

    # Map Nessus severity (0-4) to our severity levels
    SEVERITY_MAP = {
        "0": VulnerabilitySeverity.INFO.value,  # Informational
        "1": VulnerabilitySeverity.LOW.value,   # Low
        "2": VulnerabilitySeverity.MEDIUM.value, # Medium
        "3": VulnerabilitySeverity.HIGH.value,   # High
        "4": VulnerabilitySeverity.CRITICAL.value, # Critical
    }

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse Nessus XML output."""
        result = ParseOutput()
        seen_hosts = set()

        try:
            # Handle BOM and encoding issues
            if output.startswith('\ufeff'):
                output = output[1:]

            root = ET.fromstring(output)

            # Find all ReportHost elements
            for report in root.findall('.//Report'):
                for host in report.findall('ReportHost'):
                    self._process_host(host, result, seen_hosts)

            # Also check for direct ReportHost elements
            for host in root.findall('.//ReportHost'):
                if host not in root.findall('.//Report//ReportHost'):
                    self._process_host(host, result, seen_hosts)

        except ET.ParseError as e:
            result.errors.append(f"XML parse error: {e}")
            logger.error(f"Failed to parse Nessus XML: {e}")
        except Exception as e:
            result.errors.append(f"Error processing Nessus output: {e}")
            logger.exception(f"Error processing Nessus output: {e}")

        logger.info(
            f"Nessus parsing complete: {len(result.assets)} assets, "
            f"{len(result.vulnerabilities)} vulnerabilities"
        )

        return result

    def _process_host(
        self, host: ET.Element, result: ParseOutput, seen_hosts: set
    ) -> None:
        """Process a single Nessus ReportHost element."""
        # Get host information
        host_name = host.get("name", "")

        if not host_name or host_name in seen_hosts:
            return

        seen_hosts.add(host_name)

        # Get host properties
        host_props = {}
        props_elem = host.find("HostProperties")
        if props_elem is not None:
            for tag in props_elem.findall("tag"):
                tag_name = tag.get("name", "")
                tag_value = tag.text or ""
                host_props[tag_name] = tag_value

        # Determine asset type
        host_ip = host_props.get("host-ip", host_name)
        host_fqdn = host_props.get("host-fqdn", "")
        os_name = host_props.get("operating-system", "")
        mac_address = host_props.get("mac-address", "")

        # Create host asset
        is_ip = self._is_ip(host_ip)
        result.assets.append(
            ParsedAsset(
                type=AssetType.HOST.value if is_ip else AssetType.DOMAIN.value,
                value=host_ip,
                metadata={
                    "fqdn": host_fqdn,
                    "os": os_name,
                    "mac_address": mac_address,
                    "netbios_name": host_props.get("netbios-name", ""),
                    "system_type": host_props.get("system-type", ""),
                },
                tags=["nessus", "imported"],
            )
        )

        # Process vulnerabilities (ReportItem elements)
        for item in host.findall("ReportItem"):
            self._process_item(item, result, host_ip)

    def _process_item(
        self, item: ET.Element, result: ParseOutput, host: str
    ) -> None:
        """Process a single Nessus ReportItem element."""
        # Get basic info
        plugin_id = item.get("pluginID", "")
        plugin_name = item.get("pluginName", "")
        port = item.get("port", "0")
        protocol = item.get("protocol", "")
        svc_name = item.get("svc_name", "")
        severity = item.get("severity", "0")

        # Skip informational items unless they have useful data
        if severity == "0":
            return

        # Get detailed information
        description = self._get_text(item, "description")
        solution = self._get_text(item, "solution")
        synopsis = self._get_text(item, "synopsis")
        see_also = self._get_text(item, "see_also")
        plugin_output = self._get_text(item, "plugin_output")

        # Get CVE/CVSS info
        cve_list = [cve.text for cve in item.findall("cve") if cve.text]
        cvss_score = self._get_float(item, "cvss_base_score")
        cvss3_score = self._get_float(item, "cvss3_base_score")
        cvss_vector = self._get_text(item, "cvss_vector")
        cvss3_vector = self._get_text(item, "cvss3_vector")

        # Use CVSS3 if available, otherwise CVSS2
        final_cvss = cvss3_score if cvss3_score else cvss_score
        final_vector = cvss3_vector if cvss3_vector else cvss_vector

        # Get CWE
        cwe_list = []
        cwe = self._get_text(item, "cwe")
        if cwe:
            cwe_list = [f"CWE-{cwe}" if not cwe.startswith("CWE-") else cwe]

        # Get references
        references = []
        if see_also:
            references = [ref.strip() for ref in see_also.split("\n") if ref.strip()]

        # Build title
        title = plugin_name or f"Nessus Plugin {plugin_id}"

        # Create vulnerability
        result.vulnerabilities.append(
            ParsedVulnerability(
                title=title,
                severity=self.SEVERITY_MAP.get(severity, VulnerabilitySeverity.INFO.value),
                description=description or synopsis,
                cvss_score=final_cvss,
                cvss_vector=final_vector,
                cve_ids=cve_list,
                cwe_ids=cwe_list,
                evidence=plugin_output[:5000] if plugin_output else None,
                remediation=solution,
                references=references,
                template_id=f"nessus-{plugin_id}",
                tags=["nessus", "imported"],
                metadata={
                    "plugin_id": plugin_id,
                    "port": port,
                    "protocol": protocol,
                    "service": svc_name,
                    "synopsis": synopsis,
                    "risk_factor": self._get_text(item, "risk_factor"),
                    "exploit_available": self._get_text(item, "exploit_available"),
                    "exploitability_ease": self._get_text(item, "exploitability_ease"),
                },
                asset_value=host,
                asset_type=AssetType.HOST.value,
            )
        )

    def _get_text(self, element: ET.Element, tag: str) -> str:
        """Get text content of a child element."""
        child = element.find(tag)
        return child.text.strip() if child is not None and child.text else ""

    def _get_float(self, element: ET.Element, tag: str) -> Optional[float]:
        """Get float value from a child element."""
        text = self._get_text(element, tag)
        if text:
            try:
                return float(text)
            except ValueError:
                return None
        return None

    def _is_ip(self, host: str) -> bool:
        """Check if host is an IP address."""
        import re
        ipv4_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        ipv6_pattern = r"^[a-fA-F0-9:]+$"
        return bool(re.match(ipv4_pattern, host) or re.match(ipv6_pattern, host))


# Register the parser
register_parser("nessus_parser", NessusParser)
