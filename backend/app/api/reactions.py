"""API Routes - Reactions endpoints"""

import uuid
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import ReactionCreate, ReactionResponse
from app.models.models import Reaction, User
from app.core.logging import logger
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/api/reactions", tags=["reactions"])


@router.post("/", response_model=ReactionResponse)
def create_reaction(
    reaction: ReactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new target reaction query.
    
    Requires authentication. The reaction will be owned by the authenticated user.
    
    This triggers the full discovery pipeline:
    1. Knowledge Retrieval - fetch known catalysts
    2. Generative Design - create novel variants
    3. Prediction - rank all candidates
    4. Visualization - prepare interactive displays
    """
    logger.info(f"Creating new reaction: {reaction.name} (user: {current_user.email})")
    
    try:
        db_reaction = Reaction(
            id=str(uuid.uuid4()),
            name=reaction.name,
            reactants=reaction.reactants,
            products=reaction.products,
            shared_with=reaction.shared_with or [],
            temperature=reaction.temperature,
            temperature_unit=reaction.temperature_unit,
            pressure=reaction.pressure,
            pressure_unit=reaction.pressure_unit,
            solvent=reaction.solvent,
            description=reaction.description,
            creator_id=current_user.id  # Enforce ownership
        )
        db.add(db_reaction)
        db.commit()
        db.refresh(db_reaction)
        
        logger.info(f"Reaction created: {db_reaction.id} by {current_user.email}")
        return db_reaction
    except Exception as e:
        logger.error(f"Error creating reaction: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{reaction_id}", response_model=ReactionResponse)
def get_reaction(
    reaction_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve details of a specific reaction. Users can only see owned or shared reactions."""
    logger.info(f"Retrieving reaction: {reaction_id} (user: {current_user.email})")
    
    db_reaction = db.query(Reaction).filter(
        Reaction.id == reaction_id,
        or_(
            Reaction.creator_id == current_user.id,
            Reaction.shared_with.contains([current_user.id])
        )
    ).first()
    
    if not db_reaction:
        raise HTTPException(status_code=404, detail="Reaction not found or not authorized")
        
    return db_reaction


@router.get("/")
def list_reactions(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """List all reactions, ordered by newest first"""
    logger.info(f"Listing reactions (skip={skip}, limit={limit})")
    
    query = db.query(Reaction).order_by(Reaction.created_at.desc())
    total = query.count()
    reactions = query.offset(skip).limit(limit).all()
    
    return {"reactions": [ReactionResponse.model_validate(r) for r in reactions], "total": total}

