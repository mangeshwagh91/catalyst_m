"""
API endpoints for accessing loaded datasets.
"""

from fastapi import APIRouter, HTTPException
from typing import Optional
from app.core.data_loader import (
    data_loader,
    load_all_datasets,
    get_dataset_stats,
    PROTEIN_IDS,
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


@router.get("/status")
async def get_datasets_status():
    """Get status of all available datasets."""
    try:
        stats = get_dataset_stats()
        return {
            "status": "ok",
            "datasets": stats,
        }
    except Exception as e:
        logger.error(f"Error getting dataset status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load")
async def load_datasets():
    """Load all datasets into cache."""
    try:
        logger.info("Loading all datasets...")
        results = load_all_datasets()
        return {
            "status": "loaded",
            "datasets_loaded": list(results.keys()),
            "summary": results.get("summary"),
        }
    except Exception as e:
        logger.error(f"Error loading datasets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/proteins")
async def get_uniprot_proteins():
    """Get all loaded UniProt protein data."""
    proteins = data_loader.cache.get("uniprot_proteins")
    
    if not proteins:
        # Try to load if not already cached
        data_loader.fetch_all_uniprot_proteins()
        proteins = data_loader.cache.get("uniprot_proteins", {})
    
    return {
        "status": "ok",
        "count": len(proteins),
        "proteins": {
            name: {
                "id": PROTEIN_IDS[name],
                "cached": True,
                "data_preview": {
                    "accession": data.get("primaryAccession"),
                    "organism": data.get("organism", {}).get("commonName"),
                    "protein_name": data.get("proteinDescription", {}).get("recommendedName", {}).get("fullName", {}).get("value"),
                }
            }
            for name, data in proteins.items()
        },
        "proteins_list": list(PROTEIN_IDS.keys()),
    }


@router.get("/proteins/{protein_name}")
async def get_protein(protein_name: str):
    """Get specific protein data."""
    proteins = data_loader.cache.get("uniprot_proteins", {})
    
    if protein_name not in proteins:
        # Try to load single protein
        if protein_name not in PROTEIN_IDS:
            raise HTTPException(
                status_code=404,
                detail=f"Protein '{protein_name}' not found. Available: {list(PROTEIN_IDS.keys())}"
            )
        
        protein_id = PROTEIN_IDS[protein_name]
        data = data_loader.fetch_uniprot_protein(protein_id)
        
        if not data:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch protein: {protein_name}"
            )
        
        return {
            "status": "ok",
            "protein": protein_name,
            "data": data,
        }
    
    return {
        "status": "ok",
        "protein": protein_name,
        "data": proteins[protein_name],
    }


@router.get("/uniprotkb")
async def get_uniprotkb_data():
    """Get local UniProtKB dataset."""
    uniprotkb = data_loader.cache.get("local_uniprotkb")
    
    if not uniprotkb:
        # Try to load if not cached
        uniprotkb = data_loader.load_local_uniprotkb()
    
    if not uniprotkb:
        raise HTTPException(
            status_code=404,
            detail="UniProtKB data not available"
        )
    
    return {
        "status": "ok",
        "data": uniprotkb,
    }


@router.get("/materials-project/{formula}")
async def get_materials_project_data(formula: str = "Li"):
    """Get materials data from Materials Project API."""
    try:
        data = data_loader.fetch_materials_project_data(formula)
        
        if data is None:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch data for formula: {formula}"
            )
        
        return {
            "status": "ok",
            "formula": formula,
            "count": len(data) if isinstance(data, list) else 1,
            "data": data,
        }
    except Exception as e:
        logger.error(f"Error fetching Materials Project data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_datasets_summary():
    """Get summary of all datasets."""
    return {
        "status": "ok",
        "summary": get_dataset_stats(),
    }


@router.get("/available")
async def get_available_datasets():
    """Get list of available datasets."""
    return {
        "status": "ok",
        "datasets": {
            "uniprot_proteins": {
                "description": "Individual UniProt protein sequences and annotations",
                "endpoint": "/api/datasets/proteins",
                "available_proteins": list(PROTEIN_IDS.keys()),
            },
            "local_uniprotkb": {
                "description": "Local UniProtKB reviewed proteins dataset",
                "endpoint": "/api/datasets/uniprotkb",
                "file": "uniprotkb_AND_reviewed_true_2026_05_07.json",
            },
            "materials_project": {
                "description": "Materials Project API for material properties",
                "endpoint": "/api/datasets/materials-project/{formula}",
                "example": "/api/datasets/materials-project/Li",
            },
            "brenda": {
                "description": "BRENDA enzyme database (compressed)",
                "file": "brenda_2026_1.json.tar.gz",
                "status": "available_for_extraction",
            },
            "s2ef": {
                "description": "S2EF training dataset (200K records)",
                "file": "s2ef_train_200K.tar",
                "status": "available_for_extraction",
            },
        },
    }
