"""John the Ripper output parser.

Copyright 2025 milbert.ai
"""

import logging
import re

from app.models.credential import HashType
from app.models.job import Job
from app.tools.parsers import register_parser
from app.tools.parsers.base import (
    BaseParser,
    ParsedCredential,
    ParsedResult,
    ParseOutput,
)

logger = logging.getLogger(__name__)


class JohnParser(BaseParser):
    """Parser for John the Ripper output."""

    tool_name = "john"
    creates_credentials = True

    # Pattern to match cracked credentials
    # Format: username:password or hash:password
    # Example: admin:password123
    # Example: $6$rounds=5000$salt$hash:cracked
    CRACKED_PATTERN = re.compile(
        r"^([^\s:]+):(.+)$",
        re.MULTILINE
    )

    # Pattern to match hash type from loading message
    # Example: Loaded 5 password hashes with 5 different salts (bcrypt [Blowfish 32/64 X3])
    # Example: Loaded 1 password hash (Raw-MD5 [MD5 256/256 AVX2 8x3])
    HASH_TYPE_PATTERN = re.compile(
        r"Loaded \d+ password hash(?:es)?(?: with \d+ different salts)? \(([^)\[]+)",
        re.IGNORECASE
    )

    # Pattern to match --show output format
    # Format: username:password:uid:gid:gecos:home:shell
    SHOW_PATTERN = re.compile(
        r"^([^:]+):([^:]+):\d*:\d*:",
        re.MULTILINE
    )

    # Pattern to detect status lines to skip
    SKIP_PATTERNS = [
        re.compile(r"^Using default input encoding", re.IGNORECASE),
        re.compile(r"^Loaded \d+ password", re.IGNORECASE),
        re.compile(r"^Will run \d+ OpenMP", re.IGNORECASE),
        re.compile(r"^Press 'q' or Ctrl-C", re.IGNORECASE),
        re.compile(r"^Session ", re.IGNORECASE),
        re.compile(r"^\d+g \d+:", re.IGNORECASE),  # Progress line
        re.compile(r"^Warning:", re.IGNORECASE),
        re.compile(r"^Note:", re.IGNORECASE),
        re.compile(r"^Proceeding with", re.IGNORECASE),
        re.compile(r"^Cost \d+ ", re.IGNORECASE),
        re.compile(r"^\d+ password hash", re.IGNORECASE),
    ]

    # Hash type mapping from John format names
    HASH_TYPE_MAP = {
        "raw-md5": HashType.MD5.value,
        "md5": HashType.MD5.value,
        "raw-sha1": HashType.SHA1.value,
        "sha1": HashType.SHA1.value,
        "raw-sha256": HashType.SHA256.value,
        "sha256": HashType.SHA256.value,
        "raw-sha512": HashType.SHA512.value,
        "sha512": HashType.SHA512.value,
        "bcrypt": HashType.BCRYPT.value,
        "blowfish": HashType.BCRYPT.value,
        "nt": HashType.NTLM.value,
        "ntlm": HashType.NTLM.value,
        "lm": HashType.LM.value,
        "lanman": HashType.LM.value,
        "mysql": HashType.MYSQL.value,
        "mysql-sha1": HashType.MYSQL.value,
        "postgres": HashType.POSTGRES_MD5.value,
        "mssql": HashType.MSSQL.value,
        "oracle": HashType.ORACLE.value,
        "krb5": HashType.KERBEROS.value,
        "kerberos": HashType.KERBEROS.value,
    }

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse John the Ripper output."""
        result = ParseOutput()

        # Detect hash type from output
        hash_type = self._detect_hash_type(output)

        # Track seen credentials for deduplication
        seen_creds = set()

        # Parse cracked credentials
        for line in output.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Skip status/info lines
            if self._should_skip_line(line):
                continue

            # Try to parse as cracked credential
            self._parse_credential_line(line, result, seen_creds, hash_type)

        logger.info(
            f"John parsing complete: {len(result.credentials)} credentials cracked"
        )
        return result

    def _detect_hash_type(self, output: str) -> str | None:
        """Detect hash type from John output."""
        match = self.HASH_TYPE_PATTERN.search(output)
        if match:
            format_name = match.group(1).strip().lower()

            # Try direct lookup
            if format_name in self.HASH_TYPE_MAP:
                return self.HASH_TYPE_MAP[format_name]

            # Try partial match
            for key, value in self.HASH_TYPE_MAP.items():
                if key in format_name or format_name in key:
                    return value

            # Return raw format name if no mapping
            return format_name

        return HashType.UNKNOWN.value

    def _should_skip_line(self, line: str) -> bool:
        """Check if line should be skipped (status/info line)."""
        for pattern in self.SKIP_PATTERNS:
            if pattern.match(line):
                return True
        return False

    def _parse_credential_line(
        self,
        line: str,
        result: ParseOutput,
        seen: set,
        hash_type: str | None,
    ) -> None:
        """Parse a potential credential line."""
        # Try --show format first (username:password:uid:gid:...)
        show_match = self.SHOW_PATTERN.match(line)
        if show_match:
            username = show_match.group(1)
            password = show_match.group(2)
            self._add_credential(result, seen, username, password, hash_type)
            return

        # Try standard format (username:password or hash:password)
        cracked_match = self.CRACKED_PATTERN.match(line)
        if cracked_match:
            identifier = cracked_match.group(1)
            password = cracked_match.group(2)

            # Skip if password looks like it might be part of hash format
            if password.startswith("$") or len(password) > 100:
                return

            self._add_credential(result, seen, identifier, password, hash_type)

    def _add_credential(
        self,
        result: ParseOutput,
        seen: set,
        identifier: str,
        password: str,
        hash_type: str | None,
    ) -> None:
        """Add a credential to the result."""
        # Create unique key
        cred_key = f"{identifier}:{password}"
        if cred_key in seen:
            return
        seen.add(cred_key)

        # Determine if identifier is a username or hash
        is_hash_identifier = (
            identifier.startswith("$")
            or (len(identifier) in [32, 40, 64, 128]
                and all(c in "0123456789abcdefABCDEF" for c in identifier))
        )

        result.credentials.append(
            ParsedCredential(
                username=None if is_hash_identifier else identifier,
                password=password,
                hash_value=identifier if is_hash_identifier else None,
                hash_type=hash_type,
                credential_type="hash",
                metadata={
                    "source": "john",
                    "original_identifier": identifier,
                },
            )
        )

        # Also create a result entry for tracking
        result.results.append(
            ParsedResult(
                result_type="CREDENTIAL",
                parsed_data={
                    "identifier": identifier,
                    "password": password,
                    "hash_type": hash_type,
                },
                raw_data=f"{identifier}:{password}",
                severity="high",
            )
        )


# Register the parser
register_parser("john_parser", JohnParser)
