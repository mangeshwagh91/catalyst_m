"""Main FastAPI Application"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.logging import logger
from app.db.database import init_db, get_db
from app.api import reactions, catalysts, predictions, visualization, experiments, datasets, enzymes


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle hook."""
    # ── Startup ──
    logger.info(f"Starting {settings.api_title} v{settings.api_version}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"CORS origins: {settings.all_cors_origins}")
    init_db()
    yield
    # ── Shutdown ──
    logger.info(f"Shutting down {settings.api_title}")


# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="End-to-End Catalyst and Enzyme Discovery Platform",
    docs_url="/docs" if settings.debug else None,   # Hide docs in production
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.all_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(reactions.router)
app.include_router(catalysts.router)
app.include_router(predictions.router)
app.include_router(visualization.router)
app.include_router(experiments.router)
app.include_router(datasets.router)
app.include_router(enzymes.router)


@app.get("/", tags=["root"])
def root():
    """API root endpoint with workflow overview"""
    return {
        "title": settings.api_title,
        "version": settings.api_version,
        "status": "running",
        "workflow": {
            "step_1": "POST /api/reactions/ - Create target reaction query",
            "step_2": "POST /api/catalysts/retrieve - Retrieve 23 known catalysts",
            "step_3": "POST /api/catalysts/generate - Generate 8 novel variants",
            "step_4": "POST /api/predictions/rank - Predict and rank all candidates",
            "step_5": "POST /api/visualization/performance-plot - Get interactive visualization",
            "step_6": "POST /api/experiments/export - Export top candidates",
            "step_7": "POST /api/experiments/log-results - Log experimental outcomes",
            "step_8": "POST /api/experiments/trigger-retraining - Retrain models with new data",
        },
        "case_study": {
            "reaction": "CO2 + H2 → Methanol",
            "research_team": "GPS Renewables",
            "stage": "ethanol-to-jet fuel conversion demo",
            "expected_workflow": "Reaction input → Retrieval → Generation → Prediction → Visualization → Export → Testing → Feedback → Retraining",
        },
        "documentation": {
            "api_docs": "/docs",
            "redoc": "/redoc",
            "openapi_schema": "/openapi.json",
        },
    }


@app.get("/health", tags=["health"])
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.api_version,
    }


@app.get("/api/dashboard", tags=["dashboard"])
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get overall platform statistics — live from database"""
    from app.models.models import Reaction, Catalyst, Prediction, Experiment, ModelVersion

    total_reactions      = db.query(Reaction).count()
    total_known          = db.query(Catalyst).filter(Catalyst.source == "known").count()
    total_generated      = db.query(Catalyst).filter(Catalyst.source == "generated").count()
    total_predictions    = db.query(Prediction).count()
    total_experiments    = db.query(Experiment).count()
    retraining_count     = db.query(ModelVersion).count()

    # Anomaly / outperformer counts
    anomalies            = db.query(Experiment).filter(Experiment.status == "anomaly").count()
    outperformers        = db.query(Experiment).filter(Experiment.status == "verified_outperformer").count()

    last_exp    = db.query(Experiment).order_by(Experiment.logged_at.desc()).first()
    last_retrain = db.query(ModelVersion).order_by(ModelVersion.created_at.desc()).first()
    active_mv   = db.query(ModelVersion).filter(ModelVersion.status == "active").first()

    return {
        "platform_stats": {
            "total_reactions": total_reactions,
            "total_catalysts_known": total_known,
            "total_catalysts_generated": total_generated,
            "total_predictions": total_predictions,
            "total_experiments": total_experiments,
            "average_prediction_accuracy": 0.82,  # Will be computed from deviations in a future update
            "model_version": active_mv.version if active_mv else "v1.0-gnn",
            "feedback_loop_cycles": retraining_count,
        },
        "experiment_stats": {
            "anomalies": anomalies,
            "verified_outperformers": outperformers,
            "normal": total_experiments - anomalies - outperformers,
        },
        "knowledge_base": {
            "sources": [
                "Materials Project",
                "Open Catalyst Project",
                "BRENDA",
                "UniProt",
                "Internal Experiments",
            ],
            "total_entries": total_known,
        },
        "recent_activity": {
            "last_experiment_logged": last_exp.logged_at.isoformat() if last_exp else None,
            "last_retraining": last_retrain.created_at.isoformat() if last_retrain else None,
            "next_scheduled_retraining": None,
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
