"""Subfinder JSON output parser."""

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


class SubfinderParser(BaseParser):
    """Parser for Subfinder JSON output."""

    tool_name = "subfinder"
    creates_assets = True

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse Subfinder JSON output (one JSON object per line)."""
        result = ParseOutput()
        seen_subdomains = set()

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                self._process_subdomain(data, result, seen_subdomains)
            except json.JSONDecodeError:
                # Try plain text format (one subdomain per line)
                if "." in line and not line.startswith("{"):
                    self._add_subdomain(line, "", result, seen_subdomains)
            except Exception as e:
                result.errors.append(f"Error processing line: {e}")

        logger.info(f"Subfinder parsing complete: {len(result.assets)} subdomains")
        return result

    def _process_subdomain(
        self, data: dict, result: ParseOutput, seen: set
    ) -> None:
        """Process a single subfinder JSON result."""
        # Handle different JSON formats
        subdomain = data.get("host", data.get("subdomain", data.get("domain", "")))
        source = data.get("source", data.get("sources", ""))

        if isinstance(source, list):
            source = ",".join(source)

        if subdomain:
            self._add_subdomain(subdomain, source, result, seen)

    def _add_subdomain(
        self, subdomain: str, source: str, result: ParseOutput, seen: set
    ) -> None:
        """Add a subdomain to the results."""
        subdomain = subdomain.strip().lower()

        if subdomain in seen or not subdomain:
            return

        seen.add(subdomain)

        # Create subdomain asset
        result.assets.append(
            ParsedAsset(
                type=AssetType.SUBDOMAIN.value,
                value=subdomain,
                metadata={"source": source} if source else {},
                tags=["subfinder"],
            )
        )

        # Create result record
        result.results.append(
            ParsedResult(
                result_type=ResultType.SUBDOMAIN.value,
                parsed_data={
                    "subdomain": subdomain,
                    "source": source,
                },
            )
        )


# Register the parser
register_parser("subfinder_parser", SubfinderParser)
