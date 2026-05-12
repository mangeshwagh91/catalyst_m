"""API Routes - Catalysts endpoints"""

from typing import List, Optional
import uuid
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.schemas import CatalystResponse, CatalystListResponse, GenerativeRequestSchema, GeneratedCatalystSchema
from app.models.models import Catalyst, Reaction, User
from app.layers.knowledge_layer import KnowledgeLayer
from app.layers.generative_layer import GenerativeLayer
from app.core.logging import logger
from app.api.dependencies import get_current_user

router = APIRouter(prefix="/api/catalysts", tags=["catalysts"])

knowledge_layer = KnowledgeLayer()
generative_layer = GenerativeLayer()


class RetrieveRequest(BaseModel):
    reaction_id: str
    reactants: List[str]
    products: List[str]
    limit: int = Field(default=23)


@router.post("/retrieve")
def retrieve_known_catalysts(
    request: RetrieveRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve known catalysts from scientific databases for a target reaction and persist them.
    
    Requires authentication. Catalysts will be associated with the authenticated user.
    
    Strategy:
    1. Extract elements from reactants/products
    2. Query Materials Project API for real materials
    3. Query UniProt database for relevant enzymes
    4. Combine results with source attribution
    5. Fall back to mock data if APIs unavailable
    
    Returns catalysts from Materials Project + enzymes from UniProt with clear source breakdown.
    """
    logger.info(f"Retrieving known catalysts and enzymes for {request.reactants} → {request.products} (user: {current_user.email})")
    
    db_reaction = db.query(Reaction).filter(
        Reaction.id == request.reaction_id,
        Reaction.creator_id == current_user.id
    ).first()
    if not db_reaction:
        raise HTTPException(status_code=403, detail="Not authorized to retrieve catalysts for this reaction")

    try:
        # Retrieve inorganic catalysts from Materials Project
        materials_catalysts = knowledge_layer.retrieve_catalysts_for_reaction(
            reactants=request.reactants,
            products=request.products,
            limit=request.limit // 2,  # Split limit between materials and enzymes
            use_real_data=True
        )
        
        # Retrieve enzymes from UniProt
        enzymes = knowledge_layer.suggest_enzymes_for_reaction(
            reactants=request.reactants,
            products=request.products,
            limit=request.limit // 2
        )
        
        # Convert enzymes to catalyst format for consistency
        enzyme_catalysts = []
        for enzyme in enzymes:
            enzyme_catalysts.append({
                "id": enzyme.get("id"),
                "name": enzyme.get("name"),
                "composition": enzyme.get("composition"),
                "source": "UniProt",
                "activity": enzyme.get("activity"),
                "selectivity": enzyme.get("selectivity"),
                "stability": enzyme.get("stability"),
                "description": enzyme.get("description"),
                "structure": enzyme.get("structure")
            })
        
        # Combine materials and enzymes
        all_catalysts = materials_catalysts + enzyme_catalysts
        
        # Track source breakdown
        materials_count = len([c for c in all_catalysts if c.get("source") == "Materials Project"])
        enzymes_count = len([c for c in all_catalysts if c.get("source") == "UniProt"])
        mock_count = len([c for c in all_catalysts if c.get("source") not in ["Materials Project", "UniProt"]])
        
        # Persist to database
        saved_catalysts = []
        for cat in all_catalysts:
            # Deduplicate: skip if this catalyst name already exists for this reaction
            existing = db.query(Catalyst).filter(
                Catalyst.reaction_id == request.reaction_id,
                Catalyst.name == cat["name"]
            ).first()
            if existing:
                saved_catalysts.append(existing)
                continue

            db_catalyst = Catalyst(
                id=str(uuid.uuid4()),
                reaction_id=request.reaction_id,
                name=cat["name"],
                composition=cat["composition"],
                source=cat["source"],
                activity=cat.get("activity"),
                selectivity=cat.get("selectivity"),
                stability=cat.get("stability"),
                description=cat.get("description")
            )
            db.add(db_catalyst)
            saved_catalysts.append(db_catalyst)
            
        db.commit()
        for cat in saved_catalysts:
            db.refresh(cat)
        
        # Build source breakdown message
        source_breakdown = []
        if materials_count > 0:
            source_breakdown.append(f"{materials_count} from Materials Project")
        if enzymes_count > 0:
            source_breakdown.append(f"{enzymes_count} from UniProt")
        if mock_count > 0:
            source_breakdown.append(f"{mock_count} from Mock Data")
        
        source_message = ", ".join(source_breakdown) if source_breakdown else "No data available"
        
        return {
            "reaction_id": request.reaction_id,
            "count": len(saved_catalysts),
            "count_breakdown": {
                "materials_project": materials_count,
                "uniprot": enzymes_count,
                "mock_data": mock_count
            },
            "source": source_message,
            "message": f"Retrieved {len(saved_catalysts)} catalysts: {source_message}",
            "catalysts": [CatalystResponse.model_validate(c) for c in saved_catalysts],
        }
    except Exception as e:
        logger.error(f"Error retrieving catalysts: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate", response_model=dict)
def generate_catalyst_variants(
    request: GenerativeRequestSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate novel catalyst variants using AI generative models and persist them.
    
    Requires authentication.
    """
    logger.info(f"Generating {request.num_variants} variants of {request.base_catalyst} (user: {current_user.email})")
    
    if request.reaction_id:
        db_reaction = db.query(Reaction).filter(
            Reaction.id == request.reaction_id,
            Reaction.creator_id == current_user.id
        ).first()
        if not db_reaction:
            raise HTTPException(status_code=403, detail="Not authorized to generate variants for this reaction")
    
    try:
        # Mock base catalyst for demonstration
        base_catalyst = {
            "id": "cat_001",
            "name": request.base_catalyst,
            "composition": "Cu0.6Zn0.2Al0.2",
            "activity": 72.5,
            "selectivity": 88.0,
            "stability": 85.0,
        }
        
        variants = generative_layer.generate_variants(
            base_catalyst=base_catalyst,
            num_variants=request.num_variants,
            optimization_target=request.optimization_target
        )
        
        saved_variants = []
        for var in variants:
            validation = generative_layer.validate_structure(var["composition"])
            
            db_catalyst = Catalyst(
                id=str(uuid.uuid4()),
                reaction_id=request.reaction_id,
                name=var["name"],
                composition=var["composition"],
                source="generated",
                activity=var.get("activity"),
                selectivity=var.get("selectivity"),
                stability=var.get("stability"),
                description=f"Generated variant of {request.base_catalyst}",
                modification_type=request.optimization_target,
                is_valid=validation["is_valid"],
                requires_human_review=validation["requires_human_review"]
            )
            db.add(db_catalyst)
            saved_variants.append(db_catalyst)
            
        db.commit()
        for var in saved_variants:
            db.refresh(var)
        
        return {
            "base_catalyst": request.base_catalyst,
            "optimization_target": request.optimization_target,
            "num_variants": len(saved_variants),
            "variants": [CatalystResponse.model_validate(v) for v in saved_variants],
            "model_version": generative_layer.generative_model_version,
        }
    except Exception as e:
        logger.error(f"Error generating variants: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def get_knowledge_base_statistics(db: Session = Depends(get_db)):
    """Get statistics about the knowledge base"""
    logger.info("Retrieving knowledge base statistics")
    
    stats = knowledge_layer.get_statistics()
    return {
        **stats,
        "last_updated": "2026-05-05T00:00:00Z",
        "sources_description": {
            "Materials Project": "10 catalysts from computational database",
            "Open Catalyst Project": "8 catalysts from OC20/OC22",
            "BRENDA": "3 enzyme catalysts",
            "experimental": "2 from internal experiments",
        },
    }
