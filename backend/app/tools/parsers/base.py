"""Base parser class and common utilities for tool output parsing.

Copyright 2025 milbert.ai
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.credential import Credential
from app.models.job import Job
from app.models.result import Result, ResultType
from app.models.vulnerability import Vulnerability, VulnerabilitySeverity
from app.services.encryption import encrypt_sensitive_data

logger = logging.getLogger(__name__)


@dataclass
class ParsedAsset:
    """Represents a parsed asset to be created or updated."""

    type: str
    value: str
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    risk_score: int = 0


@dataclass
class ParsedVulnerability:
    """Represents a parsed vulnerability to be created or updated."""

    title: str
    severity: str
    description: str | None = None
    cvss_score: float | None = None
    cvss_vector: str | None = None
    cve_ids: list[str] = field(default_factory=list)
    cwe_ids: list[str] = field(default_factory=list)
    evidence: str | None = None
    remediation: str | None = None
    references: list[str] = field(default_factory=list)
    template_id: str | None = None
    request: str | None = None
    response: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    # For linking to asset
    asset_value: str | None = None
    asset_type: str | None = None


@dataclass
class ParsedCredential:
    """Represents a parsed credential to be created or updated."""

    username: str | None = None
    password: str | None = None
    hash_value: str | None = None
    hash_type: str | None = None
    service: str | None = None
    port: int | None = None
    url: str | None = None
    domain: str | None = None
    credential_type: str = "password"
    metadata: dict[str, Any] = field(default_factory=dict)
    # For linking to asset
    asset_value: str | None = None
    asset_type: str | None = None


@dataclass
class ParsedResult:
    """Represents a raw parsed result."""

    result_type: str
    parsed_data: dict[str, Any]
    raw_data: str | None = None
    severity: str | None = None
    # For linking to asset
    asset_value: str | None = None
    asset_type: str | None = None


@dataclass
class ParseOutput:
    """Complete output from a parser."""

    assets: list[ParsedAsset] = field(default_factory=list)
    vulnerabilities: list[ParsedVulnerability] = field(default_factory=list)
    credentials: list[ParsedCredential] = field(default_factory=list)
    results: list[ParsedResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def generate_fingerprint(*args) -> str:
    """Generate a SHA256 fingerprint from the given arguments."""
    data = ":".join(str(arg) for arg in args if arg is not None)
    return hashlib.sha256(data.encode()).hexdigest()[:32]


class BaseParser(ABC):
    """Base class for all tool output parsers."""

    # Override in subclasses
    tool_name: str = "unknown"
    creates_assets: bool = False
    creates_vulnerabilities: bool = False
    creates_credentials: bool = False

    @abstractmethod
    def parse(self, output: str, job: Job) -> ParseOutput:
        """
        Parse tool output and return structured data.

        Args:
            output: Raw tool output (concatenated stdout)
            job: The Job instance this output belongs to

        Returns:
            ParseOutput containing assets, vulnerabilities, credentials, and results
        """
        raise NotImplementedError

    async def save_results(
        self,
        db: AsyncSession,
        job: Job,
        parse_output: ParseOutput,
    ) -> dict[str, int]:
        """
        Save parsed results to the database with upsert logic.

        Args:
            db: Database session
            job: The Job instance
            parse_output: Parsed output from the parse() method

        Returns:
            Dict with counts of created/updated items
        """
        stats = {
            "assets_created": 0,
            "assets_updated": 0,
            "vulnerabilities_created": 0,
            "vulnerabilities_updated": 0,
            "credentials_created": 0,
            "credentials_updated": 0,
            "results_created": 0,
        }

        # Cache for asset lookups (value -> asset)
        asset_cache: dict[str, Asset] = {}

        # Process assets first so we can link vulns/creds to them
        for parsed_asset in parse_output.assets:
            asset, created = await self._upsert_asset(db, job, parsed_asset)
            asset_cache[parsed_asset.value] = asset
            if created:
                stats["assets_created"] += 1
            else:
                stats["assets_updated"] += 1

        # Process vulnerabilities
        for parsed_vuln in parse_output.vulnerabilities:
            # Try to find linked asset
            asset_id = None
            if parsed_vuln.asset_value and parsed_vuln.asset_value in asset_cache:
                asset_id = asset_cache[parsed_vuln.asset_value].id
            elif parsed_vuln.asset_value:
                # Try to find asset in database
                asset = await self._find_asset(
                    db, job.project_id, parsed_vuln.asset_value, parsed_vuln.asset_type
                )
                if asset:
                    asset_id = asset.id
                    asset_cache[parsed_vuln.asset_value] = asset

            _, created = await self._upsert_vulnerability(
                db, job, parsed_vuln, asset_id
            )
            if created:
                stats["vulnerabilities_created"] += 1
            else:
                stats["vulnerabilities_updated"] += 1

        # Process credentials
        for parsed_cred in parse_output.credentials:
            # Try to find linked asset
            asset_id = None
            if parsed_cred.asset_value and parsed_cred.asset_value in asset_cache:
                asset_id = asset_cache[parsed_cred.asset_value].id
            elif parsed_cred.asset_value:
                asset = await self._find_asset(
                    db, job.project_id, parsed_cred.asset_value, parsed_cred.asset_type
                )
                if asset:
                    asset_id = asset.id
                    asset_cache[parsed_cred.asset_value] = asset

            _, created = await self._upsert_credential(db, job, parsed_cred, asset_id)
            if created:
                stats["credentials_created"] += 1
            else:
                stats["credentials_updated"] += 1

        # Process raw results
        for parsed_result in parse_output.results:
            # Try to find linked asset
            asset_id = None
            if parsed_result.asset_value and parsed_result.asset_value in asset_cache:
                asset_id = asset_cache[parsed_result.asset_value].id
            elif parsed_result.asset_value:
                asset = await self._find_asset(
                    db, job.project_id, parsed_result.asset_value, parsed_result.asset_type
                )
                if asset:
                    asset_id = asset.id

            await self._create_result(db, job, parsed_result, asset_id)
            stats["results_created"] += 1

        await db.commit()
        return stats

    async def _find_asset(
        self,
        db: AsyncSession,
        project_id: UUID,
        value: str,
        asset_type: str | None = None,
    ) -> Asset | None:
        """Find an existing asset by value."""
        query = select(Asset).where(
            Asset.project_id == project_id,
            Asset.value == value,
        )
        if asset_type:
            query = query.where(Asset.type == asset_type)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def _upsert_asset(
        self,
        db: AsyncSession,
        job: Job,
        parsed_asset: ParsedAsset,
    ) -> tuple[Asset, bool]:
        """Create or update an asset. Returns (asset, created)."""
        fingerprint = generate_fingerprint(
            job.project_id, parsed_asset.type, parsed_asset.value
        )

        # Check for existing asset by fingerprint or value
        result = await db.execute(
            select(Asset).where(
                Asset.project_id == job.project_id,
                Asset.type == parsed_asset.type,
                Asset.value == parsed_asset.value,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing asset
            existing.metadata_ = {**existing.metadata_, **parsed_asset.metadata}
            existing.tags = list(set(existing.tags + parsed_asset.tags))
            existing.risk_score = max(existing.risk_score, parsed_asset.risk_score)
            await db.flush()
            return existing, False
        else:
            # Create new asset
            asset = Asset(
                project_id=job.project_id,
                type=parsed_asset.type,
                value=parsed_asset.value,
                metadata_=parsed_asset.metadata,
                tags=parsed_asset.tags,
                risk_score=parsed_asset.risk_score,
                discovered_by=job.id,
            )
            db.add(asset)
            await db.flush()
            return asset, True

    async def _upsert_vulnerability(
        self,
        db: AsyncSession,
        job: Job,
        parsed_vuln: ParsedVulnerability,
        asset_id: UUID | None,
    ) -> tuple[Vulnerability, bool]:
        """Create or update a vulnerability. Returns (vulnerability, created)."""
        # Generate fingerprint based on key identifying fields
        fingerprint = generate_fingerprint(
            job.project_id,
            parsed_vuln.title,
            parsed_vuln.template_id or "",
            asset_id or "",
        )

        # Check for existing vulnerability
        result = await db.execute(
            select(Vulnerability).where(Vulnerability.fingerprint == fingerprint)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing vulnerability
            if parsed_vuln.description:
                existing.description = parsed_vuln.description
            if parsed_vuln.evidence:
                existing.evidence = parsed_vuln.evidence
            if parsed_vuln.request:
                existing.request = parsed_vuln.request
            if parsed_vuln.response:
                existing.response = parsed_vuln.response
            existing.metadata_ = {**existing.metadata_, **parsed_vuln.metadata}
            existing.tags = list(set(existing.tags + parsed_vuln.tags))
            existing.references = list(set(existing.references + parsed_vuln.references))
            existing.cve_ids = list(set(existing.cve_ids + parsed_vuln.cve_ids))
            existing.cwe_ids = list(set(existing.cwe_ids + parsed_vuln.cwe_ids))
            await db.flush()
            return existing, False
        else:
            # Create new vulnerability
            vuln = Vulnerability(
                project_id=job.project_id,
                asset_id=asset_id,
                title=parsed_vuln.title,
                description=parsed_vuln.description,
                severity=parsed_vuln.severity,
                cvss_score=parsed_vuln.cvss_score,
                cvss_vector=parsed_vuln.cvss_vector,
                cve_ids=parsed_vuln.cve_ids,
                cwe_ids=parsed_vuln.cwe_ids,
                evidence=parsed_vuln.evidence,
                remediation=parsed_vuln.remediation,
                references=parsed_vuln.references,
                template_id=parsed_vuln.template_id,
                tool_name=self.tool_name,
                request=parsed_vuln.request,
                response=parsed_vuln.response,
                metadata_=parsed_vuln.metadata,
                tags=parsed_vuln.tags,
                fingerprint=fingerprint,
                discovered_by=job.id,
            )
            db.add(vuln)
            await db.flush()
            return vuln, True

    async def _upsert_credential(
        self,
        db: AsyncSession,
        job: Job,
        parsed_cred: ParsedCredential,
        asset_id: UUID | None,
    ) -> tuple[Credential, bool]:
        """Create or update a credential. Returns (credential, created)."""
        # Generate fingerprint
        fingerprint = generate_fingerprint(
            job.project_id,
            parsed_cred.username or "",
            parsed_cred.service or "",
            parsed_cred.port or "",
            asset_id or "",
        )

        # Check for existing credential
        result = await db.execute(
            select(Credential).where(Credential.fingerprint == fingerprint)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing credential
            if parsed_cred.password:
                existing.plaintext_encrypted = encrypt_sensitive_data(parsed_cred.password)
            if parsed_cred.hash_value:
                existing.hash_value = parsed_cred.hash_value
                existing.hash_type = parsed_cred.hash_type
            existing.is_valid = True
            existing.metadata_ = {**existing.metadata_, **parsed_cred.metadata}
            await db.flush()
            return existing, False
        else:
            # Create new credential
            cred = Credential(
                project_id=job.project_id,
                asset_id=asset_id,
                credential_type=parsed_cred.credential_type,
                username=parsed_cred.username,
                domain=parsed_cred.domain,
                plaintext_encrypted=encrypt_sensitive_data(parsed_cred.password) if parsed_cred.password else None,
                hash_value=parsed_cred.hash_value,
                hash_type=parsed_cred.hash_type,
                service=parsed_cred.service,
                port=parsed_cred.port,
                url=parsed_cred.url,
                source=self.tool_name,
                discovered_by=job.id,
                metadata_=parsed_cred.metadata,
                fingerprint=fingerprint,
                is_valid=True,
            )
            db.add(cred)
            await db.flush()
            return cred, True

    async def _create_result(
        self,
        db: AsyncSession,
        job: Job,
        parsed_result: ParsedResult,
        asset_id: UUID | None,
    ) -> Result:
        """Create a new result record."""
        fingerprint = generate_fingerprint(
            job.id,
            parsed_result.result_type,
            str(parsed_result.parsed_data),
        )

        result = Result(
            job_id=job.id,
            asset_id=asset_id,
            result_type=parsed_result.result_type,
            severity=parsed_result.severity,
            raw_data=parsed_result.raw_data,
            parsed_data=parsed_result.parsed_data,
            fingerprint=fingerprint,
        )
        db.add(result)
        await db.flush()
        return result
