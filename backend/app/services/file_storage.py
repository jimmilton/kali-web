"""Filesystem-based file storage service.

Copyright 2025 milbert.ai

Replaces MinIO with simple filesystem storage.
"""

import hashlib
import logging
import mimetypes
import shutil
from datetime import datetime
from pathlib import Path
from typing import BinaryIO, Optional
from uuid import uuid4

from app.config import settings

logger = logging.getLogger(__name__)


class FileStorage:
    """Simple filesystem-based file storage."""

    def __init__(self, base_path: Optional[Path] = None):
        self.base_path = base_path or settings.uploads_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        file: BinaryIO,
        filename: str,
        folder: str = "",
        content_type: Optional[str] = None,
    ) -> dict:
        """
        Save a file to storage.

        Args:
            file: File-like object
            filename: Original filename
            folder: Subfolder to store in
            content_type: MIME type

        Returns:
            Dict with file metadata
        """
        # Generate unique filename
        ext = Path(filename).suffix
        unique_name = f"{uuid4().hex}{ext}"

        # Create folder path
        folder_path = self.base_path / folder if folder else self.base_path
        folder_path.mkdir(parents=True, exist_ok=True)

        # Full file path
        file_path = folder_path / unique_name

        # Calculate hash while saving
        hasher = hashlib.sha256()
        size = 0

        with open(file_path, "wb") as f:
            while chunk := file.read(8192):
                f.write(chunk)
                hasher.update(chunk)
                size += len(chunk)

        # Detect content type if not provided
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or "application/octet-stream"

        return {
            "id": unique_name,
            "filename": filename,
            "path": str(file_path.relative_to(self.base_path)),
            "size": size,
            "hash": hasher.hexdigest(),
            "content_type": content_type,
            "created_at": datetime.utcnow().isoformat(),
        }

    def get(self, file_id: str, folder: str = "") -> Optional[Path]:
        """
        Get file path by ID.

        Args:
            file_id: File ID (unique name)
            folder: Subfolder

        Returns:
            Path to file or None if not found
        """
        folder_path = self.base_path / folder if folder else self.base_path
        file_path = folder_path / file_id

        if file_path.exists():
            return file_path
        return None

    def read(self, file_id: str, folder: str = "") -> Optional[bytes]:
        """Read file contents."""
        file_path = self.get(file_id, folder)
        if file_path:
            return file_path.read_bytes()
        return None

    def delete(self, file_id: str, folder: str = "") -> bool:
        """
        Delete a file.

        Args:
            file_id: File ID
            folder: Subfolder

        Returns:
            True if deleted, False if not found
        """
        file_path = self.get(file_id, folder)
        if file_path:
            file_path.unlink()
            logger.info(f"Deleted file: {file_id}")
            return True
        return False

    def list_files(self, folder: str = "") -> list:
        """List files in a folder."""
        folder_path = self.base_path / folder if folder else self.base_path
        if not folder_path.exists():
            return []

        files = []
        for f in folder_path.iterdir():
            if f.is_file():
                stat = f.stat()
                files.append({
                    "id": f.name,
                    "size": stat.st_size,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
        return files

    def get_size(self, folder: str = "") -> int:
        """Get total size of files in folder."""
        folder_path = self.base_path / folder if folder else self.base_path
        if not folder_path.exists():
            return 0

        total = 0
        for f in folder_path.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total

    def cleanup_old_files(self, folder: str, max_age_days: int = 30) -> int:
        """Delete files older than max_age_days."""
        folder_path = self.base_path / folder if folder else self.base_path
        if not folder_path.exists():
            return 0

        cutoff = datetime.utcnow().timestamp() - (max_age_days * 86400)
        deleted = 0

        for f in folder_path.rglob("*"):
            if f.is_file() and f.stat().st_mtime < cutoff:
                f.unlink()
                deleted += 1

        logger.info(f"Cleaned up {deleted} old files from {folder}")
        return deleted


# Global storage instance
file_storage = FileStorage()


def save_report(file: BinaryIO, filename: str) -> dict:
    """Save a report file."""
    storage = FileStorage(settings.reports_path)
    return storage.save(file, filename, folder="")


def get_report(file_id: str) -> Optional[Path]:
    """Get a report file path."""
    storage = FileStorage(settings.reports_path)
    return storage.get(file_id)


def save_output(content: str, job_id: str, filename: str) -> dict:
    """Save tool output to a file."""
    storage = FileStorage(settings.outputs_path)
    folder = str(job_id)

    # Create folder for job outputs
    (storage.base_path / folder).mkdir(parents=True, exist_ok=True)

    # Write content
    file_path = storage.base_path / folder / filename
    file_path.write_text(content)

    return {
        "id": filename,
        "path": str(file_path.relative_to(storage.base_path)),
        "size": len(content),
    }


def get_output(job_id: str, filename: str) -> Optional[str]:
    """Get tool output content."""
    storage = FileStorage(settings.outputs_path)
    file_path = storage.base_path / str(job_id) / filename
    if file_path.exists():
        return file_path.read_text()
    return None
