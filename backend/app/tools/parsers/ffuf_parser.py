"""FFUF JSON output parser."""

import json
import logging
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


class FfufParser(BaseParser):
    """Parser for FFUF JSON output."""

    tool_name = "ffuf"
    creates_assets = True

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse FFUF JSON output."""
        result = ParseOutput()

        try:
            # FFUF outputs a single JSON object
            data = json.loads(output)
            self._process_results(data, result, job)
        except json.JSONDecodeError as e:
            result.errors.append(f"JSON parse error: {e}")
            logger.error(f"Failed to parse FFUF JSON: {e}")

        logger.info(
            f"FFUF parsing complete: {len(result.assets)} assets, "
            f"{len(result.results)} results"
        )
        return result

    def _process_results(
        self, data: dict, result: ParseOutput, job: Job
    ) -> None:
        """Process FFUF results."""
        # Get configuration info
        config = data.get("config", {})
        base_url = config.get("url", "")

        # Get the FUZZ keyword position
        commandline = data.get("commandline", "")

        # Process results
        results = data.get("results", [])
        seen_urls = set()

        for item in results:
            try:
                self._process_item(item, base_url, result, seen_urls)
            except Exception as e:
                result.errors.append(f"Error processing item: {e}")

    def _process_item(
        self, item: dict, base_url: str, result: ParseOutput, seen_urls: set
    ) -> None:
        """Process a single FFUF result item."""
        # Get item details
        input_value = item.get("input", {})
        fuzz_word = input_value.get("FUZZ", "")

        status = item.get("status", 0)
        length = item.get("length", 0)
        words = item.get("words", 0)
        lines = item.get("lines", 0)
        content_type = item.get("content-type", "")
        redirect_location = item.get("redirectlocation", "")
        url = item.get("url", "")

        if not url:
            # Reconstruct URL from base and fuzz word
            url = base_url.replace("FUZZ", fuzz_word) if base_url else fuzz_word

        if url in seen_urls:
            return
        seen_urls.add(url)

        # Determine if it's likely a file or directory
        is_file = "." in fuzz_word or "." in url.split("/")[-1]
        result_type = ResultType.FILE.value if is_file else ResultType.DIRECTORY.value

        metadata = {
            "fuzz_word": fuzz_word,
            "status_code": status,
            "length": length,
            "words": words,
            "lines": lines,
            "content_type": content_type,
        }
        if redirect_location:
            metadata["redirect"] = redirect_location

        # Create asset
        result.assets.append(
            ParsedAsset(
                type=AssetType.ENDPOINT.value,
                value=url,
                metadata=metadata,
                tags=["ffuf", f"status-{status}"],
            )
        )

        # Create result
        result.results.append(
            ParsedResult(
                result_type=result_type,
                parsed_data={
                    "url": url,
                    "fuzz_word": fuzz_word,
                    "status_code": status,
                    "length": length,
                    "words": words,
                    "lines": lines,
                    "content_type": content_type,
                    "redirect": redirect_location,
                },
                asset_value=url,
                asset_type=AssetType.ENDPOINT.value,
            )
        )


# Register the parser
register_parser("ffuf_parser", FfufParser)
