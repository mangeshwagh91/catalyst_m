"""API Routes - Enzymes endpoints"""

import uuid
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.models.models import Reaction, User
from app.layers.knowledge_layer import KnowledgeLayer
from app.core.logging import logger
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/api/enzymes", tags=["enzymes"])

knowledge_layer = KnowledgeLayer()


class EnzymeSuggestionRequest(BaseModel):
    reaction_id: str
    reactants: List[str]
    products: List[str]
    limit: int = Field(default=10, ge=1, le=50)


class EnzymeSuggestionResponse(BaseModel):
    reaction_id: str
    count: int
    source: str
    enzymes: List[dict]


@router.post("/suggest", response_model=EnzymeSuggestionResponse)
def suggest_enzymes(
    request: EnzymeSuggestionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Suggest relevant enzymes from UniProt database for a target reaction.
    
    Requires authentication.
    
    Query Parameters:
    - reaction_id: ID of the reaction
    - reactants: List of reactant compounds (e.g., ["glucose"])
    - products: List of product compounds (e.g., ["ethanol"])
    - limit: Maximum number of enzymes to return (default: 10)
    
    Returns:
    - List of enzyme records with UniProt IDs, EC numbers, organism, description
    - Source: "UniProt"
    """
    logger.info(
        f"Suggesting enzymes for reaction {request.reaction_id}: "
        f"{request.reactants} → {request.products} (user: {current_user.email})"
    )

    db_reaction = db.query(Reaction).filter(
        Reaction.id == request.reaction_id,
        Reaction.creator_id == current_user.id
    ).first()
    if not db_reaction:
        raise HTTPException(status_code=403, detail="Not authorized to suggest enzymes for this reaction")
    
    try:
        # Query knowledge layer for relevant enzymes
        enzymes = knowledge_layer.suggest_enzymes_for_reaction(
            reactants=request.reactants,
            products=request.products,
            limit=request.limit
        )
        
        logger.info(f"Retrieved {len(enzymes)} enzymes for reaction {request.reaction_id}")
        
        return EnzymeSuggestionResponse(
            reaction_id=request.reaction_id,
            count=len(enzymes),
            source="UniProt",
            enzymes=enzymes
        )
    
    except Exception as e:
        logger.error(f"Error suggesting enzymes: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available")
def get_available_enzymes():
    """
    Get information about available enzyme datasets and endpoints.
    """
    return {
        "status": "ok",
        "sources": {
            "uniprotdb": {
                "description": "Local UniProt database for enzyme queries",
                "endpoint": "/api/enzymes/suggest",
                "method": "POST",
                "available": True
            }
        },
        "endpoints": {
            "suggest": "POST /api/enzymes/suggest - Get enzyme suggestions for a reaction",
            "available": "GET /api/enzymes/available - List available enzyme sources"
        }
    }
