"""Amass JSON output parser."""

import json
import logging
from typing import Optional

from app.models.asset import AssetType
from app.models.job import Job
from app.tools.parsers import register_parser
from app.tools.parsers.base import (
    BaseParser,
    ParsedAsset,
    ParseOutput,
)

logger = logging.getLogger(__name__)


class AmassParser(BaseParser):
    """Parser for Amass JSON output."""

    tool_name = "amass"
    creates_assets = True
    creates_vulnerabilities = False
    creates_credentials = False

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse Amass JSON output (one JSON object per line)."""
        result = ParseOutput()
        seen_domains = set()
        seen_ips = set()

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            try:
                finding = json.loads(line)
                self._process_finding(finding, result, seen_domains, seen_ips)
            except json.JSONDecodeError as e:
                # Skip non-JSON lines (status messages, etc.)
                if line.startswith("{"):
                    result.errors.append(f"JSON parse error: {e}")
                continue
            except Exception as e:
                result.errors.append(f"Error processing finding: {e}")
                logger.exception(f"Error processing Amass finding: {e}")

        logger.info(
            f"Amass parsing complete: {len(result.assets)} assets discovered"
        )

        return result

    def _process_finding(
        self,
        finding: dict,
        result: ParseOutput,
        seen_domains: set,
        seen_ips: set,
    ) -> None:
        """Process a single Amass finding."""
        # Get the name (subdomain/domain)
        name = finding.get("name", "")
        domain = finding.get("domain", "")

        if not name:
            return

        # Create domain/subdomain asset
        if name and name not in seen_domains:
            seen_domains.add(name)

            # Determine if it's a subdomain or root domain
            is_subdomain = name != domain and domain and name.endswith(f".{domain}")

            result.assets.append(
                ParsedAsset(
                    type=AssetType.DOMAIN.value,
                    value=name,
                    metadata={
                        "root_domain": domain,
                        "is_subdomain": is_subdomain,
                        "source": finding.get("source", ""),
                        "tag": finding.get("tag", ""),
                    },
                    tags=["amass", "subdomain" if is_subdomain else "root-domain"],
                )
            )

        # Process addresses (IP addresses)
        addresses = finding.get("addresses", [])
        for addr in addresses:
            ip = addr.get("ip", "")
            if ip and ip not in seen_ips:
                seen_ips.add(ip)
                result.assets.append(
                    ParsedAsset(
                        type=AssetType.HOST.value,
                        value=ip,
                        metadata={
                            "cidr": addr.get("cidr", ""),
                            "asn": addr.get("asn", 0),
                            "desc": addr.get("desc", ""),
                            "associated_domain": name,
                        },
                        tags=["amass", "discovered-ip"],
                    )
                )


# Register the parser
register_parser("amass_parser", AmassParser)
