"""API Routes - Reactions endpoints"""

import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import ReactionCreate, ReactionResponse
from app.models.models import Reaction
from app.core.logging import logger

router = APIRouter(prefix="/api/reactions", tags=["reactions"])


@router.post("/", response_model=ReactionResponse)
def create_reaction(reaction: ReactionCreate, db: Session = Depends(get_db)):
    """
    Create a new target reaction query.
    
    This triggers the full discovery pipeline:
    1. Knowledge Retrieval - fetch known catalysts
    2. Generative Design - create novel variants
    3. Prediction - rank all candidates
    4. Visualization - prepare interactive displays
    """
    logger.info(f"Creating new reaction: {reaction.name}")
    
    try:
        db_reaction = Reaction(
            id=str(uuid.uuid4()),
            name=reaction.name,
            reactants=reaction.reactants,
            products=reaction.products,
            temperature=reaction.temperature,
            temperature_unit=reaction.temperature_unit,
            pressure=reaction.pressure,
            pressure_unit=reaction.pressure_unit,
            solvent=reaction.solvent,
            description=reaction.description
        )
        db.add(db_reaction)
        db.commit()
        db.refresh(db_reaction)
        
        return db_reaction
    except Exception as e:
        logger.error(f"Error creating reaction: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{reaction_id}", response_model=ReactionResponse)
def get_reaction(reaction_id: str, db: Session = Depends(get_db)):
    """Retrieve details of a specific reaction"""
    logger.info(f"Retrieving reaction: {reaction_id}")
    
    db_reaction = db.query(Reaction).filter(Reaction.id == reaction_id).first()
    if not db_reaction:
        raise HTTPException(status_code=404, detail="Reaction not found")
        
    return db_reaction


@router.get("/")
def list_reactions(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """List all reactions, ordered by newest first"""
    logger.info(f"Listing reactions (skip={skip}, limit={limit})")
    
    query = db.query(Reaction).order_by(Reaction.created_at.desc())
    total = query.count()
    reactions = query.offset(skip).limit(limit).all()
    
    return {"reactions": [ReactionResponse.model_validate(r) for r in reactions], "total": total}

