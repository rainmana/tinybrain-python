"""Security data downloader for NVD, ATT&CK, and OWASP datasets."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


class SecurityDataDownloader:
    """Handles downloading and updating security datasets."""

    def __init__(self, rate_limit: float = 1.0):
        """Initialize the security data downloader.
        
        Args:
            rate_limit: Requests per second (default: 1.0 for NVD API compliance)
        """
        self.rate_limit = rate_limit
        self.client = httpx.AsyncClient(
            timeout=30.0 * 60,  # 30 minutes for large downloads
            headers={
                "User-Agent": "TinyBrain-SecurityHub/2.0 (Security Research Tool)",
                "Accept": "application/json",
            },
        )
        self._rate_limiter = asyncio.Semaphore(1)  # Simple rate limiting

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def _rate_limited_get(self, url: str) -> httpx.Response:
        """Perform a rate-limited HTTP GET request."""
        async with self._rate_limiter:
            await asyncio.sleep(1.0 / self.rate_limit)
            return await self.client.get(url)

    async def download_nvd_dataset(
        self, start_index: int = 0, max_results: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Download the complete NVD dataset.
        
        Args:
            start_index: Starting index for pagination
            max_results: Maximum number of results to download (None for all)
        
        Returns:
            List of CVE dictionaries
        """
        logger.info("Starting NVD dataset download")
        
        all_cves = []
        current_index = start_index
        results_per_page = 2000  # NVD API max
        
        while True:
            url = (
                f"https://services.nvd.nist.gov/rest/json/cves/2.0"
                f"?startIndex={current_index}&resultsPerPage={results_per_page}"
            )
            
            logger.debug(f"Downloading NVD batch: startIndex={current_index}")
            
            try:
                response = await self._rate_limited_get(url)
                response.raise_for_status()
                data = response.json()
                
                vulnerabilities = data.get("vulnerabilities", [])
                total_results = data.get("totalResults", 0)
                
                for vuln in vulnerabilities:
                    cve_data = self._convert_nvd_to_dict(vuln)
                    all_cves.append(cve_data)
                
                logger.info(
                    f"Downloaded NVD batch: {len(vulnerabilities)} CVEs, "
                    f"total so far: {len(all_cves)}"
                )
                
                # Check if we've downloaded everything
                if current_index + results_per_page >= total_results:
                    break
                
                if max_results and len(all_cves) >= max_results:
                    all_cves = all_cves[:max_results]
                    break
                
                current_index += results_per_page
                
            except httpx.HTTPError as e:
                logger.error(f"Failed to download NVD data: {e}")
                raise
            except Exception as e:
                logger.error(f"Error processing NVD data: {e}")
                raise
        
        logger.info(f"NVD dataset download completed: {len(all_cves)} CVEs")
        return all_cves

    def _convert_nvd_to_dict(self, vuln: dict[str, Any]) -> dict[str, Any]:
        """Convert NVD API response to our dictionary format."""
        cve = vuln.get("cve", {})
        cve_id = cve.get("id", "")
        
        # Extract description
        descriptions = cve.get("descriptions", [])
        description = ""
        for desc in descriptions:
            if desc.get("lang") == "en":
                description = desc.get("value", "")
                break
        
        # Extract CVSS scores
        metrics = cve.get("metrics", {})
        cvss_v2_score = None
        cvss_v2_vector = None
        cvss_v3_score = None
        cvss_v3_vector = None
        severity = None
        
        cvss_v2 = metrics.get("cvssMetricV2", [])
        if cvss_v2:
            cvss_data = cvss_v2[0].get("cvssData", {})
            cvss_v2_score = cvss_data.get("baseScore")
            cvss_v2_vector = cvss_data.get("vectorString")
        
        cvss_v3 = metrics.get("cvssMetricV31", []) or metrics.get("cvssMetricV30", [])
        if cvss_v3:
            cvss_data = cvss_v3[0].get("cvssData", {})
            cvss_v3_score = cvss_data.get("baseScore")
            cvss_v3_vector = cvss_data.get("vectorString")
            severity = cvss_data.get("baseSeverity", "").upper()
        
        # Extract CWE IDs
        weaknesses = cve.get("weaknesses", [])
        cwe_ids = []
        for weakness in weaknesses:
            for desc in weakness.get("description", []):
                if desc.get("lang") == "en":
                    cwe_id = desc.get("value", "")
                    if cwe_id.startswith("CWE-"):
                        cwe_ids.append(cwe_id)
        
        # Extract affected products
        configurations = cve.get("configurations", [])
        affected_products = []
        for config in configurations:
            nodes = config.get("nodes", [])
            for node in nodes:
                cpe_match = node.get("cpeMatch", [])
                for match in cpe_match:
                    criteria = match.get("criteria", "")
                    if criteria:
                        affected_products.append(criteria)
        
        # Extract references
        references = cve.get("references", [])
        refs = [ref.get("url", "") for ref in references if ref.get("url")]
        
        return {
            "id": cve_id,
            "description": description,
            "cvss_v2_score": cvss_v2_score,
            "cvss_v2_vector": cvss_v2_vector,
            "cvss_v3_score": cvss_v3_score,
            "cvss_v3_vector": cvss_v3_vector,
            "severity": severity,
            "published_date": cve.get("published"),
            "last_modified_date": cve.get("lastModified"),
            "cwe_ids": cwe_ids,
            "affected_products": affected_products[:100],  # Limit to avoid huge JSON
            "references": refs[:50],  # Limit references
            "raw_data": json.dumps(vuln),  # Store full data as JSON string
        }

    async def download_attack_dataset(self) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Download MITRE ATT&CK dataset.
        
        Returns:
            Tuple of (techniques, tactics) lists
        """
        logger.info("Starting ATT&CK dataset download")
        
        # MITRE ATT&CK Enterprise data
        url = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
        
        try:
            response = await self._rate_limited_get(url)
            response.raise_for_status()
            data = response.json()
            
            techniques = []
            tactics = []
            
            objects = data.get("objects", [])
            for obj in objects:
                obj_type = obj.get("type", "")
                
                if obj_type == "x-mitre-tactic":
                    tactic = self._convert_attack_tactic(obj)
                    tactics.append(tactic)
                elif obj_type == "attack-pattern":
                    technique = self._convert_attack_technique(obj)
                    techniques.append(technique)
            
            logger.info(
                f"ATT&CK dataset download completed: "
                f"{len(techniques)} techniques, {len(tactics)} tactics"
            )
            
            return techniques, tactics
            
        except Exception as e:
            logger.error(f"Failed to download ATT&CK data: {e}")
            raise

    def _convert_attack_tactic(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Convert ATT&CK tactic object to our format."""
        external_refs = obj.get("external_references", [])
        tactic_id = None
        for ref in external_refs:
            if ref.get("source_name") == "mitre-attack":
                tactic_id = ref.get("external_id", "")
                break
        
        return {
            "id": tactic_id or obj.get("x_mitre_shortname", ""),
            "name": obj.get("name", ""),
            "description": obj.get("description", ""),
            "external_id": tactic_id,
            "kill_chain_phases": json.dumps([obj.get("x_mitre_shortname", "")]),
            "raw_data": json.dumps(obj),
        }

    def _convert_attack_technique(self, obj: dict[str, Any]) -> dict[str, Any]:
        """Convert ATT&CK technique object to our format."""
        external_refs = obj.get("external_references", [])
        technique_id = None
        for ref in external_refs:
            if ref.get("source_name") == "mitre-attack":
                technique_id = ref.get("external_id", "")
                break
        
        # Extract tactics
        kill_chain_phases = obj.get("kill_chain_phases", [])
        tactics_list = [phase.get("phase_name", "") for phase in kill_chain_phases]
        primary_tactic = tactics_list[0] if tactics_list else ""
        
        # Extract platforms
        x_mitre_platforms = obj.get("x_mitre_platforms", [])
        
        # Extract sub-techniques
        x_mitre_is_subtechnique = obj.get("x_mitre_is_subtechnique", False)
        parent_technique = None
        if x_mitre_is_subtechnique:
            # Extract parent from technique ID (e.g., T1055.001 -> T1055)
            if technique_id and "." in technique_id:
                parent_technique = technique_id.split(".")[0]
        
        return {
            "id": technique_id or "",
            "name": obj.get("name", ""),
            "description": obj.get("description", ""),
            "tactic": primary_tactic,
            "tactics": json.dumps(tactics_list),
            "platforms": json.dumps(x_mitre_platforms),
            "kill_chain_phases": json.dumps(tactics_list),
            "data_sources": json.dumps(obj.get("x_mitre_data_sources", [])),
            "detection": "",  # Would need to extract from related objects
            "mitigation": "",  # Would need to extract from related objects
            "references": json.dumps([ref.get("url", "") for ref in external_refs if ref.get("url")]),
            "sub_techniques": json.dumps([]),  # Would need to find related sub-techniques
            "parent_technique": parent_technique,
            "raw_data": json.dumps(obj),
        }

    async def download_owasp_dataset(self) -> list[dict[str, Any]]:
        """Download OWASP Testing Guide dataset.
        
        Note: OWASP doesn't have a public API, so this would need to scrape
        or use a pre-processed dataset. For now, returns empty list.
        """
        logger.info("Starting OWASP dataset download")
        logger.warning("OWASP dataset download not fully implemented - requires scraping or pre-processed data")
        
        # TODO: Implement OWASP data download
        # This would require either:
        # 1. Scraping the OWASP Testing Guide website
        # 2. Using a pre-processed JSON dataset
        # 3. Parsing the OWASP Testing Guide markdown files
        
        return []

