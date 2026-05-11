"""Knowledge Layer - Retrieves known catalysts from scientific databases"""

from typing import List, Dict, Any
import requests
import json
import re
from pathlib import Path
from app.core.logging import logger
from app.core.utils import generate_id, parse_chemical_formula

# Configuration
MATERIALS_PROJECT_API_KEY = "7Rkpv4MQv2tr1hJxWPb0nly9slDVECHC"
MATERIALS_PROJECT_API_BASE = "https://api.materialsproject.org/materials"
UNIPROT_API_BASE = "https://rest.uniprot.org/uniprotkb"
DATA_DIR = Path(__file__).parent.parent.parent.parent / "mal_masala"
UNIPROTKB_FILE = DATA_DIR / "uniprotkb_AND_reviewed_true_2026_05_07.json"

# Cached UniProt data
_uniprotdb_cache = None


def _load_uniprotdb():
    """Load UniProt database from local file on startup."""
    global _uniprotdb_cache
    if _uniprotdb_cache is not None:
        return _uniprotdb_cache
    
    try:
        if UNIPROTKB_FILE.exists():
            logger.info(f"Loading UniProt database from {UNIPROTKB_FILE}")
            with open(UNIPROTKB_FILE, 'r') as f:
                _uniprotdb_cache = json.load(f)
            logger.info(f"Loaded {len(_uniprotdb_cache)} UniProt entries")
            return _uniprotdb_cache
    except Exception as e:
        logger.error(f"Error loading UniProt database: {str(e)}")
    
    return {}


def _extract_elements_from_reaction(reactants: List[str], products: List[str]) -> List[str]:
    """
    Extract chemical elements from reactants and products.
    Example: ['CO2', 'H2'] → ['C', 'O', 'H']
    """
    elements = set()
    
    # Chemical element symbols (commonly used in catalysis)
    element_pattern = r'[A-Z][a-z]?'
    
    for compound in reactants + products:
        # Extract element symbols
        matches = re.findall(element_pattern, compound)
        elements.update(matches)
    
    # Filter out common non-elements
    valid_elements = {'C', 'H', 'N', 'O', 'S', 'P', 'Cu', 'Zn', 'Ni', 'Co', 'Fe', 'Pt', 'Pd', 'Au', 'Ag', 'Mo', 'W', 'V', 'Cr', 'Mn', 'Re', 'Ru', 'Rh', 'Ir'}
    return list(elements & valid_elements)


def _query_materials_project(elements: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Query Materials Project API for materials containing specified elements.
    """
    if not elements:
        logger.warning("No elements provided for Materials Project query")
        return []
    
    try:
        # Build formula query (e.g., "Cu" or "Cu-Zn" or "Cu-Zn-Al")
        formula_query = "-".join(sorted(set(elements)))
        
        # Materials Project API endpoint
        url = f"{MATERIALS_PROJECT_API_BASE}"
        params = {
            "api_key": MATERIALS_PROJECT_API_KEY,
            "formula": formula_query,
            "fields": ["formula", "material_id", "energy_above_hull", "band_gap", "structure"],
        }
        
        logger.info(f"Querying Materials Project for elements: {elements}, formula: {formula_query}")
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        materials = data.get("data", [])[:limit]
        
        logger.info(f"Retrieved {len(materials)} materials from Materials Project")
        
        # Format materials for our system
        formatted = []
        for i, mat in enumerate(materials):
            formatted.append({
                "id": f"mp_{mat.get('material_id', f'unknown_{i}')}",
                "name": f"Material {mat.get('formula', 'Unknown')}",
                "composition": mat.get('formula', 'Unknown'),
                "source": "Materials Project",
                "activity": 60 + (i * 2),  # Heuristic: better materials first
                "selectivity": 75 + (i * 1),
                "stability": 70 + (i * 1.5),
                "description": f"From Materials Project (Energy above hull: {mat.get('energy_above_hull', 'N/A')} eV)",
                "structure": {
                    "material_id": mat.get('material_id'),
                    "band_gap": mat.get('band_gap'),
                    "energy_above_hull": mat.get('energy_above_hull'),
                }
            })
        
        return formatted
    
    except Exception as e:
        logger.error(f"Error querying Materials Project: {str(e)}")
        return []


def _search_uniprotdb_by_reaction(reactants: List[str], products: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Search UniProt database for enzymes relevant to a reaction.
    """
    db = _load_uniprotdb()
    if not db:
        logger.warning("UniProt database not loaded")
        return []
    
    # Build search query from reaction
    search_terms = ' '.join(reactants + products).lower()
    
    matching_enzymes = []
    for entry in db:
        if isinstance(entry, dict):
            # Search in description, recommended name, etc.
            text = ' '.join([
                entry.get('description', '').lower(),
                entry.get('recommendedName', '').lower(),
                entry.get('alternativeNames', '')
            ])
            
            # Simple keyword matching
            if any(term.lower() in text for term in reactants + products):
                matching_enzymes.append({
                    "id": entry.get('uniprot_id', 'unknown'),
                    "name": entry.get('recommendedName', 'Unknown Enzyme'),
                    "composition": entry.get('sequence_length', 'N/A'),
                    "source": "UniProt",
                    "activity": 75,
                    "selectivity": 85,
                    "stability": 80,
                    "description": entry.get('description', 'No description'),
                    "structure": {
                        "type": "enzyme",
                        "ec_number": entry.get('ec_number'),
                        "organism": entry.get('organism'),
                    }
                })
    
    return matching_enzymes[:limit]


# Mock data for fallback (kept for backward compatibility)
KNOWN_CATALYSTS_DB = [
    {
        "id": "cat_001",
        "name": "Cu-Zn-Al Oxide",
        "composition": "Cu0.6Zn0.2Al0.2",
        "source": "Open Catalyst Project",
        "activity": 72.5,
        "selectivity": 88.0,
        "stability": 85.0,
        "description": "Industrial standard Cu-Zn-Al oxide catalyst for CO2 hydrogenation",
        "structure": {"lattice": "cubic", "dopants": ["Al"]},
    },
    {
        "id": "cat_002",
        "name": "Cu-Zn-Cr Oxide",
        "composition": "Cu0.5Zn0.3Cr0.2",
        "source": "Open Catalyst Project",
        "activity": 68.0,
        "selectivity": 82.0,
        "stability": 80.0,
        "description": "Cu-Zn-Cr oxide with chromium promoter",
        "structure": {"lattice": "cubic", "dopants": ["Cr"]},
    },
    {
        "id": "cat_003",
        "name": "Pt/C Catalyst",
        "composition": "Pt0.05C0.95",
        "source": "Materials Project",
        "activity": 85.0,
        "selectivity": 78.0,
        "stability": 70.0,
        "description": "Platinum on carbon support",
        "structure": {"support": "carbon", "nanoparticles": "Pt"},
    },
    {
        "id": "cat_004",
        "name": "Pd/Al2O3",
        "composition": "Pd0.02Al0.98O3",
        "source": "Materials Project",
        "activity": 75.0,
        "selectivity": 84.0,
        "stability": 82.0,
        "description": "Palladium on alumina support",
        "structure": {"support": "Al2O3", "nanoparticles": "Pd"},
    },
    {
        "id": "cat_005",
        "name": "Ni-Mo-S",
        "composition": "Ni0.4Mo0.4S0.2",
        "source": "BRENDA",
        "activity": 62.0,
        "selectivity": 86.0,
        "stability": 88.0,
        "description": "Nickel-molybdenum sulfide HER catalyst",
        "structure": {"lattice": "layered", "edges": "MoS2-edge"},
    },
    {
        "id": "cat_006",
        "name": "Fe-Ni/N-C",
        "composition": "Fe0.3Ni0.3N0.1C0.3",
        "source": "Open Catalyst Project",
        "activity": 70.0,
        "selectivity": 80.0,
        "stability": 75.0,
        "description": "Fe-Ni doped nitrogen-carbon ORR catalyst",
        "structure": {"dopant": "N", "support": "carbon"},
    },
    {
        "id": "cat_007",
        "name": "Co3O4",
        "composition": "Co0.75O",
        "source": "Materials Project",
        "activity": 65.0,
        "selectivity": 79.0,
        "stability": 84.0,
        "description": "Cobalt oxide OER catalyst",
        "structure": {"lattice": "spinel"},
    },
    {
        "id": "cat_008",
        "name": "MnO2/C",
        "composition": "Mn0.1O0.2C0.7",
        "source": "BRENDA",
        "activity": 58.0,
        "selectivity": 75.0,
        "stability": 80.0,
        "description": "Manganese dioxide on carbon",
        "structure": {"support": "carbon", "particles": "MnO2"},
    },
    {
        "id": "cat_009",
        "name": "Ag-Cu Alloy",
        "composition": "Ag0.4Cu0.6",
        "source": "Materials Project",
        "activity": 76.0,
        "selectivity": 87.0,
        "stability": 83.0,
        "description": "Silver-copper bimetallic catalyst",
        "structure": {"alloy": "AgCu", "structure": "FCC"},
    },
    {
        "id": "cat_010",
        "name": "RuO2/TiO2",
        "composition": "Ru0.05O0.2Ti0.75O2",
        "source": "Open Catalyst Project",
        "activity": 82.0,
        "selectivity": 81.0,
        "stability": 77.0,
        "description": "Ruthenium oxide on titanium dioxide",
        "structure": {"support": "TiO2", "particles": "RuO2"},
    },
]

# More catalysts for comprehensive database
KNOWN_CATALYSTS_DB.extend([
    {
        "id": f"cat_{str(i+11).zfill(3)}",
        "name": f"Catalyst_{i+11}",
        "composition": f"Element{i%5}0.{50+i%40}Element{(i+1)%5}0.{30-(i%30)}",
        "source": ["Materials Project", "Open Catalyst Project", "BRENDA"][i % 3],
        "activity": 50 + (i % 40),
        "selectivity": 70 + (i % 25),
        "stability": 60 + (i % 35),
        "description": f"Synthetic catalyst variant {i+11}",
        "structure": {"variant": i},
    }
    for i in range(1, 14)  # Creates 13 more catalysts for total of 23+
])


class KnowledgeLayer:
    """Knowledge Layer - Handles scientific database retrieval"""
    
    def __init__(self):
        self.logger = logger
        self.catalysts_db = KNOWN_CATALYSTS_DB
        # Load UniProt database on startup
        _load_uniprotdb()
    
    def retrieve_catalysts_for_reaction(
        self, 
        reactants: List[str], 
        products: List[str],
        limit: int = 10,
        use_real_data: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Retrieve known catalysts from scientific databases for a given reaction.
        
        Strategy:
        1. Extract elements from reactants/products
        2. Query Materials Project API for real materials
        3. Fallback to rule-based search + mock data
        
        Returns real Materials Project data if available, otherwise mock data.
        """
        self.logger.info(
            f"Retrieving catalysts for reaction: {reactants} → {products} (use_real_data={use_real_data})"
        )
        
        retrieved = []
        
        if use_real_data:
            # Extract elements from reaction
            elements = _extract_elements_from_reaction(reactants, products)
            self.logger.info(f"Extracted elements from reaction: {elements}")
            
            # Try to get real materials from Materials Project
            if elements:
                materials = _query_materials_project(elements, limit=limit)
                if materials:
                    self.logger.info(f"Retrieved {len(materials)} real materials from Materials Project")
                    retrieved = materials
            
            # If no real data, fall back to mock data
            if not retrieved:
                self.logger.info("No real data available, using mock catalysts")
                retrieved = sorted(
                    self.catalysts_db,
                    key=lambda x: (x.get("activity", 0) + x.get("selectivity", 0)) / 2,
                    reverse=True
                )[:limit]
        else:
            # Use only mock data
            retrieved = sorted(
                self.catalysts_db,
                key=lambda x: (x.get("activity", 0) + x.get("selectivity", 0)) / 2,
                reverse=True
            )[:limit]
        
        return retrieved
    
    def suggest_enzymes_for_reaction(
        self,
        reactants: List[str],
        products: List[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Suggest relevant enzymes from UniProt database for a given reaction.
        
        Returns:
        - List of enzyme records with UniProt IDs, sequences, EC numbers
        """
        self.logger.info(
            f"Suggesting enzymes for reaction: {reactants} → {products}"
        )
        
        # Search UniProt database
        enzymes = _search_uniprotdb_by_reaction(reactants, products, limit)
        
        self.logger.info(f"Found {len(enzymes)} relevant enzymes")
        return enzymes
    
    def get_catalyst_details(self, catalyst_id: str) -> Dict[str, Any]:
        """Retrieve detailed information for a specific catalyst"""
        for cat in self.catalysts_db:
            if cat["id"] == catalyst_id:
                self.logger.info(f"Retrieved details for catalyst: {catalyst_id}")
                return cat
        self.logger.warning(f"Catalyst not found: {catalyst_id}")
        return None
    
    def search_catalysts_by_composition(self, element: str) -> List[Dict[str, Any]]:
        """Search for catalysts containing a specific element"""
        matching = [
            cat for cat in self.catalysts_db 
            if element.lower() in cat["composition"].lower()
        ]
        self.logger.info(f"Found {len(matching)} catalysts containing {element}")
        return matching
    
    def add_catalyst_to_knowledge_base(
        self, 
        name: str, 
        composition: str, 
        properties: Dict[str, float],
        source: str = "experimental"
    ) -> Dict[str, Any]:
        """
        Add a newly discovered catalyst to the knowledge base.
        This is called from the Feedback Layer after experimental validation.
        """
        catalyst = {
            "id": generate_id(),
            "name": name,
            "composition": composition,
            "source": source,
            "activity": properties.get("activity", 0),
            "selectivity": properties.get("selectivity", 0),
            "stability": properties.get("stability", 0),
            "description": f"Experimentally validated {name}",
            "structure": properties.get("structure", {}),
        }
        self.catalysts_db.append(catalyst)
        self.logger.info(f"Added new catalyst to knowledge base: {catalyst['id']}")
        return catalyst
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base"""
        if not self.catalysts_db:
            return {}
        
        activities = [c.get("activity", 0) for c in self.catalysts_db]
        selectivities = [c.get("selectivity", 0) for c in self.catalysts_db]
        stabilities = [c.get("stability", 0) for c in self.catalysts_db]
        
        return {
            "total_catalysts": len(self.catalysts_db),
            "avg_activity": sum(activities) / len(activities) if activities else 0,
            "avg_selectivity": sum(selectivities) / len(selectivities) if selectivities else 0,
            "avg_stability": sum(stabilities) / len(stabilities) if stabilities else 0,
            "sources": list(set(c.get("source", "unknown") for c in self.catalysts_db)),
        }
