"""Masscan JSON output parser."""

import json
import logging

from app.models.asset import AssetType
from app.models.job import Job
from app.models.result import ResultType
from app.tools.parsers import register_parser
from app.tools.parsers.base import (
    BaseParser,
    ParsedAsset,
    ParsedResult,
    ParseOutput,
)

logger = logging.getLogger(__name__)


class MasscanParser(BaseParser):
    """Parser for Masscan JSON output."""

    tool_name = "masscan"
    creates_assets = True

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse Masscan JSON output."""
        result = ParseOutput()
        seen_hosts = set()

        try:
            # Masscan outputs a JSON array
            # Clean up the output - remove trailing commas, etc.
            output = output.strip()
            if output.endswith(","):
                output = output[:-1]
            if not output.startswith("["):
                output = "[" + output
            if not output.endswith("]"):
                output = output + "]"

            data = json.loads(output)

            for entry in data:
                self._process_entry(entry, result, seen_hosts)

        except json.JSONDecodeError as e:
            result.errors.append(f"JSON parse error: {e}")
            logger.error(f"Failed to parse Masscan JSON: {e}")
            # Try line-by-line parsing as fallback
            self._parse_line_by_line(output, result, seen_hosts)

        logger.info(
            f"Masscan parsing complete: {len(result.assets)} assets, "
            f"{len(result.results)} results"
        )
        return result

    def _parse_line_by_line(
        self, output: str, result: ParseOutput, seen_hosts: set
    ) -> None:
        """Fallback parser for line-by-line JSON."""
        for line in output.split("\n"):
            line = line.strip().rstrip(",")
            if not line or line in ["[", "]"]:
                continue
            try:
                entry = json.loads(line)
                self._process_entry(entry, result, seen_hosts)
            except json.JSONDecodeError:
                continue

    def _process_entry(
        self, entry: dict, result: ParseOutput, seen_hosts: set
    ) -> None:
        """Process a single Masscan result entry."""
        ip = entry.get("ip", "")
        if not ip:
            return

        # Create host asset if not seen
        if ip not in seen_hosts:
            seen_hosts.add(ip)
            result.assets.append(
                ParsedAsset(
                    type=AssetType.HOST.value,
                    value=ip,
                    metadata={},
                    tags=["masscan"],
                )
            )

        # Process ports
        ports = entry.get("ports", [])
        for port_info in ports:
            port = port_info.get("port")
            protocol = port_info.get("proto", "tcp")
            status = port_info.get("status", "open")
            reason = port_info.get("reason", "")
            ttl = port_info.get("ttl", 0)

            if not port or status != "open":
                continue

            # Create service asset
            service_value = f"{ip}:{port}/{protocol}"
            result.assets.append(
                ParsedAsset(
                    type=AssetType.SERVICE.value,
                    value=service_value,
                    metadata={
                        "ip": ip,
                        "port": port,
                        "protocol": protocol,
                        "status": status,
                        "reason": reason,
                        "ttl": ttl,
                    },
                    tags=["masscan"],
                )
            )

            # Create port result
            result.results.append(
                ParsedResult(
                    result_type=ResultType.PORT.value,
                    parsed_data={
                        "ip": ip,
                        "port": port,
                        "protocol": protocol,
                        "status": status,
                        "reason": reason,
                        "ttl": ttl,
                    },
                    asset_value=ip,
                    asset_type=AssetType.HOST.value,
                )
            )


# Register the parser
register_parser("masscan_parser", MasscanParser)
