"""Hashcat output parser."""

import json
import logging
import re
from typing import Optional

from app.models.asset import AssetType
from app.models.job import Job
from app.tools.parsers import register_parser
from app.tools.parsers.base import (
    BaseParser,
    ParsedCredential,
    ParseOutput,
)

logger = logging.getLogger(__name__)


class HashcatParser(BaseParser):
    """Parser for Hashcat output (potfile format and status output)."""

    tool_name = "hashcat"
    creates_assets = False
    creates_vulnerabilities = False
    creates_credentials = True

    # Common hash type mappings
    HASH_TYPES = {
        "0": "MD5",
        "100": "SHA1",
        "1400": "SHA256",
        "1700": "SHA512",
        "1000": "NTLM",
        "3000": "LM",
        "1800": "SHA512crypt",
        "500": "MD5crypt",
        "1500": "DES",
        "5500": "NetNTLMv1",
        "5600": "NetNTLMv2",
        "13100": "Kerberos 5 TGS-REP",
        "18200": "Kerberos 5 AS-REP",
        "7500": "Kerberos 5 AS-REQ",
        "22000": "WPA-PBKDF2-PMKID+EAPOL",
        "2500": "WPA-EAPOL-PBKDF2",
        "11600": "7-Zip",
        "13400": "KeePass",
        "16800": "WPA-PMKID-PBKDF2",
        "3200": "bcrypt",
    }

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse Hashcat output."""
        result = ParseOutput()

        # Try to parse JSON output first (--status-json)
        if self._try_parse_json(output, result):
            logger.info(f"Hashcat parsing (JSON): {len(result.credentials)} credentials cracked")
            return result

        # Parse potfile format (hash:password)
        self._parse_potfile_format(output, result, job)

        # Parse show output format
        self._parse_show_format(output, result, job)

        logger.info(f"Hashcat parsing complete: {len(result.credentials)} credentials cracked")

        return result

    def _try_parse_json(self, output: str, result: ParseOutput) -> bool:
        """Try to parse JSON status output."""
        try:
            for line in output.split("\n"):
                line = line.strip()
                if not line or not line.startswith("{"):
                    continue

                data = json.loads(line)

                # Check for recovered hashes in JSON status
                if "recovered" in data:
                    recovered = data.get("recovered", [])
                    if isinstance(recovered, list) and len(recovered) >= 2:
                        cracked_count = recovered[0]
                        if cracked_count > 0:
                            # JSON status doesn't include actual passwords
                            # Just log the count
                            logger.info(f"Hashcat recovered {cracked_count} hashes")

            return False  # Continue with text parsing
        except json.JSONDecodeError:
            return False

    def _parse_potfile_format(self, output: str, result: ParseOutput, job: Job) -> None:
        """Parse hashcat potfile format (hash:password)."""
        # Match common hash formats followed by :password
        # Handles various hash formats including $hash$, hex hashes, etc.

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Skip status lines and other non-result lines
            if any(skip in line.lower() for skip in [
                "session", "status", "speed", "progress", "time",
                "recovered", "hashtype", "candidates", "hardware"
            ]):
                continue

            # Try to extract hash:password pairs
            credential = self._extract_credential(line, job)
            if credential:
                result.credentials.append(credential)

    def _parse_show_format(self, output: str, result: ParseOutput, job: Job) -> None:
        """Parse hashcat --show output format."""
        # --show format can be:
        # hash:password
        # username:hash:password (with --username)

        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Skip already processed or non-data lines
            if ":" not in line:
                continue

            parts = line.split(":")

            # Check if this looks like a cracked result
            if len(parts) >= 2:
                credential = self._extract_credential(line, job)
                if credential and not self._credential_exists(credential, result):
                    result.credentials.append(credential)

    def _extract_credential(self, line: str, job: Job) -> Optional[ParsedCredential]:
        """Extract credential from a hashcat output line."""
        # Common patterns:
        # 1. hash:password
        # 2. username:hash:password (with --username flag)
        # 3. user@domain:hash:password

        parts = line.split(":")

        if len(parts) < 2:
            return None

        username = None
        hash_value = None
        password = None
        hash_type = None
        domain = None

        # Detect hash type from job parameters if available
        if job.parameters:
            mode = job.parameters.get("mode") or job.parameters.get("hash_type")
            if mode:
                hash_type = self.HASH_TYPES.get(str(mode), f"Mode {mode}")

        # Try to identify the format
        if len(parts) == 2:
            # Simple hash:password format
            hash_value = parts[0]
            password = parts[1]
        elif len(parts) == 3:
            # Could be username:hash:password or hash_with_colon:password
            # Check if first part looks like a username
            if self._looks_like_username(parts[0]) and not self._looks_like_hash(parts[0]):
                username = parts[0]
                hash_value = parts[1]
                password = parts[2]
            else:
                # Assume hash contains a colon (e.g., MD5(Unix) format)
                hash_value = f"{parts[0]}:{parts[1]}"
                password = parts[2]
        elif len(parts) >= 4:
            # Complex format - username:hash_parts:password
            if self._looks_like_username(parts[0]):
                username = parts[0]
                password = parts[-1]
                hash_value = ":".join(parts[1:-1])
            else:
                password = parts[-1]
                hash_value = ":".join(parts[:-1])

        # Extract domain from username if present
        if username and "@" in username:
            username, domain = username.split("@", 1)
        elif username and "\\" in username:
            domain, username = username.split("\\", 1)

        # Validate we have at least a password
        if not password or len(password) == 0:
            return None

        # Skip if password looks like it's part of a hash (hex-only, specific patterns)
        if self._looks_like_hash(password):
            return None

        # Detect hash type from hash value if not already set
        if not hash_type:
            hash_type = self._detect_hash_type(hash_value)

        return ParsedCredential(
            username=username,
            password=password,
            hash_value=hash_value,
            hash_type=hash_type,
            domain=domain,
            credential_type="password",
            metadata={
                "source": "hashcat",
                "raw_line": line[:500],  # Store original for reference
            },
        )

    def _looks_like_username(self, s: str) -> bool:
        """Check if string looks like a username."""
        if not s:
            return False
        # Usernames typically:
        # - Don't start with $ (hash indicator)
        # - Aren't all hex
        # - Are relatively short
        # - May contain letters, numbers, underscores, @, .
        if s.startswith("$"):
            return False
        if len(s) > 64:
            return False
        if re.match(r"^[a-fA-F0-9]{32,}$", s):  # Pure hex, likely hash
            return False
        return bool(re.match(r"^[\w\-@.\\]+$", s))

    def _looks_like_hash(self, s: str) -> bool:
        """Check if string looks like a hash."""
        if not s:
            return False
        # Common hash patterns
        patterns = [
            r"^\$[a-z0-9]+\$",  # $type$ format (MD5crypt, bcrypt, etc.)
            r"^[a-fA-F0-9]{32}$",  # MD5
            r"^[a-fA-F0-9]{40}$",  # SHA1
            r"^[a-fA-F0-9]{64}$",  # SHA256
            r"^[a-fA-F0-9]{128}$",  # SHA512
        ]
        for pattern in patterns:
            if re.match(pattern, s):
                return True
        return False

    def _detect_hash_type(self, hash_value: str) -> Optional[str]:
        """Try to detect hash type from hash value."""
        if not hash_value:
            return None

        if hash_value.startswith("$1$"):
            return "MD5crypt"
        elif hash_value.startswith("$2"):
            return "bcrypt"
        elif hash_value.startswith("$5$"):
            return "SHA256crypt"
        elif hash_value.startswith("$6$"):
            return "SHA512crypt"
        elif hash_value.startswith("$apr1$"):
            return "Apache MD5"
        elif len(hash_value) == 32 and re.match(r"^[a-fA-F0-9]+$", hash_value):
            return "MD5/NTLM"
        elif len(hash_value) == 40 and re.match(r"^[a-fA-F0-9]+$", hash_value):
            return "SHA1"
        elif len(hash_value) == 64 and re.match(r"^[a-fA-F0-9]+$", hash_value):
            return "SHA256"

        return None

    def _credential_exists(self, cred: ParsedCredential, result: ParseOutput) -> bool:
        """Check if credential already exists in results."""
        for existing in result.credentials:
            if (existing.username == cred.username and
                existing.password == cred.password and
                existing.hash_value == cred.hash_value):
                return True
        return False


# Register the parser
register_parser("hashcat_parser", HashcatParser)
