"""SQLMap text output parser.

Copyright 2025 milbert.ai
"""

import logging
import re

from app.models.asset import AssetType
from app.models.job import Job
from app.models.vulnerability import VulnerabilitySeverity
from app.tools.parsers import register_parser
from app.tools.parsers.base import (
    BaseParser,
    ParsedAsset,
    ParsedCredential,
    ParsedResult,
    ParsedVulnerability,
    ParseOutput,
)

logger = logging.getLogger(__name__)


class SqlmapParser(BaseParser):
    """Parser for SQLMap text output."""

    tool_name = "sqlmap"
    creates_assets = True
    creates_vulnerabilities = True
    creates_credentials = True

    # Pattern to match injection point detection
    # Example: Parameter: id (GET)
    PARAM_PATTERN = re.compile(
        r"Parameter:\s*(\S+)\s*\((\w+)\)",
        re.IGNORECASE
    )

    # Pattern to match injection type
    # Example: Type: boolean-based blind
    TYPE_PATTERN = re.compile(
        r"Type:\s*(.+?)(?:\n|$)",
        re.IGNORECASE
    )

    # Pattern to match payload
    # Example: Payload: id=1 AND 1=1
    PAYLOAD_PATTERN = re.compile(
        r"Payload:\s*(.+?)(?:\n|$)",
        re.IGNORECASE
    )

    # Pattern to match DBMS detection
    # Example: [INFO] the back-end DBMS is MySQL
    DBMS_PATTERN = re.compile(
        r"\[INFO\]\s*the back-end DBMS is\s+(\S+)",
        re.IGNORECASE
    )

    # Pattern to match database version
    # Example: web application technology: PHP 7.4.3, Apache 2.4.41
    TECH_PATTERN = re.compile(
        r"web application technology:\s*(.+?)(?:\n|$)",
        re.IGNORECASE
    )

    # Pattern to match available databases
    # Example: available databases [5]:
    DB_LIST_PATTERN = re.compile(
        r"available databases \[(\d+)\]:",
        re.IGNORECASE
    )

    # Pattern to match database name in list
    # Example: [*] information_schema
    DB_NAME_PATTERN = re.compile(
        r"^\[\*\]\s+(\S+)",
        re.MULTILINE
    )

    # Pattern to match table dump header
    # Example: Database: testdb
    # Table: users
    DUMP_DB_PATTERN = re.compile(
        r"Database:\s*(\S+)",
        re.IGNORECASE
    )
    DUMP_TABLE_PATTERN = re.compile(
        r"Table:\s*(\S+)",
        re.IGNORECASE
    )

    # Pattern to match credential-like columns in dumps
    # Looks for username/password/email/hash columns
    CRED_COLUMNS = ["username", "user", "login", "email", "password", "passwd", "pass", "hash", "pwd"]

    def parse(self, output: str, job: Job) -> ParseOutput:
        """Parse SQLMap text output."""
        result = ParseOutput()

        # Extract target URL from job parameters
        target = job.parameters.get("target", job.parameters.get("url", "unknown"))

        # Track found injections for deduplication
        seen_injections = set()

        # Parse injection points
        self._parse_injections(output, result, target, seen_injections)

        # Parse DBMS info
        self._parse_dbms_info(output, result, target)

        # Parse technology info
        self._parse_tech_info(output, result, target)

        # Parse database list
        self._parse_databases(output, result, target)

        # Parse table dumps for credentials
        self._parse_dumps(output, result, target)

        logger.info(
            f"SQLMap parsing complete: {len(result.assets)} assets, "
            f"{len(result.vulnerabilities)} vulnerabilities, "
            f"{len(result.credentials)} credentials"
        )
        return result

    def _parse_injections(
        self,
        output: str,
        result: ParseOutput,
        target: str,
        seen: set,
    ) -> None:
        """Parse SQL injection findings."""
        # Split output into sections by parameter
        sections = re.split(r"---\n", output)

        current_param = None
        current_method = None

        for section in sections:
            # Check for parameter line
            param_match = self.PARAM_PATTERN.search(section)
            if param_match:
                current_param = param_match.group(1)
                current_method = param_match.group(2)

            # Look for injection types in this section
            type_matches = self.TYPE_PATTERN.findall(section)
            payload_matches = self.PAYLOAD_PATTERN.findall(section)

            for i, inj_type in enumerate(type_matches):
                inj_type = inj_type.strip()
                if not inj_type or not current_param:
                    continue

                # Create unique key
                key = f"{current_param}:{current_method}:{inj_type}"
                if key in seen:
                    continue
                seen.add(key)

                # Get payload if available
                payload = payload_matches[i] if i < len(payload_matches) else None

                # Determine severity based on injection type
                severity = self._get_severity(inj_type)

                # Create vulnerability
                result.vulnerabilities.append(
                    ParsedVulnerability(
                        title=f"SQL Injection - {current_param} ({inj_type})",
                        severity=severity,
                        description=(
                            f"SQL injection vulnerability found in parameter '{current_param}' "
                            f"via {current_method} request. Injection type: {inj_type}."
                        ),
                        cwe_ids=["CWE-89"],
                        evidence=f"Parameter: {current_param}\nMethod: {current_method}\nType: {inj_type}"
                                 + (f"\nPayload: {payload}" if payload else ""),
                        remediation=(
                            "Use parameterized queries or prepared statements. "
                            "Implement proper input validation and sanitization. "
                            "Apply principle of least privilege to database accounts."
                        ),
                        references=[
                            "https://owasp.org/www-community/attacks/SQL_Injection",
                            "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
                        ],
                        template_id=f"sqlmap:{current_param}:{inj_type}",
                        metadata={
                            "parameter": current_param,
                            "method": current_method,
                            "injection_type": inj_type,
                            "payload": payload,
                        },
                        tags=["sqlmap", "sql-injection", inj_type.lower().replace(" ", "-")],
                        asset_value=target,
                        asset_type=AssetType.URL.value,
                    )
                )

    def _get_severity(self, injection_type: str) -> str:
        """Determine severity based on injection type."""
        inj_lower = injection_type.lower()

        # Stacked queries and UNION-based are most dangerous
        if "stacked" in inj_lower or "union" in inj_lower:
            return VulnerabilitySeverity.CRITICAL.value

        # Time-based and error-based are high severity
        if "time-based" in inj_lower or "error-based" in inj_lower:
            return VulnerabilitySeverity.HIGH.value

        # Boolean-based is medium-high
        if "boolean" in inj_lower:
            return VulnerabilitySeverity.HIGH.value

        # Default to high for any SQL injection
        return VulnerabilitySeverity.HIGH.value

    def _parse_dbms_info(
        self,
        output: str,
        result: ParseOutput,
        target: str,
    ) -> None:
        """Parse DBMS detection info."""
        match = self.DBMS_PATTERN.search(output)
        if match:
            dbms = match.group(1).strip()

            # Create service asset for the database
            result.assets.append(
                ParsedAsset(
                    type=AssetType.SERVICE.value,
                    value=f"{target}:database:{dbms}",
                    metadata={
                        "dbms": dbms,
                        "source": "sqlmap",
                    },
                    tags=["sqlmap", "database", dbms.lower()],
                    risk_score=70,
                )
            )

            # Create result entry
            result.results.append(
                ParsedResult(
                    result_type="SERVICE",
                    parsed_data={
                        "dbms": dbms,
                        "target": target,
                    },
                    raw_data=match.group(0),
                    severity="info",
                )
            )

    def _parse_tech_info(
        self,
        output: str,
        result: ParseOutput,
        target: str,
    ) -> None:
        """Parse web technology info."""
        match = self.TECH_PATTERN.search(output)
        if match:
            tech_string = match.group(1).strip()
            technologies = [t.strip() for t in tech_string.split(",")]

            for tech in technologies:
                if tech:
                    result.assets.append(
                        ParsedAsset(
                            type=AssetType.TECHNOLOGY.value,
                            value=tech,
                            metadata={
                                "target": target,
                                "source": "sqlmap",
                            },
                            tags=["sqlmap", "technology"],
                        )
                    )

    def _parse_databases(
        self,
        output: str,
        result: ParseOutput,
        target: str,
    ) -> None:
        """Parse discovered database names."""
        # Find database list section
        list_match = self.DB_LIST_PATTERN.search(output)
        if not list_match:
            return

        # Find position after the header
        start_pos = list_match.end()

        # Extract database names
        remaining = output[start_pos:start_pos + 2000]  # Limit search area
        db_names = self.DB_NAME_PATTERN.findall(remaining)

        for db_name in db_names:
            if db_name:
                result.results.append(
                    ParsedResult(
                        result_type="RAW",
                        parsed_data={
                            "database_name": db_name,
                            "target": target,
                        },
                        raw_data=f"Database: {db_name}",
                        severity="info",
                    )
                )

    def _parse_dumps(
        self,
        output: str,
        result: ParseOutput,
        target: str,
    ) -> None:
        """Parse table dumps for credentials."""
        # Look for table dump sections
        # SQLMap dumps are formatted as ASCII tables

        # Find dump headers
        db_matches = list(self.DUMP_DB_PATTERN.finditer(output))

        for db_match in db_matches:
            db_name = db_match.group(1)
            section_start = db_match.start()

            # Find table name after database
            table_match = self.DUMP_TABLE_PATTERN.search(output[section_start:section_start + 500])
            if not table_match:
                continue

            table_name = table_match.group(1)

            # Look for ASCII table structure with columns
            # Pattern: | column1 | column2 | column3 |
            table_start = section_start + table_match.end()
            section_end = output.find("\n\n", table_start)
            if section_end == -1:
                section_end = min(table_start + 5000, len(output))

            table_section = output[table_start:section_end]

            # Extract credentials from table
            self._extract_credentials_from_table(
                table_section, db_name, table_name, target, result
            )

    def _extract_credentials_from_table(
        self,
        table_text: str,
        db_name: str,
        table_name: str,
        target: str,
        result: ParseOutput,
    ) -> None:
        """Extract credentials from ASCII table dump."""
        lines = table_text.split("\n")

        # Find header row (contains column names)
        header_idx = -1
        columns = []

        for i, line in enumerate(lines):
            if "|" in line and not line.startswith("+"):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if parts:
                    # Check if this looks like a header (has credential column names)
                    lower_parts = [p.lower() for p in parts]
                    if any(col in lower_parts for col in self.CRED_COLUMNS):
                        columns = parts
                        header_idx = i
                        break

        if header_idx == -1 or not columns:
            return

        # Map column indices
        col_map = {col.lower(): idx for idx, col in enumerate(columns)}

        # Find username and password columns
        user_idx = None
        pass_idx = None

        for col_name in ["username", "user", "login", "email"]:
            if col_name in col_map:
                user_idx = col_map[col_name]
                break

        for col_name in ["password", "passwd", "pass", "hash", "pwd"]:
            if col_name in col_map:
                pass_idx = col_map[col_name]
                break

        if user_idx is None and pass_idx is None:
            return

        # Parse data rows
        seen_creds = set()

        for line in lines[header_idx + 1:]:
            if "|" not in line or line.startswith("+"):
                continue

            parts = [p.strip() for p in line.split("|") if p.strip()]
            if len(parts) < max(filter(None, [user_idx, pass_idx]), default=0) + 1:
                continue

            username = parts[user_idx] if user_idx is not None and user_idx < len(parts) else None
            password = parts[pass_idx] if pass_idx is not None and pass_idx < len(parts) else None

            if not username and not password:
                continue

            # Dedup
            cred_key = f"{username}:{password}"
            if cred_key in seen_creds:
                continue
            seen_creds.add(cred_key)

            # Determine if password is a hash
            is_hash = (
                password
                and len(password) in [32, 40, 64, 128]  # Common hash lengths
                and all(c in "0123456789abcdefABCDEF$." for c in password)
            )

            result.credentials.append(
                ParsedCredential(
                    username=username,
                    password=None if is_hash else password,
                    hash_value=password if is_hash else None,
                    hash_type="unknown" if is_hash else None,
                    service="database",
                    credential_type="hash" if is_hash else "password",
                    metadata={
                        "database": db_name,
                        "table": table_name,
                        "source": "sqlmap",
                        "target": target,
                    },
                    asset_value=target,
                    asset_type=AssetType.URL.value,
                )
            )


# Register the parser
register_parser("sqlmap_parser", SqlmapParser)
