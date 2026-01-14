"""Nuclei JSON output parser."""

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
    ParseOutput,
)

logger = logging.getLogger(__name__)


class NucleiParser(BaseParser):
    """Parser for Nuclei JSON output (JSONL format)."""

    tool_name = "nuclei"
    creates_assets = True
    creates_vulnerabilities = True

    # Map Nuclei severity to our severity levels
    SEVERITY_MAP = {
        "info": VulnerabilitySeverity.INFO.value,
        "low": VulnerabilitySeverity.LOW.value,
        "medium": VulnerabilitySeverity.MEDIUM.value,
        "high": VulnerabilitySeverity.HIGH.value,
        "critical": VulnerabilitySeverity.CRITICAL.value,
        "unknown": VulnerabilitySeverity.INFO.value,
    }

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse Nuclei JSON output (one JSON object per line)."""
        result = ParseOutput()
        seen_hosts = set()

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            try:
                finding = json.loads(line)
                self._process_finding(finding, result, seen_hosts)
            except json.JSONDecodeError as e:
                # Skip non-JSON lines (status messages, etc.)
                if line.startswith("{"):
                    result.errors.append(f"JSON parse error: {e}")
                continue
            except Exception as e:
                result.errors.append(f"Error processing finding: {e}")
                logger.exception(f"Error processing Nuclei finding: {e}")

        logger.info(
            f"Nuclei parsing complete: {len(result.assets)} assets, "
            f"{len(result.vulnerabilities)} vulnerabilities"
        )

        return result

    def _process_finding(
        self, finding: dict, result: ParseOutput, seen_hosts: set
    ) -> None:
        """Process a single Nuclei finding."""
        # Get template info
        template_id = finding.get("template-id", finding.get("templateID", ""))
        info = finding.get("info", {})

        # Get target info
        host = finding.get("host", "")
        matched_at = finding.get("matched-at", finding.get("matched", ""))
        target_url = matched_at or host

        if not target_url:
            return

        # Create URL asset if we haven't seen this host
        if host and host not in seen_hosts:
            seen_hosts.add(host)
            self._create_url_asset(host, result)

        # Get severity
        severity = info.get("severity", "info").lower()
        severity = self.SEVERITY_MAP.get(severity, VulnerabilitySeverity.INFO.value)

        # Get name and description
        name = info.get("name", template_id)
        description = info.get("description", "")

        # Get references
        references = info.get("reference", [])
        if isinstance(references, str):
            references = [references] if references else []

        # Get CVE IDs from classification
        classification = info.get("classification", {})
        cve_ids = classification.get("cve-id", [])
        if isinstance(cve_ids, str):
            cve_ids = [cve_ids] if cve_ids else []

        cwe_ids = classification.get("cwe-id", [])
        if isinstance(cwe_ids, str):
            cwe_ids = [cwe_ids] if cwe_ids else []

        # Get CVSS score
        cvss_score = None
        cvss_metrics = classification.get("cvss-metrics", "")
        cvss_score_str = classification.get("cvss-score")
        if cvss_score_str:
            try:
                cvss_score = float(cvss_score_str)
            except (ValueError, TypeError):
                pass

        # Get tags
        tags = info.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]

        # Get request/response if available
        request = finding.get("request", "")
        response = finding.get("response", "")

        # Truncate large responses
        if len(response) > 5000:
            response = response[:5000] + "\n... [truncated]"

        # Get extracted results as evidence
        extracted = finding.get("extracted-results", [])
        evidence = ""
        if extracted:
            if isinstance(extracted, list):
                evidence = "\n".join(str(e) for e in extracted)
            else:
                evidence = str(extracted)

        # Also include matcher info in evidence
        matcher_name = finding.get("matcher-name", "")
        if matcher_name:
            evidence = f"Matcher: {matcher_name}\n{evidence}".strip()

        # Get remediation
        remediation = info.get("remediation", "")

        # Create vulnerability
        result.vulnerabilities.append(
            ParsedVulnerability(
                title=name,
                severity=severity,
                description=description,
                cvss_score=cvss_score,
                cvss_vector=cvss_metrics if cvss_metrics else None,
                cve_ids=cve_ids,
                cwe_ids=cwe_ids,
                evidence=evidence if evidence else None,
                remediation=remediation if remediation else None,
                references=references,
                template_id=template_id,
                request=request[:5000] if request else None,
                response=response if response else None,
                tags=["nuclei"] + tags,
                metadata={
                    "template_id": template_id,
                    "matched_at": matched_at,
                    "host": host,
                    "type": finding.get("type", ""),
                    "matcher_name": matcher_name,
                },
                asset_value=host,
                asset_type=AssetType.URL.value,
            )
        )

    def _create_url_asset(self, url: str, result: ParseOutput) -> None:
        """Create a URL asset from the target."""
        try:
            parsed = urlparse(url)

            # Create URL asset
            result.assets.append(
                ParsedAsset(
                    type=AssetType.URL.value,
                    value=url,
                    metadata={
                        "scheme": parsed.scheme,
                        "netloc": parsed.netloc,
                        "path": parsed.path,
                    },
                    tags=["nuclei"],
                )
            )

            # Also create domain asset if applicable
            if parsed.netloc:
                # Remove port if present
                host = parsed.netloc.split(":")[0]
                if host and not self._is_ip(host):
                    result.assets.append(
                        ParsedAsset(
                            type=AssetType.DOMAIN.value,
                            value=host,
                            metadata={"source_url": url},
                            tags=["nuclei"],
                        )
                    )
        except Exception as e:
            logger.warning(f"Failed to parse URL {url}: {e}")

    def _is_ip(self, host: str) -> bool:
        """Check if host is an IP address."""
        import re
        ipv4_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        return bool(re.match(ipv4_pattern, host))


# Register the parser
register_parser("nuclei_parser", NucleiParser)
