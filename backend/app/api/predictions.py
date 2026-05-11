"""API Routes - Predictions endpoints"""

import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.database import get_db
from app.schemas.schemas import PredictionRankingResponse
from app.models.models import Prediction, Reaction, User
from app.layers.prediction_layer import PredictionLayer
from app.core.logging import logger
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/api/predictions", tags=["predictions"])

# Global prediction layer instance
prediction_layer = PredictionLayer()


def ensure_latest_model():
    """
    Ensure the prediction layer is using the latest trained model.
    This is called before each prediction to guarantee model freshness.
    """
    # The PredictionLayer.trainable model automatically loads the latest
    # state from disk on initialization, so we just ensure it's loaded
    if hasattr(prediction_layer, 'trainable') and prediction_layer.trainable:
        # Trigger reload if model state exists
        prediction_layer.trainable._load_model_state()
    return prediction_layer


class RankRequest(BaseModel):
    catalysts: List[Dict[str, Any]]
    reaction_conditions: Dict[str, Any]
    reaction_id: str
    weights: Optional[Dict[str, float]] = None


class PredictSingleRequest(BaseModel):
    catalyst: Dict[str, Any]
    reaction_conditions: Dict[str, Any]
    reaction_id: str


@router.post("/rank")
def rank_catalysts(
    request: RankRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Predict properties for multiple catalysts and rank them, then persist results.
    Always uses the latest trained model loaded from disk.
    """
    logger.info(f"Ranking {len(request.catalysts)} catalysts for reaction {request.reaction_id} (user: {current_user.email})")
    
    db_reaction = db.query(Reaction).filter(
        Reaction.id == request.reaction_id,
        Reaction.creator_id == current_user.id
    ).first()
    if not db_reaction:
        raise HTTPException(status_code=403, detail="Not authorized to rank catalysts for this reaction")

    try:
        # Ensure we're using the latest model
        pred_layer = ensure_latest_model()
        
        if not request.reaction_conditions:
            reaction_conditions = {
                "temperature": 298.15,
                "pressure": 1.0,
                "solvent": "water"
            }
        else:
            reaction_conditions = request.reaction_conditions
        
        # Predict properties for all catalysts
        predictions = pred_layer.batch_predict(request.catalysts, reaction_conditions)
        
        # Rank catalysts
        ranked = pred_layer.rank_catalysts(predictions, request.weights)
        
        saved_predictions = []
        for r in ranked:
            db_prediction = Prediction(
                id=str(uuid.uuid4()),
                reaction_id=request.reaction_id,
                catalyst_id=r["catalyst_id"],
                activity=r["activity"],
                selectivity=r["selectivity"],
                stability=r["stability"],
                combined_score=r["combined_score"],
                rank=r["rank"],
                uncertainty=r["uncertainty"],
                model_version=pred_layer.model_version,
                reaction_conditions=reaction_conditions
            )
            db.add(db_prediction)
            saved_predictions.append(db_prediction)
            
        db.commit()
        
        return {
            "reaction_conditions": reaction_conditions,
            "total_catalysts": len(ranked),
            "predictions": ranked,
            "model_info": {
                "version": pred_layer.model_version,
                "confidence": pred_layer.model_confidence,
                "avg_uncertainty": sum(p["uncertainty"] for p in ranked) / len(ranked) if ranked else 0,
                "is_trained": pred_layer.trainable.is_trained if hasattr(pred_layer, 'trainable') else False,
                "training_samples": pred_layer.trainable.n_samples if hasattr(pred_layer, 'trainable') else 0,
            },
        }
    except Exception as e:
        logger.error(f"Error ranking catalysts: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/predict-single")
def predict_single_catalyst(
    request: PredictSingleRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Predict properties for a single catalyst and persist. Always uses latest model."""
    logger.info(f"Predicting properties for {request.catalyst.get('name', 'unknown')} (user: {current_user.email})")

    db_reaction = db.query(Reaction).filter(
        Reaction.id == request.reaction_id,
        Reaction.creator_id == current_user.id
    ).first()
    if not db_reaction:
        raise HTTPException(status_code=403, detail="Not authorized to predict for this reaction")
    
    try:
        # Ensure we're using the latest model
        pred_layer = ensure_latest_model()
        
        prediction = pred_layer.predict_properties(request.catalyst, request.reaction_conditions)
        
        db_prediction = Prediction(
            id=str(uuid.uuid4()),
            reaction_id=request.reaction_id,
            catalyst_id=request.catalyst["id"],
            activity=prediction["activity"],
            selectivity=prediction["selectivity"],
            stability=prediction["stability"],
            uncertainty=prediction.get("uncertainty", 0.1),
            model_version=pred_layer.model_version,
            reaction_conditions=request.reaction_conditions
        )
        db.add(db_prediction)
        db.commit()
        db.refresh(db_prediction)
        
        return {
            "catalyst_id": request.catalyst["id"],
            "catalyst_name": request.catalyst["name"],
            "prediction": prediction,
            "model_version": pred_layer.model_version,
            "is_trained": pred_layer.trainable.is_trained if hasattr(pred_layer, 'trainable') else False,
        }
    except Exception as e:
        logger.error(f"Error predicting properties: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/model-info")
def get_prediction_model_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed information about the prediction model (always latest)"""
    logger.info("Retrieving prediction model information")
    
    # Ensure we have the latest model
    pred_layer = ensure_latest_model()
    
    return {
        **pred_layer.get_model_details(),
        "available_since": "2026-01-15",
        "last_updated": "2026-05-01",
        "status": "production",
        "trainable_model_info": {
            "is_trained": pred_layer.trainable.is_trained if hasattr(pred_layer, 'trainable') else False,
            "version": pred_layer.trainable.model_version if hasattr(pred_layer, 'trainable') else None,
            "n_training_samples": pred_layer.trainable.n_samples if hasattr(pred_layer, 'trainable') else 0,
            "model_state_loaded_from_disk": True,
        }
    }

