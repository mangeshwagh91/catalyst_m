"""API Routes - Visualization endpoints"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import VisualizationDataSchema, DashboardStatsSchema
from app.layers.visualization_layer import VisualizationLayer
from app.core.logging import logger
from app.api.dependencies import get_current_user

router = APIRouter(
    prefix="/api/visualization",
    tags=["visualization"],
    dependencies=[Depends(get_current_user)]
)

visualization_layer = VisualizationLayer()


class StructureRequest(BaseModel):
    catalyst: Dict[str, Any]
    prediction: Optional[Dict[str, Any]] = None

class PredictionsListRequest(BaseModel):
    predictions: List[Dict[str, Any]]

class EnergyDiagramRequest(BaseModel):
    catalyst_id: str

class DashboardSummaryRequest(BaseModel):
    reaction_id: str
    predictions: List[Dict[str, Any]]


@router.post("/catalyst-structure")
def format_catalyst_for_viewer(
    request: StructureRequest,
    db: Session = Depends(get_db)
):
    """
    Format catalyst data for interactive 3D/2D molecular viewer.
    """
    logger.info(f"Formatting catalyst {request.catalyst.get('name')} for visualization")
    
    try:
        formatted = visualization_layer.format_catalyst_for_viewer(request.catalyst, request.prediction)
        return formatted
    except Exception as e:
        logger.error(f"Error formatting catalyst: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/performance-plot")
def create_performance_plot(
    request: PredictionsListRequest,
    db: Session = Depends(get_db)
):
    """
    Create Plotly-compatible data for performance comparison plot.
    """
    logger.info(f"Creating performance plot for {len(request.predictions)} catalysts")
    
    try:
        plot_data = visualization_layer.create_performance_plot_data(request.predictions)
        return {
            "type": "plotly",
            "plot": plot_data,
        }
    except Exception as e:
        logger.error(f"Error creating plot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ranking-table")
def create_ranking_table(
    request: PredictionsListRequest,
    db: Session = Depends(get_db)
):
    """
    Create tabular data for ranking display.
    """
    logger.info(f"Creating ranking table for {len(request.predictions)} catalysts")
    
    try:
        table_data = visualization_layer.create_ranking_table_data(request.predictions)
        return table_data
    except Exception as e:
        logger.error(f"Error creating table: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/energy-diagram")
def get_reaction_energy_diagram(
    request: EnergyDiagramRequest,
    db: Session = Depends(get_db)
):
    """
    Get reaction energy profile diagram for a catalyst.
    """
    logger.info(f"Creating energy diagram for catalyst {request.catalyst_id}")
    
    try:
        diagram = visualization_layer.create_reaction_energy_diagram(request.catalyst_id)
        return diagram
    except Exception as e:
        logger.error(f"Error creating energy diagram: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/dashboard-summary")
def get_dashboard_summary(
    request: DashboardSummaryRequest,
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for the main dashboard.
    """
    logger.info(f"Creating dashboard summary for reaction {request.reaction_id}")
    
    try:
        summary = visualization_layer.get_dashboard_summary(request.reaction_id, request.predictions)
        return summary
    except Exception as e:
        logger.error(f"Error creating dashboard summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-formats")
def get_supported_export_formats(db: Session = Depends(get_db)):
    """Get list of supported export formats for catalysts"""
    return {
        "molecular_formats": [
            {"format": "PDB", "description": "Protein Data Bank format", "extension": ".pdb"},
            {"format": "CIF", "description": "Crystallographic Information File", "extension": ".cif"},
            {"format": "XYZ", "description": "XYZ coordinate format", "extension": ".xyz"},
            {"format": "POSCAR", "description": "VASP format", "extension": ".vasp"},
            {"format": "SMILES", "description": "Simplified Molecular Input Line Entry System", "extension": ".smi"},
        ],
        "data_formats": [
            {"format": "JSON", "description": "JavaScript Object Notation", "extension": ".json"},
            {"format": "CSV", "description": "Comma-Separated Values", "extension": ".csv"},
            {"format": "Excel", "description": "Microsoft Excel", "extension": ".xlsx"},
        ],
    }
