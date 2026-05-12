"""API Routes - Experiments and feedback endpoints"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, EmailStr
from sqlalchemy import or_
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import ExperimentCreate, ExperimentResponse, DiscrepancyAnalysisSchema
from app.models.models import Catalyst, Experiment, ModelVersion, Reaction, User
from app.layers.feedback_layer import FeedbackLearningLayer
from app.layers.prediction_layer import PredictionLayer
from app.core.logging import logger
from app.api.dependencies import get_current_user

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


class ShareExperimentRequest(BaseModel):
    email: EmailStr


class ExportRequest(BaseModel):
    reaction_id: str
    catalyst_ids: List[str]
    export_format: str = "json"


class RetrainingRequest(BaseModel):
    new_experiments: List[Dict[str, Any]]
    trigger_reason: str = "new_data"
    use_all_quality_experiments: bool = False  # If True, use all quality experiments from DB


@router.post("/log-results")
def log_experimental_results(
    request: LogResultsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Log experimental results and trigger analysis, then persist to DB.
    """
    logger.info(f"Logging experimental results for catalyst {request.catalyst_id} (user: {current_user.email})")

    db_reaction = db.query(Reaction).filter(
        Reaction.id == request.reaction_id,
        Reaction.creator_id == current_user.id
    ).first()
    if not db_reaction:
        raise HTTPException(status_code=403, detail="Not authorized to log results for this reaction")

    db_catalyst = db.query(Catalyst).filter(
        Catalyst.id == request.catalyst_id,
        Catalyst.reaction_id == request.reaction_id
    ).first()
    if not db_catalyst:
        raise HTTPException(status_code=404, detail="Catalyst not found for this reaction")

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
            creator_id=current_user.id,
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


@router.get("/")
def list_experiments(
    skip: int = 0,
    limit: int = 20,
    reaction_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List experiments owned by or shared with the current user."""
    logger.info(f"Listing experiments for user: {current_user.email} (skip={skip}, limit={limit})")

    query = db.query(Experiment).filter(
        or_(
            Experiment.creator_id == current_user.id,
            Experiment.shared_with.contains([current_user.id])
        )
    )
    if reaction_id:
        query = query.filter(Experiment.reaction_id == reaction_id)

    total = query.count()
    experiments = query.order_by(Experiment.logged_at.desc()).offset(skip).limit(limit).all()

    return {
        "experiments": [ExperimentResponse.model_validate(exp) for exp in experiments],
        "total": total,
    }


@router.get("/{experiment_id}")
def get_experiment(
    experiment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve a single experiment if owned by or shared with the current user."""
    logger.info(f"Retrieving experiment {experiment_id} for user: {current_user.email}")

    db_experiment = db.query(Experiment).filter(
        Experiment.id == experiment_id,
        or_(
            Experiment.creator_id == current_user.id,
            Experiment.shared_with.contains([current_user.id])
        )
    ).first()

    if not db_experiment:
        raise HTTPException(status_code=404, detail="Experiment not found or not authorized")

    return ExperimentResponse.model_validate(db_experiment)


@router.post("/{experiment_id}/share")
def share_experiment(
    experiment_id: str,
    request: ShareExperimentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Share an experiment with another user by email."""
    logger.info(f"User {current_user.email} sharing experiment {experiment_id} with {request.email}")

    experiment = db.query(Experiment).filter(Experiment.id == experiment_id).first()
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    if experiment.creator_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the experiment owner can share it")

    target_user = db.query(User).filter(User.email == request.email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")

    shared_with = experiment.shared_with or []
    if target_user.id not in shared_with:
        shared_with.append(target_user.id)
        experiment.shared_with = shared_with
        db.add(experiment)
        db.commit()
        db.refresh(experiment)

    return {
        "experiment_id": experiment.id,
        "shared_with": experiment.shared_with,
        "shared_with_user": {
            "id": target_user.id,
            "email": target_user.email,
        },
    }


@router.post("/flag-outliers")
def flag_experimental_outliers(
    experiments: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Identify and flag experimental outliers for human review.
    """
    logger.info(f"Flagging outliers from {len(experiments)} experiments (user: {current_user.email})")
    
    try:
        outliers = feedback_layer.flag_outliers(experiments)
        return outliers
    except Exception as e:
        logger.error(f"Error flagging outliers: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-retraining")
def trigger_model_retraining(
    request: RetrainingRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger model retraining with before/after evaluation metrics.
    
    The endpoint:
    1. Queries quality experiments from DB if use_all_quality_experiments=True
    2. Evaluates model performance BEFORE retraining
    3. Trains the model on quality-filtered experiments
    4. Evaluates model performance AFTER retraining
    5. Computes MAE and R² improvements
    6. Displays results with before-vs-after bar chart data
    """
    logger.info(f"Triggering model retraining ({request.trigger_reason})")
    
    try:
        # If requesting all quality experiments from DB, fetch them
        if request.use_all_quality_experiments:
            logger.info("Fetching all quality experiments from database")
            db_experiments = db.query(Experiment).filter(
                Experiment.creator_id == current_user.id,
                Experiment.status.in_(["normal", "verified_outperformer"])
            ).all()
            # Convert DB experiments to dict format for feedback layer
            request.new_experiments = [
                {
                    "id": exp.id,
                    "reaction_id": exp.reaction_id,
                    "catalyst_id": exp.catalyst_id,
                    "status": exp.status,
                    "measured_activity": exp.measured_activity,
                    "measured_selectivity": exp.measured_selectivity,
                    "measured_stability": exp.measured_stability,
                    "predicted_activity": exp.predicted_activity,
                    "predicted_selectivity": exp.predicted_selectivity,
                    "predicted_stability": exp.predicted_stability,
                }
                for exp in db_experiments
            ]
            logger.info(f"Loaded {len(request.new_experiments)} quality experiments from DB")
        
        # Filter to get quality experiments for evaluation (split or use same set)
        quality_exps = [
            exp for exp in request.new_experiments
            if exp.get("status") in ["normal", "verified_outperformer"]
        ]
        
        # Use 80% for training, 20% for evaluation (held-out set)
        # If < 10 experiments, use all for training and evaluation
        if len(quality_exps) >= 10:
            split_idx = int(len(quality_exps) * 0.8)
            training_exps = quality_exps[:split_idx]
            eval_exps = quality_exps[split_idx:]
            logger.info(f"Split experiments: {len(training_exps)} for training, {len(eval_exps)} for evaluation")
        else:
            training_exps = quality_exps
            eval_exps = quality_exps
            logger.info(f"Using all {len(quality_exps)} experiments for both training and evaluation")
        
        # Trigger retraining with evaluation
        job = feedback_layer.trigger_model_retraining(
            new_experiments=training_exps,
            trigger_reason=request.trigger_reason,
            eval_experiments=eval_exps
        )
        
        if job.get("status") == "insufficient_data":
            return {
                "success": False,
                "error": job.get("message"),
                "n_experiments": job.get("n_quality_experiments", 0),
            }
        
        # Persist model version info with evaluation metrics
        improvement_metrics = job.get("improvement_metrics", {})
        db_version = ModelVersion(
            id=str(uuid.uuid4()),
            version=job.get("version", "v" + str(uuid.uuid4())[:8]),
            model_type="Linear Regression (Learnable)",
            status="active",
            trigger_reason=request.trigger_reason,
            training_samples=job.get("new_training_samples", 0),
            accuracy_score=job.get("after_evaluation", {}).get("overall_r2"),
            accuracy_improvement=improvement_metrics.get("r2_improvement") if improvement_metrics else None,
            training_started_at=datetime.now()
        )
        db.add(db_version)
        db.commit()
        db.refresh(db_version)
        
        # Prepare response with before/after metrics for UI visualization
        return {
            "success": True,
            "retraining_job": {
                "job_id": job.get("job_id"),
                "version": job.get("version"),
                "status": job.get("status"),
                "trigger_reason": job.get("trigger_reason"),
                "training_samples": job.get("new_training_samples"),
            },
            "evaluation": {
                "before": job.get("before_evaluation"),
                "after": job.get("after_evaluation"),
                "improvement": {
                    "mae_improvement": improvement_metrics.get("mae_improvement") if improvement_metrics else None,
                    "mae_percent_change": improvement_metrics.get("mae_percent_change") if improvement_metrics else None,
                    "r2_improvement": improvement_metrics.get("r2_improvement") if improvement_metrics else None,
                    "r2_percent_change": improvement_metrics.get("r2_percent_change") if improvement_metrics else None,
                }
            },
            "model_version": {
                "id": db_version.id,
                "version": db_version.version,
                "status": db_version.status,
            },
            "chart_data": {
                "metrics": ["MAE", "R²"],
                "before": {
                    "MAE": job.get("before_evaluation", {}).get("overall_mae"),
                    "R²": job.get("before_evaluation", {}).get("overall_r2"),
                },
                "after": {
                    "MAE": job.get("after_evaluation", {}).get("overall_mae"),
                    "R²": job.get("after_evaluation", {}).get("overall_r2"),
                },
            },
            "next_steps": [
                f"New model version {db_version.version} trained and deployed",
                f"Predictions will now reflect updated model",
                "Monitor re-ranking of catalysts on the dashboard"
            ],
        }
    except Exception as e:
        logger.error(f"Error triggering retraining: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/retraining-history")
def get_retraining_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complete history of model retraining events from DB"""
    logger.info(f"Retrieving retraining history for user: {current_user.email}")
    
    history = db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).all()
    return {
        "total_retraining_events": len(history),
        "history": history,
        "status": "up_to_date" if history else "no_retraining_yet",
    }


@router.post("/export")
def export_candidates_for_testing(
    request: ExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Export top candidates for experimental synthesis and testing.
    """
    logger.info(f"Exporting {len(request.catalyst_ids)} candidates in {request.export_format} format (user: {current_user.email})")

    db_reaction = db.query(Reaction).filter(
        Reaction.id == request.reaction_id,
        Reaction.creator_id == current_user.id
    ).first()
    if not db_reaction:
        raise HTTPException(status_code=403, detail="Not authorized to export for this reaction")

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get summary of experiments owned by the current user"""
    logger.info(f"Retrieving experiment summary for user: {current_user.email}")
    
    query = db.query(Experiment).filter(
        or_(
            Experiment.creator_id == current_user.id,
            Experiment.shared_with.contains([current_user.id])
        )
    )
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


@router.get("/model-evaluation")
def get_model_evaluation_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get the latest model evaluation metrics (before/after chart data).
    
    Returns:
    - Latest model version
    - Before/after metrics (MAE, R²)
    - Improvement percentages
    - Chart-friendly data for visualization
    """
    logger.info(f"Retrieving latest model evaluation metrics for user: {current_user.email}")
    
    try:
        # Get latest model version with evaluation data
        latest_version = db.query(ModelVersion).filter(
            ModelVersion.status == "active"
        ).order_by(ModelVersion.created_at.desc()).first()
        
        if not latest_version:
            return {
                "status": "no_models",
                "message": "No trained models found. Retraining is required.",
            }
        
        # Get all model versions for history
        all_versions = db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).limit(10).all()
        
        # Build chart data
        chart_data = {
            "current_version": latest_version.version,
            "training_samples": latest_version.training_samples,
            "status": latest_version.status,
            "accuracy_score": latest_version.accuracy_score,
            "accuracy_improvement": latest_version.accuracy_improvement,
            "created_at": latest_version.created_at.isoformat() if latest_version.created_at else None,
        }
        
        # Build history for trend
        history = []
        for v in all_versions:
            history.append({
                "version": v.version,
                "accuracy": v.accuracy_score,
                "accuracy_improvement": v.accuracy_improvement,
                "training_samples": v.training_samples,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            })
        
        return {
            "status": "success",
            "current_model": chart_data,
            "history": history,
            "model_improved": latest_version.accuracy_improvement > 0 if latest_version.accuracy_improvement else None,
        }
    except Exception as e:
        logger.error(f"Error retrieving model evaluation metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))