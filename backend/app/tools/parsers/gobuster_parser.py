"""Gobuster text output parser."""

import logging
import re
from urllib.parse import urljoin

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


class GobusterParser(BaseParser):
    """Parser for Gobuster text output."""

    tool_name = "gobuster"
    creates_assets = True

    # Pattern to match gobuster output lines
    # Examples:
    # /admin                (Status: 200) [Size: 1234]
    # /images               (Status: 301) [Size: 456] [--> /images/]
    LINE_PATTERN = re.compile(
        r"^(/\S*)\s+\(Status:\s*(\d+)\)\s*\[Size:\s*(\d+)\](?:\s*\[--> ([^\]]+)\])?"
    )

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse Gobuster text output."""
        result = ParseOutput()
        seen_paths = set()

        # Try to extract base URL from job parameters
        base_url = self._get_base_url(job)

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            match = self.LINE_PATTERN.match(line)
            if match:
                path = match.group(1)
                status = int(match.group(2))
                size = int(match.group(3))
                redirect = match.group(4)

                if path not in seen_paths:
                    seen_paths.add(path)
                    self._add_directory(
                        path, status, size, redirect, base_url, result
                    )

        logger.info(
            f"Gobuster parsing complete: {len(result.assets)} assets, "
            f"{len(result.results)} results"
        )
        return result

    def _get_base_url(self, job: Job) -> str:
        """Extract base URL from job parameters."""
        params = job.parameters if isinstance(job.parameters, dict) else {}
        return params.get("url", "")

    def _add_directory(
        self,
        path: str,
        status: int,
        size: int,
        redirect: str,
        base_url: str,
        result: ParseOutput,
    ) -> None:
        """Add a discovered directory/file to results."""
        # Determine if it's a file or directory
        is_file = "." in path.split("/")[-1]
        result_type = ResultType.FILE.value if is_file else ResultType.DIRECTORY.value
        asset_type = AssetType.ENDPOINT.value

        # Build full URL if base URL is available
        full_url = urljoin(base_url, path) if base_url else path

        metadata = {
            "path": path,
            "status_code": status,
            "size": size,
        }
        if redirect:
            metadata["redirect"] = redirect

        # Create asset
        result.assets.append(
            ParsedAsset(
                type=asset_type,
                value=full_url,
                metadata=metadata,
                tags=["gobuster", f"status-{status}"],
            )
        )

        # Create result
        result.results.append(
            ParsedResult(
                result_type=result_type,
                parsed_data={
                    "path": path,
                    "full_url": full_url,
                    "status_code": status,
                    "size": size,
                    "redirect": redirect,
                },
                asset_value=base_url if base_url else path,
                asset_type=AssetType.URL.value if base_url else None,
            )
        )


# Register the parser
register_parser("gobuster_parser", GobusterParser)
