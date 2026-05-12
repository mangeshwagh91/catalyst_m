"""Pydantic schemas for request/response validation"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime

# Shared config that silences Pydantic's 'model_' namespace warning
_no_ns = ConfigDict(protected_namespaces=())

# ==================== Reaction Schemas ====================

class ReactionCreate(BaseModel):
    """Schema for creating a new reaction query"""
    name: str
    reactants: List[str]
    products: List[str]
    temperature: float = Field(default=298.15, description="Temperature value")
    temperature_unit: str = Field(default="K", description="K or C")
    pressure: float = Field(default=1.0, description="Pressure value")
    pressure_unit: str = Field(default="atm", description="atm, bar, MPa")
    solvent: str = Field(default="water")
    description: Optional[str] = None


class ReactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    """Schema for reaction response"""
    id: str
    name: str
    reactants: List[str]
    products: List[str]
    temperature: float
    temperature_unit: str
    pressure: float
    pressure_unit: str
    solvent: str
    description: Optional[str]
    created_at: datetime


# ==================== Catalyst Schemas ====================

class CatalystCreate(BaseModel):
    """Schema for creating a catalyst"""
    name: str
    composition: str
    structure_data: Optional[Dict[str, Any]] = None
    source: str = Field(default="known", description="'known' or 'generated'")
    confidence: float = Field(default=0.5, ge=0, le=1)
    description: Optional[str] = None


class CatalystResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    """Schema for catalyst response"""
    id: str
    reaction_id: str
    name: str
    composition: str
    structure_data: Optional[Dict[str, Any]]
    source: str
    confidence: float
    description: Optional[str]
    created_at: datetime


class CatalystListResponse(BaseModel):
    """Schema for list of catalysts"""
    known: List[CatalystResponse]
    generated: List[CatalystResponse]
    total_count: int


# ==================== Prediction Schemas ====================

class PredictionCreate(BaseModel):
    model_config = _no_ns
    """Schema for creating a prediction"""
    reaction_id: str
    catalyst_id: str
    activity: float = Field(ge=0, le=100)
    selectivity: float = Field(ge=0, le=100)
    stability: float = Field(ge=0, le=100)
    turnover_frequency: Optional[float] = None
    uncertainty: float = Field(default=0.1, ge=0, le=1)
    model_version: str = "v1.0"


class PredictionResponse(BaseModel):
    model_config = _no_ns
    """Schema for prediction response"""
    id: str
    reaction_id: str
    catalyst_id: str
    activity: float
    selectivity: float
    stability: float
    turnover_frequency: Optional[float]
    uncertainty: float
    model_version: str
    created_at: datetime


class PredictionRankingResponse(BaseModel):
    """Schema for ranked predictions"""
    catalyst_id: str
    catalyst_name: str
    composition: str
    source: str
    activity: float
    selectivity: float
    stability: float
    combined_score: float  # Weighted combination
    rank: int
    uncertainty: float


# ==================== Experiment Schemas ====================

class ExperimentCreate(BaseModel):
    """Schema for logging experimental results"""
    reaction_id: str
    catalyst_id: str
    measured_activity: Optional[float] = None
    measured_selectivity: Optional[float] = None
    measured_stability: Optional[float] = None
    yield_percentage: Optional[float] = None
    notes: Optional[str] = None
    researcher_name: Optional[str] = None
    tested_at: Optional[datetime] = None


class ExperimentResponse(BaseModel):
    """Schema for experiment response"""
    id: str
    reaction_id: str
    catalyst_id: str
    measured_activity: Optional[float]
    measured_selectivity: Optional[float]
    measured_stability: Optional[float]
    yield_percentage: Optional[float]
    notes: Optional[str]
    hypothesis: Optional[str]
    activity_deviation: Optional[float]
    selectivity_deviation: Optional[float]
    stability_deviation: Optional[float]
    status: str
    logged_at: datetime


class ExperimentDiscrepancyResponse(BaseModel):
    """Schema for experiment discrepancy analysis"""
    catalyst_name: str
    composition: str
    predicted_activity: float
    measured_activity: float
    activity_deviation: float
    deviation_percentage: float
    status: str
    hypothesis: Optional[str]


# ==================== Generative Design Schemas ====================

class GenerativeRequestSchema(BaseModel):
    """Schema for requesting generative design"""
    base_catalyst: str
    num_variants: int = Field(default=8, ge=1, le=20)
    optimization_target: str = Field(default="activity", description="activity, selectivity, or stability")
    reaction_id: Optional[str] = None


class GeneratedCatalystSchema(BaseModel):
    """Schema for generated catalyst variant"""
    name: str
    composition: str
    modification: str  # Description of modification from base
    confidence: float
    predicted_improvement: float  # Percentage improvement vs base


# ==================== Visualization Schemas ====================

class VisualizationDataSchema(BaseModel):
    """Schema for visualization data"""
    catalyst_id: str
    catalyst_name: str
    composition: str
    structure_3d: Optional[Dict[str, Any]]
    structure_2d_smiles: Optional[str]
    properties: Dict[str, float]


class DashboardStatsSchema(BaseModel):
    model_config = _no_ns
    """Schema for dashboard statistics"""
    total_reactions: int
    total_catalysts_known: int
    total_catalysts_generated: int
    total_predictions: int
    total_experiments: int
    average_prediction_accuracy: float
    model_version: str


# ==================== Feedback & Learning Schemas ====================

class ModelRetrainingRequestSchema(BaseModel):
    """Schema for triggering model retraining"""
    trigger_type: str  # "manual", "scheduled", "auto_drift_detected"
    min_new_data_points: int = Field(default=5)
    include_low_confidence: bool = False


class ModelRetrainingResponseSchema(BaseModel):
    """Schema for model retraining response"""
    job_id: str
    status: str  # queued, training, completed, failed
    version: str
    training_started_at: Optional[datetime]
    training_completed_at: Optional[datetime]
    accuracy_improvement: Optional[float]


# ==================== Analysis Schemas ====================

class DiscrepancyAnalysisSchema(BaseModel):
    model_config = _no_ns
    """Schema for discrepancy analysis results"""
    outlier_experiments: List[ExperimentDiscrepancyResponse]
    avg_deviation: float
    max_deviation: float
    flagged_structural_features: List[str]
    recommended_hypothesis: str
    model_drift_detected: bool
