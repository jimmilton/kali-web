"""Nmap XML output parser."""

import logging
import xml.etree.ElementTree as ET
from typing import List, Optional

from app.models.asset import AssetType
from app.models.job import Job
from app.models.result import ResultType
from app.models.vulnerability import VulnerabilitySeverity
from app.tools.parsers import register_parser
from app.tools.parsers.base import (
    BaseParser,
    ParsedAsset,
    ParsedResult,
    ParsedVulnerability,
    ParseOutput,
)

logger = logging.getLogger(__name__)


class NmapParser(BaseParser):
    """Parser for Nmap XML output."""

    tool_name = "nmap"
    creates_assets = True
    creates_vulnerabilities = True

    # Script IDs that typically indicate vulnerabilities
    VULN_SCRIPTS = {
        "vulners",
        "vulscan",
        "http-vuln",
        "smb-vuln",
        "ssl-heartbleed",
        "ssl-poodle",
        "ssl-drown",
        "ssl-ccs-injection",
        "sslv2-drown",
        "ms-sql-empty-password",
        "mysql-empty-password",
        "ftp-anon",
        "http-shellshock",
        "smb-double-pulsar-backdoor",
        "smb-vuln-cve-2017-7494",
        "smb-vuln-ms06-025",
        "smb-vuln-ms07-029",
        "smb-vuln-ms08-067",
        "smb-vuln-ms10-054",
        "smb-vuln-ms10-061",
        "smb-vuln-ms17-010",
        "smtp-vuln-cve2010-4344",
        "smtp-vuln-cve2011-1720",
        "smtp-vuln-cve2011-1764",
    }

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse Nmap XML output."""
        result = ParseOutput()

        try:
            # Parse XML
            root = ET.fromstring(output)
        except ET.ParseError as e:
            result.errors.append(f"XML parse error: {e}")
            logger.error(f"Failed to parse Nmap XML: {e}")
            return result

        # Process each host
        for host in root.findall(".//host"):
            try:
                self._process_host(host, result)
            except Exception as e:
                result.errors.append(f"Error processing host: {e}")
                logger.exception(f"Error processing Nmap host: {e}")

        logger.info(
            f"Nmap parsing complete: {len(result.assets)} assets, "
            f"{len(result.vulnerabilities)} vulnerabilities, "
            f"{len(result.results)} results"
        )

        return result

    def _process_host(self, host: ET.Element, result: ParseOutput) -> None:
        """Process a single host element."""
        # Check if host is up
        status = host.find("status")
        if status is not None and status.get("state") != "up":
            return

        # Get IP address
        ip_addr = None
        hostnames = []

        for addr in host.findall("address"):
            if addr.get("addrtype") == "ipv4":
                ip_addr = addr.get("addr")
            elif addr.get("addrtype") == "ipv6":
                ip_addr = addr.get("addr")

        if not ip_addr:
            return

        # Get hostnames
        for hostname in host.findall(".//hostname"):
            name = hostname.get("name")
            if name:
                hostnames.append(name)

        # Create host asset
        host_metadata = {
            "ip": ip_addr,
            "hostnames": hostnames,
        }

        # Get OS detection info
        os_match = host.find(".//osmatch")
        if os_match is not None:
            host_metadata["os"] = os_match.get("name")
            host_metadata["os_accuracy"] = os_match.get("accuracy")

        result.assets.append(
            ParsedAsset(
                type=AssetType.HOST.value,
                value=ip_addr,
                metadata=host_metadata,
                tags=["nmap"],
            )
        )

        # Also create domain assets for hostnames
        for hostname in hostnames:
            result.assets.append(
                ParsedAsset(
                    type=AssetType.DOMAIN.value,
                    value=hostname,
                    metadata={"ip": ip_addr},
                    tags=["nmap"],
                )
            )

        # Process ports
        for port in host.findall(".//port"):
            self._process_port(port, ip_addr, result)

    def _process_port(
        self, port: ET.Element, ip_addr: str, result: ParseOutput
    ) -> None:
        """Process a single port element."""
        port_id = port.get("portid")
        protocol = port.get("protocol", "tcp")

        state_elem = port.find("state")
        if state_elem is None:
            return

        state = state_elem.get("state")
        if state != "open":
            return

        # Get service info
        service_elem = port.find("service")
        service_name = ""
        product = ""
        version = ""
        extra_info = ""

        if service_elem is not None:
            service_name = service_elem.get("name", "")
            product = service_elem.get("product", "")
            version = service_elem.get("version", "")
            extra_info = service_elem.get("extrainfo", "")

        # Create service asset
        service_value = f"{ip_addr}:{port_id}/{protocol}"
        service_metadata = {
            "ip": ip_addr,
            "port": int(port_id),
            "protocol": protocol,
            "state": state,
            "service": service_name,
            "product": product,
            "version": version,
            "extra_info": extra_info,
        }

        result.assets.append(
            ParsedAsset(
                type=AssetType.SERVICE.value,
                value=service_value,
                metadata=service_metadata,
                tags=["nmap", service_name] if service_name else ["nmap"],
            )
        )

        # Create port result
        result.results.append(
            ParsedResult(
                result_type=ResultType.PORT.value,
                parsed_data={
                    "port": int(port_id),
                    "protocol": protocol,
                    "state": state,
                    "service": service_name,
                    "product": product,
                    "version": version,
                },
                asset_value=ip_addr,
                asset_type=AssetType.HOST.value,
            )
        )

        # Create service result
        if service_name:
            result.results.append(
                ParsedResult(
                    result_type=ResultType.SERVICE.value,
                    parsed_data={
                        "name": service_name,
                        "product": product,
                        "version": version,
                        "port": int(port_id),
                        "protocol": protocol,
                    },
                    asset_value=ip_addr,
                    asset_type=AssetType.HOST.value,
                )
            )

        # Process scripts for vulnerabilities
        for script in port.findall("script"):
            self._process_script(script, ip_addr, int(port_id), protocol, result)

    def _process_script(
        self,
        script: ET.Element,
        ip_addr: str,
        port: int,
        protocol: str,
        result: ParseOutput,
    ) -> None:
        """Process a script element for potential vulnerabilities."""
        script_id = script.get("id", "")
        script_output = script.get("output", "")

        # Check if this is a vulnerability-related script
        is_vuln_script = any(
            vuln_pattern in script_id.lower() for vuln_pattern in self.VULN_SCRIPTS
        )

        if not is_vuln_script:
            # Still record as a result
            result.results.append(
                ParsedResult(
                    result_type=ResultType.RAW.value,
                    parsed_data={
                        "script_id": script_id,
                        "output": script_output,
                        "port": port,
                        "protocol": protocol,
                    },
                    raw_data=script_output,
                    asset_value=ip_addr,
                    asset_type=AssetType.HOST.value,
                )
            )
            return

        # Parse vulnerability scripts
        vulns = self._parse_vuln_script(script_id, script_output, script)

        for vuln in vulns:
            vuln.asset_value = ip_addr
            vuln.asset_type = AssetType.HOST.value
            vuln.metadata["port"] = port
            vuln.metadata["protocol"] = protocol
            result.vulnerabilities.append(vuln)

    def _parse_vuln_script(
        self, script_id: str, output: str, script: ET.Element
    ) -> List[ParsedVulnerability]:
        """Parse vulnerability information from script output."""
        vulns = []

        # Handle vulners script (CVE listing)
        if "vulners" in script_id.lower():
            vulns.extend(self._parse_vulners_output(output))

        # Handle specific SMB vulnerabilities
        elif "smb-vuln" in script_id.lower():
            vuln = self._parse_smb_vuln(script_id, output, script)
            if vuln:
                vulns.append(vuln)

        # Handle SSL/TLS vulnerabilities
        elif any(x in script_id.lower() for x in ["ssl-", "sslv2-"]):
            vuln = self._parse_ssl_vuln(script_id, output)
            if vuln:
                vulns.append(vuln)

        # Handle HTTP vulnerabilities
        elif "http-vuln" in script_id.lower():
            vuln = self._parse_http_vuln(script_id, output)
            if vuln:
                vulns.append(vuln)

        # Generic vulnerability script
        else:
            if "VULNERABLE" in output.upper():
                vulns.append(
                    ParsedVulnerability(
                        title=f"Nmap {script_id}",
                        severity=VulnerabilitySeverity.MEDIUM.value,
                        description=f"Vulnerability detected by Nmap script: {script_id}",
                        evidence=output[:2000],
                        template_id=f"nmap:{script_id}",
                        tags=["nmap", script_id],
                        metadata={"script_id": script_id},
                    )
                )

        return vulns

    def _parse_vulners_output(self, output: str) -> List[ParsedVulnerability]:
        """Parse vulners script output for CVEs."""
        vulns = []

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Look for CVE patterns
            if "CVE-" in line.upper():
                parts = line.split()
                for part in parts:
                    if part.upper().startswith("CVE-"):
                        cve_id = part.upper().rstrip(":")
                        # Try to extract CVSS score
                        cvss = None
                        for p in parts:
                            try:
                                score = float(p)
                                if 0 <= score <= 10:
                                    cvss = score
                                    break
                            except ValueError:
                                continue

                        severity = self._cvss_to_severity(cvss) if cvss else VulnerabilitySeverity.MEDIUM.value

                        vulns.append(
                            ParsedVulnerability(
                                title=f"{cve_id}",
                                severity=severity,
                                description=line,
                                cvss_score=cvss,
                                cve_ids=[cve_id],
                                template_id=f"nmap:vulners:{cve_id}",
                                references=[f"https://nvd.nist.gov/vuln/detail/{cve_id}"],
                                tags=["nmap", "vulners", cve_id],
                                metadata={"raw_line": line},
                            )
                        )
                        break

        return vulns

    def _parse_smb_vuln(
        self, script_id: str, output: str, script: ET.Element
    ) -> Optional[ParsedVulnerability]:
        """Parse SMB vulnerability script output."""
        if "NOT VULNERABLE" in output.upper():
            return None

        # Extract CVE from script ID if present
        cve_ids = []
        if "cve" in script_id.lower():
            import re
            match = re.search(r"cve[_-]?(\d{4})[_-]?(\d+)", script_id.lower())
            if match:
                cve_ids.append(f"CVE-{match.group(1)}-{match.group(2)}")

        # Determine severity based on script
        severity = VulnerabilitySeverity.HIGH.value
        if "ms17-010" in script_id.lower():
            severity = VulnerabilitySeverity.CRITICAL.value
            cve_ids = ["CVE-2017-0143", "CVE-2017-0144", "CVE-2017-0145"]

        return ParsedVulnerability(
            title=f"SMB Vulnerability: {script_id}",
            severity=severity,
            description=f"SMB vulnerability detected: {script_id}",
            evidence=output[:2000],
            cve_ids=cve_ids,
            template_id=f"nmap:{script_id}",
            tags=["nmap", "smb", script_id],
            metadata={"script_id": script_id},
        )

    def _parse_ssl_vuln(
        self, script_id: str, output: str
    ) -> Optional[ParsedVulnerability]:
        """Parse SSL/TLS vulnerability script output."""
        if "NOT VULNERABLE" in output.upper():
            return None

        vuln_info = {
            "ssl-heartbleed": {
                "title": "OpenSSL Heartbleed Vulnerability",
                "severity": VulnerabilitySeverity.CRITICAL.value,
                "cve_ids": ["CVE-2014-0160"],
            },
            "ssl-poodle": {
                "title": "SSL POODLE Vulnerability",
                "severity": VulnerabilitySeverity.MEDIUM.value,
                "cve_ids": ["CVE-2014-3566"],
            },
            "ssl-drown": {
                "title": "DROWN Attack Vulnerability",
                "severity": VulnerabilitySeverity.HIGH.value,
                "cve_ids": ["CVE-2016-0800"],
            },
            "ssl-ccs-injection": {
                "title": "OpenSSL CCS Injection Vulnerability",
                "severity": VulnerabilitySeverity.MEDIUM.value,
                "cve_ids": ["CVE-2014-0224"],
            },
        }

        info = vuln_info.get(script_id.lower(), {
            "title": f"SSL/TLS Vulnerability: {script_id}",
            "severity": VulnerabilitySeverity.MEDIUM.value,
            "cve_ids": [],
        })

        return ParsedVulnerability(
            title=info["title"],
            severity=info["severity"],
            description="SSL/TLS vulnerability detected by Nmap",
            evidence=output[:2000],
            cve_ids=info["cve_ids"],
            template_id=f"nmap:{script_id}",
            tags=["nmap", "ssl", "tls", script_id],
            metadata={"script_id": script_id},
        )

    def _parse_http_vuln(
        self, script_id: str, output: str
    ) -> Optional[ParsedVulnerability]:
        """Parse HTTP vulnerability script output."""
        if "NOT VULNERABLE" in output.upper():
            return None

        return ParsedVulnerability(
            title=f"HTTP Vulnerability: {script_id}",
            severity=VulnerabilitySeverity.HIGH.value,
            description=f"HTTP vulnerability detected: {script_id}",
            evidence=output[:2000],
            template_id=f"nmap:{script_id}",
            tags=["nmap", "http", script_id],
            metadata={"script_id": script_id},
        )

    def _cvss_to_severity(self, cvss: float) -> str:
        """Convert CVSS score to severity level."""
        if cvss >= 9.0:
            return VulnerabilitySeverity.CRITICAL.value
        elif cvss >= 7.0:
            return VulnerabilitySeverity.HIGH.value
        elif cvss >= 4.0:
            return VulnerabilitySeverity.MEDIUM.value
        elif cvss > 0:
            return VulnerabilitySeverity.LOW.value
        else:
            return VulnerabilitySeverity.INFO.value


# Register the parser
register_parser("nmap_parser", NmapParser)
