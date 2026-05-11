"""API Routes - Experiments and feedback endpoints"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import ExperimentCreate, ExperimentResponse, DiscrepancyAnalysisSchema
from app.models.models import Experiment, ModelVersion
from app.layers.feedback_layer import FeedbackLearningLayer
from app.layers.prediction_layer import PredictionLayer
from app.core.logging import logger

router = APIRouter(prefix="/api/experiments", tags=["experiments"])

# Initialize layers - FeedbackLearningLayer with access to PredictionLayer for training
prediction_layer = PredictionLayer()
feedback_layer = FeedbackLearningLayer(prediction_layer=prediction_layer)


class LogResultsRequest(BaseModel):
    reaction_id: str
    catalyst_id: str
    measured_properties: Dict[str, float]
    predicted_properties: Dict[str, float]
    researcher_name: Optional[str] = None
    notes: Optional[str] = None


class ExportRequest(BaseModel):
    reaction_id: str
    catalyst_ids: List[str]
    export_format: str = "json"


class RetrainingRequest(BaseModel):
    new_experiments: List[Dict[str, Any]]
    trigger_reason: str = "new_data"


@router.post("/log-results")
def log_experimental_results(
    request: LogResultsRequest,
    db: Session = Depends(get_db)
):
    """
    Log experimental results and trigger analysis, then persist to DB.
    """
    logger.info(f"Logging experimental results for catalyst {request.catalyst_id}")
    
    try:
        experiment_data = feedback_layer.log_experiment(
            reaction_id=request.reaction_id,
            catalyst_id=request.catalyst_id,
            measured_properties=request.measured_properties,
            predicted_properties=request.predicted_properties,
            researcher_name=request.researcher_name,
            notes=request.notes
        )
        
        # Persist to database
        # NOTE: feedback_layer returns deviations nested as:
        #   experiment_data["deviations"]["activity"]["absolute_deviation"]
        deviations = experiment_data.get("deviations", {})
        db_experiment = Experiment(
            id=str(uuid.uuid4()),
            reaction_id=request.reaction_id,
            catalyst_id=request.catalyst_id,
            measured_activity=request.measured_properties.get("activity"),
            measured_selectivity=request.measured_properties.get("selectivity"),
            measured_stability=request.measured_properties.get("stability"),
            predicted_activity=request.predicted_properties.get("activity"),
            predicted_selectivity=request.predicted_properties.get("selectivity"),
            predicted_stability=request.predicted_properties.get("stability"),
            activity_deviation=deviations.get("activity", {}).get("percent_deviation"),
            selectivity_deviation=deviations.get("selectivity", {}).get("percent_deviation"),
            stability_deviation=deviations.get("stability", {}).get("percent_deviation"),
            status=experiment_data.get("status", "normal"),
            hypothesis=experiment_data.get("hypothesis"),
            notes=request.notes,
            researcher_name=request.researcher_name,
            tested_at=datetime.now()
        )
        db.add(db_experiment)
        db.commit()
        db.refresh(db_experiment)
        
        return {
            "success": True,
            "experiment": db_experiment,
            "recommendation": {
                "trigger_retraining": db_experiment.status in ["anomaly", "verified_outperformer"],
                "reason": "Significant deviation detected" if db_experiment.status == "anomaly" else "Strong outperformance",
            },
        }
    except Exception as e:
        logger.error(f"Error logging experimental results: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/flag-outliers")
def flag_experimental_outliers(
    experiments: List[Dict[str, Any]],
    db: Session = Depends(get_db)
):
    """
    Identify and flag experimental outliers for human review.
    """
    logger.info(f"Flagging outliers from {len(experiments)} experiments")
    
    try:
        outliers = feedback_layer.flag_outliers(experiments)
        return outliers
    except Exception as e:
        logger.error(f"Error flagging outliers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-retraining")
def trigger_model_retraining(
    request: RetrainingRequest,
    db: Session = Depends(get_db)
):
    """
    Trigger model retraining and persist version info.
    """
    logger.info(f"Triggering model retraining ({request.trigger_reason})")
    
    try:
        job = feedback_layer.trigger_model_retraining(
            new_experiments=request.new_experiments,
            trigger_reason=request.trigger_reason
        )
        
        # Persist model version info
        db_version = ModelVersion(
            id=str(uuid.uuid4()),
            version=job.get("version", "v" + str(uuid.uuid4())[:8]),
            model_type="GNN",
            status="active",
            trigger_reason=request.trigger_reason,
            training_samples=len(request.new_experiments),
            training_started_at=datetime.now()
        )
        db.add(db_version)
        db.commit()
        db.refresh(db_version)
        
        return {
            "success": True,
            "retraining_job": job,
            "model_version": db_version,
            "next_steps": f"Monitor retraining progress at /api/experiments/retraining-status/{db_version.id}",
        }
    except Exception as e:
        logger.error(f"Error triggering retraining: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retraining-history")
def get_retraining_history(db: Session = Depends(get_db)):
    """Get complete history of model retraining events from DB"""
    logger.info("Retrieving retraining history")
    
    history = db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()
    return {
        "total_retraining_events": len(history),
        "history": history,
        "status": "up_to_date" if history else "no_retraining_yet",
    }


@router.post("/export")
def export_candidates_for_testing(
    request: ExportRequest,
    db: Session = Depends(get_db)
):
    """
    Export top candidates for experimental synthesis and testing.
    """
    logger.info(f"Exporting {len(request.catalyst_ids)} candidates in {request.export_format} format")
    
    try:
        export_data = {
            "reaction_id": request.reaction_id,
            "num_catalysts": len(request.catalyst_ids),
            "export_format": request.export_format,
            "catalyst_ids": request.catalyst_ids,
            "export_timestamp": datetime.now().isoformat(),
            "download_link": f"/api/experiments/download-export/{request.reaction_id}",
        }
        
        return {
            "success": True,
            "export": export_data,
        }
    except Exception as e:
        logger.error(f"Error exporting candidates: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
def get_experiment_summary(
    reaction_id: str = None,
    db: Session = Depends(get_db)
):
    """Get summary of all experiments and feedback loop status from DB"""
    logger.info(f"Retrieving experiment summary")
    
    query = db.query(Experiment)
    if reaction_id:
        query = query.filter(Experiment.reaction_id == reaction_id)
        
    total_experiments = query.count()
    
    experiments_by_status = {
        "normal": query.filter(Experiment.status == "normal").count(),
        "verified_outperformer": query.filter(Experiment.status == "verified_outperformer").count(),
        "anomaly": query.filter(Experiment.status == "anomaly").count(),
    }
    
    retrainings_count = db.query(ModelVersion).count()
    
    return {
        "total_experiments": total_experiments,
        "experiments_by_status": experiments_by_status,
        "model_retrainings": retrainings_count,
        "last_update": datetime.now().isoformat(),
    }

