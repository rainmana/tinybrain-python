"""Security data retrieval service for querying NVD, ATT&CK, and OWASP data."""

import json
import logging
from typing import Any, Optional

from tinybrain.database.base import DatabaseBackend

logger = logging.getLogger(__name__)


class SecurityRetrievalService:
    """Service for querying security datasets."""

    def __init__(self, db: DatabaseBackend):
        """Initialize the security retrieval service."""
        self.db = db

    async def query_nvd(
        self,
        query: Optional[str] = None,
        cwe_id: Optional[str] = None,
        min_cvss: Optional[float] = None,
        severity: Optional[str] = None,
        component: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query NVD CVE data.
        
        Args:
            query: Text search query
            cwe_id: Filter by CWE ID (e.g., "CWE-89")
            min_cvss: Minimum CVSS score
            severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
            component: Affected component/product
            limit: Maximum number of results
        
        Returns:
            List of CVE dictionaries
        """
        # This would query the nvd_cves table
        # For now, return empty list as the table structure needs to be added
        logger.info(f"Querying NVD data: query={query}, cwe_id={cwe_id}, min_cvss={min_cvss}")
        
        # TODO: Implement actual database query
        # SELECT * FROM nvd_cves WHERE ...
        # Filter by query, cwe_id, min_cvss, severity, component
        # ORDER BY cvss_v3_score DESC
        # LIMIT ?
        
        return []

    async def query_attack(
        self,
        query: Optional[str] = None,
        tactic: Optional[str] = None,
        technique_id: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query MITRE ATT&CK data.
        
        Args:
            query: Text search query
            tactic: Filter by tactic (e.g., "initial-access")
            technique_id: Filter by technique ID (e.g., "T1055.001")
            platform: Filter by platform (e.g., "Windows")
            limit: Maximum number of results
        
        Returns:
            List of technique/tactic dictionaries
        """
        logger.info(
            f"Querying ATT&CK data: query={query}, tactic={tactic}, "
            f"technique_id={technique_id}, platform={platform}"
        )
        
        # TODO: Implement actual database query
        # SELECT * FROM attack_techniques WHERE ...
        # Filter by query, tactic, technique_id, platform
        # ORDER BY ...
        # LIMIT ?
        
        return []

    async def query_owasp(
        self,
        query: Optional[str] = None,
        category: Optional[str] = None,
        vulnerability_type: Optional[str] = None,
        testing_phase: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Query OWASP Testing Guide data.
        
        Args:
            query: Text search query
            category: Testing category (e.g., "authentication")
            vulnerability_type: Type of vulnerability
            testing_phase: Testing phase (static, dynamic)
            limit: Maximum number of results
        
        Returns:
            List of OWASP procedure dictionaries
        """
        logger.info(
            f"Querying OWASP data: query={query}, category={category}, "
            f"vulnerability_type={vulnerability_type}, testing_phase={testing_phase}"
        )
        
        # TODO: Implement actual database query
        # SELECT * FROM owasp_procedures WHERE ...
        # Filter by query, category, vulnerability_type, testing_phase
        # ORDER BY ...
        # LIMIT ?
        
        return []

    def summarize_results(
        self, results: list[dict[str, Any]], data_source: str, max_results: int = 10
    ) -> list[dict[str, Any]]:
        """Summarize results for context efficiency.
        
        This reduces the size of results by keeping only essential fields.
        """
        if len(results) <= max_results:
            return results
        
        summarized = []
        for result in results[:max_results]:
            if data_source == "nvd":
                summarized.append({
                    "id": result.get("id", ""),
                    "description": result.get("description", "")[:200] + "...",
                    "cvss_v3_score": result.get("cvss_v3_score"),
                    "severity": result.get("severity"),
                })
            elif data_source == "attack":
                summarized.append({
                    "id": result.get("id", ""),
                    "name": result.get("name", ""),
                    "tactic": result.get("tactic", ""),
                    "description": result.get("description", "")[:200] + "...",
                })
            elif data_source == "owasp":
                summarized.append({
                    "id": result.get("id", ""),
                    "title": result.get("title", ""),
                    "category": result.get("category", ""),
                    "description": result.get("description", "")[:200] + "...",
                })
            else:
                summarized.append(result)
        
        return summarized

