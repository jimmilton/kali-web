"""Parser registry for tool output parsing."""

import logging
from typing import Dict, Optional, Type

from app.tools.parsers.base import BaseParser

logger = logging.getLogger(__name__)

# Registry of parser classes
_parsers: Dict[str, Type[BaseParser]] = {}


def register_parser(name: str, parser_class: Type[BaseParser]) -> None:
    """Register a parser class."""
    _parsers[name] = parser_class
    logger.debug(f"Registered parser: {name}")


def get_parser(name: str) -> Optional[BaseParser]:
    """
    Get a parser instance by name.

    Args:
        name: Parser name (e.g., 'nmap_parser', 'nuclei_parser')

    Returns:
        Parser instance or None if not found
    """
    parser_class = _parsers.get(name)
    if parser_class:
        return parser_class()
    logger.warning(f"Parser not found: {name}")
    return None


def list_parsers() -> list[str]:
    """List all registered parser names."""
    return list(_parsers.keys())


# Import and register all parsers
# Each parser module registers itself when imported
def _load_parsers():
    """Load all parser modules to trigger registration."""
    try:
        from app.tools.parsers import nmap_parser
    except ImportError as e:
        logger.debug(f"nmap_parser not available: {e}")

    try:
        from app.tools.parsers import nuclei_parser
    except ImportError as e:
        logger.debug(f"nuclei_parser not available: {e}")

    try:
        from app.tools.parsers import subfinder_parser
    except ImportError as e:
        logger.debug(f"subfinder_parser not available: {e}")

    try:
        from app.tools.parsers import masscan_parser
    except ImportError as e:
        logger.debug(f"masscan_parser not available: {e}")

    try:
        from app.tools.parsers import httpx_parser
    except ImportError as e:
        logger.debug(f"httpx_parser not available: {e}")

    try:
        from app.tools.parsers import gobuster_parser
    except ImportError as e:
        logger.debug(f"gobuster_parser not available: {e}")

    try:
        from app.tools.parsers import ffuf_parser
    except ImportError as e:
        logger.debug(f"ffuf_parser not available: {e}")

    try:
        from app.tools.parsers import nikto_parser
    except ImportError as e:
        logger.debug(f"nikto_parser not available: {e}")

    try:
        from app.tools.parsers import hydra_parser
    except ImportError as e:
        logger.debug(f"hydra_parser not available: {e}")

    try:
        from app.tools.parsers import sqlmap_parser
    except ImportError as e:
        logger.debug(f"sqlmap_parser not available: {e}")

    try:
        from app.tools.parsers import john_parser
    except ImportError as e:
        logger.debug(f"john_parser not available: {e}")

    try:
        from app.tools.parsers import amass_parser
    except ImportError as e:
        logger.debug(f"amass_parser not available: {e}")

    try:
        from app.tools.parsers import wpscan_parser
    except ImportError as e:
        logger.debug(f"wpscan_parser not available: {e}")

    try:
        from app.tools.parsers import hashcat_parser
    except ImportError as e:
        logger.debug(f"hashcat_parser not available: {e}")

    try:
        from app.tools.parsers import nessus_parser
    except ImportError as e:
        logger.debug(f"nessus_parser not available: {e}")

    try:
        from app.tools.parsers import burp_parser
    except ImportError as e:
        logger.debug(f"burp_parser not available: {e}")


# Load parsers on module import
_load_parsers()
