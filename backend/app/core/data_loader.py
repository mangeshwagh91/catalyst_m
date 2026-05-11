"""
Data loader module for fetching and caching datasets from multiple sources.
Supports: UniProt, Materials Project, Local files (BRENDA, S2EF).
"""

import json
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from functools import lru_cache
import requests
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Configuration
MATERIALS_PROJECT_API_KEY = "7Rkpv4MQv2tr1hJxWPb0nly9slDVECHC"
UNIPROT_API_BASE = "https://rest.uniprot.org/uniprotkb"
MATERIALS_PROJECT_API_BASE = "https://api.materialsproject.org/materials"

# Dataset file paths
DATA_DIR = Path(__file__).parent.parent.parent.parent / "mal_masala"
BRENDA_FILE = DATA_DIR / "brenda_2026_1.json.tar.gz"
S2EF_FILE = DATA_DIR / "s2ef_train_200K.tar"
UNIPROTKB_FILE = DATA_DIR / "uniprotkb_AND_reviewed_true_2026_05_07.json"

# UniProt protein IDs to load
PROTEIN_IDS = {
    "alcohol_dehydrogenase": "P00326",
    "cytochrome_p450": "P20853",
    "cellulase": "P26222",
    "lipase": "P54315",
    "aldehyde_dehydrogenase": "P23883",
}


class DataLoader:
    """Load and cache datasets from multiple sources."""
    
    def __init__(self):
        self.cache = {}
        self.last_updated = {}
    
    def fetch_uniprot_protein(self, protein_id: str) -> Optional[Dict[str, Any]]:
        """Fetch protein data from UniProt API."""
        try:
            url = f"{UNIPROT_API_BASE}/{protein_id}.json"
            logger.info(f"Fetching UniProt data: {protein_id} from {url}")
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched UniProt protein: {protein_id}")
            return data
        except Exception as e:
            logger.error(f"Error fetching UniProt protein {protein_id}: {str(e)}")
            return None
    
    def fetch_all_uniprot_proteins(self) -> Dict[str, Dict[str, Any]]:
        """Fetch all protein data from UniProt."""
        proteins = {}
        for name, protein_id in PROTEIN_IDS.items():
            data = self.fetch_uniprot_protein(protein_id)
            if data:
                proteins[name] = data
        
        self.cache["uniprot_proteins"] = proteins
        self.last_updated["uniprot_proteins"] = datetime.now().isoformat()
        return proteins
    
    def fetch_materials_project_data(self, formula: str = "Li") -> Optional[List[Dict]]:
        """Fetch materials data from Materials Project API."""
        try:
            params = {
                "API_KEY": MATERIALS_PROJECT_API_KEY,
                "criteria": json.dumps({"formula": formula}),
            }
            logger.info(f"Fetching Materials Project data for formula: {formula}")
            
            response = requests.get(
                MATERIALS_PROJECT_API_BASE,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            logger.info(f"Successfully fetched Materials Project data for: {formula}")
            return data.get("response", [])
        except Exception as e:
            logger.error(f"Error fetching Materials Project data: {str(e)}")
            return None
    
    def load_local_uniprotkb(self) -> Optional[Dict[str, Any]]:
        """Load UniProtKB dataset from local JSON file."""
        try:
            if not UNIPROTKB_FILE.exists():
                logger.warning(f"UniProtKB file not found: {UNIPROTKB_FILE}")
                return None
            
            logger.info(f"Loading local UniProtKB data: {UNIPROTKB_FILE}")
            with open(UNIPROTKB_FILE, 'r', encoding='utf-8') as f:
                # Load first 1000 entries to avoid memory issues
                data = json.load(f)
                if isinstance(data, list):
                    summary = {
                        "total_entries": len(data),
                        "sample_entries": data[:100],  # First 100 entries
                        "source": "UniProtKB Reviewed",
                        "file": str(UNIPROTKB_FILE),
                    }
                else:
                    summary = data
                
                self.cache["local_uniprotkb"] = summary
                self.last_updated["local_uniprotkb"] = datetime.now().isoformat()
                logger.info(f"Loaded {summary.get('total_entries', 'unknown')} entries from UniProtKB")
                return summary
        except Exception as e:
            logger.error(f"Error loading local UniProtKB: {str(e)}")
            return None
    
    def get_dataset_summary(self) -> Dict[str, Any]:
        """Get summary of all available datasets."""
        summary = {
            "timestamp": datetime.now().isoformat(),
            "datasets": {
                "uniprot_proteins": {
                    "status": "cached" if "uniprot_proteins" in self.cache else "not_loaded",
                    "count": len(self.cache.get("uniprot_proteins", {})),
                    "last_updated": self.last_updated.get("uniprot_proteins"),
                    "proteins": list(PROTEIN_IDS.keys()),
                },
                "local_uniprotkb": {
                    "status": "cached" if "local_uniprotkb" in self.cache else "not_loaded",
                    "file": str(UNIPROTKB_FILE),
                    "exists": UNIPROTKB_FILE.exists(),
                    "last_updated": self.last_updated.get("local_uniprotkb"),
                },
                "materials_project": {
                    "status": "available",
                    "api_key_configured": bool(MATERIALS_PROJECT_API_KEY),
                    "base_url": MATERIALS_PROJECT_API_BASE,
                },
                "brenda": {
                    "file": str(BRENDA_FILE),
                    "exists": BRENDA_FILE.exists(),
                    "note": "Compressed archive - extract before use",
                },
                "s2ef": {
                    "file": str(S2EF_FILE),
                    "exists": S2EF_FILE.exists(),
                    "note": "Large training dataset - 200K records",
                },
            },
            "cache": {
                "total_cached": len(self.cache),
                "cached_datasets": list(self.cache.keys()),
            }
        }
        return summary


# Global data loader instance
data_loader = DataLoader()


def load_all_datasets() -> Dict[str, Any]:
    """Load all available datasets."""
    logger.info("Starting to load all datasets...")
    
    results = {}
    
    # Load UniProt proteins
    logger.info("Loading UniProt proteins...")
    proteins = data_loader.fetch_all_uniprot_proteins()
    results["uniprot_proteins"] = proteins
    
    # Load local UniProtKB
    logger.info("Loading local UniProtKB...")
    uniprotkb = data_loader.load_local_uniprotkb()
    results["local_uniprotkb"] = uniprotkb
    
    # Get summary
    results["summary"] = data_loader.get_dataset_summary()
    
    logger.info("Dataset loading completed")
    return results


def get_cached_dataset(dataset_name: str) -> Optional[Dict[str, Any]]:
    """Get cached dataset by name."""
    return data_loader.cache.get(dataset_name)


def get_dataset_stats() -> Dict[str, Any]:
    """Get statistics about loaded datasets."""
    return data_loader.get_dataset_summary()
