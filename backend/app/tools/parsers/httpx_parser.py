"""HTTPx JSON output parser."""

import json
import logging
from urllib.parse import urlparse

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


class HttpxParser(BaseParser):
    """Parser for HTTPx JSON output."""

    tool_name = "httpx"
    creates_assets = True

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse HTTPx JSON output (one JSON object per line)."""
        result = ParseOutput()
        seen_urls = set()

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                self._process_result(data, result, seen_urls)
            except json.JSONDecodeError:
                # Skip non-JSON lines
                if line.startswith("{"):
                    result.errors.append(f"JSON parse error for line")
            except Exception as e:
                result.errors.append(f"Error processing result: {e}")

        logger.info(
            f"HTTPx parsing complete: {len(result.assets)} assets, "
            f"{len(result.results)} results"
        )
        return result

    def _process_result(
        self, data: dict, result: ParseOutput, seen_urls: set
    ) -> None:
        """Process a single HTTPx result."""
        url = data.get("url", data.get("input", ""))
        if not url or url in seen_urls:
            return

        seen_urls.add(url)

        # Parse URL for asset creation
        try:
            parsed = urlparse(url)
            host = parsed.netloc.split(":")[0]
        except Exception:
            host = ""

        # Extract common fields
        status_code = data.get("status_code", data.get("status-code"))
        title = data.get("title", "")
        content_length = data.get("content_length", data.get("content-length"))
        content_type = data.get("content_type", data.get("content-type", ""))
        web_server = data.get("webserver", data.get("server", ""))
        technologies = data.get("tech", data.get("technologies", []))
        final_url = data.get("final_url", data.get("final-url", url))

        # Handle technologies
        if isinstance(technologies, str):
            technologies = [t.strip() for t in technologies.split(",") if t.strip()]

        # Create URL asset
        metadata = {
            "status_code": status_code,
            "title": title,
            "content_type": content_type,
            "content_length": content_length,
            "web_server": web_server,
            "technologies": technologies,
        }
        # Remove None values
        metadata = {k: v for k, v in metadata.items() if v is not None}

        result.assets.append(
            ParsedAsset(
                type=AssetType.URL.value,
                value=url,
                metadata=metadata,
                tags=["httpx"] + technologies[:5],  # Limit tags
            )
        )

        # Create endpoint result
        result.results.append(
            ParsedResult(
                result_type=ResultType.ENDPOINT.value,
                parsed_data={
                    "url": url,
                    "final_url": final_url,
                    "status_code": status_code,
                    "title": title,
                    "content_type": content_type,
                    "content_length": content_length,
                    "web_server": web_server,
                },
                asset_value=url,
                asset_type=AssetType.URL.value,
            )
        )

        # Create technology results
        for tech in technologies:
            # Also create technology asset
            result.assets.append(
                ParsedAsset(
                    type=AssetType.TECHNOLOGY.value,
                    value=tech,
                    metadata={"source_url": url},
                    tags=["httpx"],
                )
            )

            result.results.append(
                ParsedResult(
                    result_type=ResultType.TECHNOLOGY.value,
                    parsed_data={
                        "name": tech,
                        "url": url,
                    },
                    asset_value=url,
                    asset_type=AssetType.URL.value,
                )
            )

        # Create domain asset if applicable
        if host and not self._is_ip(host):
            result.assets.append(
                ParsedAsset(
                    type=AssetType.DOMAIN.value,
                    value=host,
                    metadata={"source_url": url},
                    tags=["httpx"],
                )
            )

    def _is_ip(self, host: str) -> bool:
        """Check if host is an IP address."""
        import re
        ipv4_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        return bool(re.match(ipv4_pattern, host))


# Register the parser
register_parser("httpx_parser", HttpxParser)
