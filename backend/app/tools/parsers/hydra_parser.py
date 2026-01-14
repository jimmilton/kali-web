"""Hydra text output parser."""

import logging
import re

from app.models.asset import AssetType
from app.models.job import Job
from app.tools.parsers import register_parser
from app.tools.parsers.base import (
    BaseParser,
    ParsedAsset,
    ParsedCredential,
    ParseOutput,
)

logger = logging.getLogger(__name__)


class HydraParser(BaseParser):
    """Parser for Hydra text output."""

    tool_name = "hydra"
    creates_assets = True
    creates_credentials = True

    # Pattern to match successful login lines
    # Examples:
    # [22][ssh] host: 192.168.1.1   login: admin   password: password123
    # [80][http-get] host: example.com   login: user   password: pass
    # [3306][mysql] host: 192.168.1.1   login: root   password: root123
    SUCCESS_PATTERN = re.compile(
        r"\[(\d+)\]\[([^\]]+)\]\s+host:\s*(\S+)\s+login:\s*(\S+)\s+password:\s*(.+)$",
        re.IGNORECASE
    )

    # Alternative pattern for newer hydra versions
    ALT_PATTERN = re.compile(
        r"\[(\d+)\]\[([^\]]+)\]\s+host:\s*(\S+)\s+login:\s*(\S*)\s+password:\s*(.*)$",
        re.IGNORECASE
    )

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse Hydra text output."""
        result = ParseOutput()
        seen_creds = set()

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Try to match success pattern
            match = self.SUCCESS_PATTERN.match(line)
            if not match:
                match = self.ALT_PATTERN.match(line)

            if match:
                self._process_match(match, result, seen_creds, job)

        logger.info(
            f"Hydra parsing complete: {len(result.assets)} assets, "
            f"{len(result.credentials)} credentials"
        )
        return result

    def _process_match(
        self,
        match: re.Match,
        result: ParseOutput,
        seen_creds: set,
        job: Job,
    ) -> None:
        """Process a successful credential match."""
        port = int(match.group(1))
        service = match.group(2).strip()
        host = match.group(3).strip()
        username = match.group(4).strip()
        password = match.group(5).strip()

        # Create unique key for deduplication
        cred_key = f"{host}:{port}:{username}:{password}"
        if cred_key in seen_creds:
            return
        seen_creds.add(cred_key)

        # Create host asset
        result.assets.append(
            ParsedAsset(
                type=AssetType.HOST.value if self._is_ip(host) else AssetType.DOMAIN.value,
                value=host,
                metadata={
                    "port": port,
                    "service": service,
                },
                tags=["hydra", service],
                risk_score=80,  # High risk - credential found
            )
        )

        # Create service asset
        service_value = f"{host}:{port}/{service}"
        result.assets.append(
            ParsedAsset(
                type=AssetType.SERVICE.value,
                value=service_value,
                metadata={
                    "host": host,
                    "port": port,
                    "service": service,
                    "credential_found": True,
                },
                tags=["hydra", "credential-found"],
                risk_score=90,  # Very high risk
            )
        )

        # Create credential
        result.credentials.append(
            ParsedCredential(
                username=username,
                password=password,
                service=service,
                port=port,
                credential_type="password",
                metadata={
                    "source": "hydra",
                    "host": host,
                },
                asset_value=host,
                asset_type=AssetType.HOST.value if self._is_ip(host) else AssetType.DOMAIN.value,
            )
        )

    def _is_ip(self, host: str) -> bool:
        """Check if host is an IP address."""
        ipv4_pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        return bool(re.match(ipv4_pattern, host))


# Register the parser
register_parser("hydra_parser", HydraParser)
