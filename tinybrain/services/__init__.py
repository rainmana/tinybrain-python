"""Security data downloaders for MITRE ATT&CK, NVD, CWE, OWASP."""

import json
from pathlib import Path
from typing import Optional

import httpx
from loguru import logger

from tinybrain.config import settings


class SecurityDataDownloader:
    """Download and manage security datasets."""

    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or settings.security_data_dir
        self.data_dir.mkdir(parents=True, exist_ok=True)

    async def download_mitre_attack(self) -> Path:
        """Download MITRE ATT&CK dataset."""
        url = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
        output_file = self.data_dir / "mitre_attack.json"

        logger.info("Downloading MITRE ATT&CK dataset...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            data = response.json()
            output_file.write_text(json.dumps(data, indent=2))

        logger.info(f"MITRE ATT&CK dataset saved to {output_file}")
        return output_file

    async def download_nvd_cves(self, year: Optional[int] = None) -> Path:
        """Download NVD CVE dataset."""
        if year:
            url = f"https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-{year}.json.gz"
        else:
            url = "https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-recent.json.gz"

        output_file = self.data_dir / f"nvd_cve_{year or 'recent'}.json"

        logger.info(f"Downloading NVD CVE dataset for {year or 'recent'}...")
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            # Note: In production, you'd decompress the .gz file
            # For now, we'll just save the response
            output_file.write_bytes(response.content)

        logger.info(f"NVD CVE dataset saved to {output_file}")
        return output_file

    async def download_cwe_list(self) -> Path:
        """Download CWE list."""
        url = "https://cwe.mitre.org/data/xml/cwec_latest.xml.zip"
        output_file = self.data_dir / "cwe_list.xml.zip"

        logger.info("Downloading CWE list...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            output_file.write_bytes(response.content)

        logger.info(f"CWE list saved to {output_file}")
        return output_file

    async def download_owasp_top10(self) -> Path:
        """Download OWASP Top 10 data."""
        # This is a placeholder - OWASP Top 10 doesn't have a direct JSON API
        # You would typically scrape or manually curate this data
        url = "https://raw.githubusercontent.com/OWASP/Top10/master/2021/docs/index.md"
        output_file = self.data_dir / "owasp_top10.md"

        logger.info("Downloading OWASP Top 10...")
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()

            output_file.write_text(response.text)

        logger.info(f"OWASP Top 10 saved to {output_file}")
        return output_file

    async def download_all(self) -> dict[str, Path]:
        """Download all security datasets."""
        results = {}

        try:
            results["mitre_attack"] = await self.download_mitre_attack()
        except Exception as e:
            logger.error(f"Failed to download MITRE ATT&CK: {e}")

        try:
            results["cwe"] = await self.download_cwe_list()
        except Exception as e:
            logger.error(f"Failed to download CWE: {e}")

        try:
            results["owasp"] = await self.download_owasp_top10()
        except Exception as e:
            logger.error(f"Failed to download OWASP Top 10: {e}")

        return results
