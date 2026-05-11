"""SQLAlchemy ORM Models for the Catalyst AI Platform"""

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, Text, DateTime,
    ForeignKey, JSON, Index
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


def _utcnow():
    return datetime.now(timezone.utc)


class User(Base):
    """Stores user accounts for multi-user platform"""
    __tablename__ = "users"

    id = Column(String(64), primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    reactions = relationship("Reaction", back_populates="creator", foreign_keys="Reaction.creator_id")
    experiments = relationship("Experiment", back_populates="creator", foreign_keys="Experiment.creator_id")

    __table_args__ = (
        Index("ix_users_username", "username"),
        Index("ix_users_email", "email"),
        Index("ix_users_is_active", "is_active"),
    )

    def __repr__(self):
        return f"<User(id={self.id!r}, username={self.username!r}, email={self.email!r})>"


class Reaction(Base):
    """Stores target reaction queries submitted by researchers."""
    __tablename__ = "reactions"

    id = Column(String(64), primary_key=True)
    creator_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    reactants = Column(JSON, nullable=False)        # List[str]
    products = Column(JSON, nullable=False)          # List[str]
    shared_with = Column(JSON, nullable=True, default=list)
    temperature = Column(Float, default=298.15)
    pressure = Column(Float, default=1.0)
    solvent = Column(String(100), default="water")
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    creator = relationship("User", back_populates="reactions", foreign_keys=[creator_id])
    catalysts = relationship("Catalyst", back_populates="reaction", cascade="all, delete-orphan")
    predictions = relationship("Prediction", back_populates="reaction", cascade="all, delete-orphan")
    experiments = relationship("Experiment", back_populates="reaction", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_reactions_creator_id", "creator_id"),
        Index("ix_reactions_name", "name"),
        Index("ix_reactions_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Reaction(id={self.id!r}, name={self.name!r}, creator_id={self.creator_id!r})>"


class Catalyst(Base):
    """Stores both known (retrieved) and AI-generated catalyst candidates."""
    __tablename__ = "catalysts"

    id = Column(String(64), primary_key=True)
    reaction_id = Column(String(64), ForeignKey("reactions.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    composition = Column(String(255), nullable=False)
    source = Column(String(50), default="known")   # 'known' | 'generated' | 'experimental'
    confidence = Column(Float, default=0.5)
    activity = Column(Float, nullable=True)
    selectivity = Column(Float, nullable=True)
    stability = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    structure_data = Column(JSON, nullable=True)    # Lattice, support, dopants, etc.
    modification_type = Column(String(50), nullable=True)   # For generated: doping | substitution …
    modification_description = Column(Text, nullable=True)
    is_valid = Column(Boolean, default=True)
    requires_human_review = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    reaction = relationship("Reaction", back_populates="catalysts")
    predictions = relationship("Prediction", back_populates="catalyst", cascade="all, delete-orphan")
    experiments = relationship("Experiment", back_populates="catalyst", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_catalysts_reaction_id", "reaction_id"),
        Index("ix_catalysts_source", "source"),
        Index("ix_catalysts_name", "name"),
    )

    def __repr__(self):
        return f"<Catalyst(id={self.id!r}, name={self.name!r}, source={self.source!r})>"


class Prediction(Base):
    """Stores ML model predictions for each catalyst + reaction combination."""
    __tablename__ = "predictions"

    id = Column(String(64), primary_key=True)
    reaction_id = Column(String(64), ForeignKey("reactions.id", ondelete="CASCADE"), nullable=False)
    catalyst_id = Column(String(64), ForeignKey("catalysts.id", ondelete="CASCADE"), nullable=False)
    activity = Column(Float, nullable=False)
    selectivity = Column(Float, nullable=False)
    stability = Column(Float, nullable=False)
    turnover_frequency = Column(Float, nullable=True)
    combined_score = Column(Float, nullable=True)
    rank = Column(Integer, nullable=True)
    uncertainty = Column(Float, default=0.1)
    model_version = Column(String(30), default="v1.0-gnn")
    reaction_conditions = Column(JSON, nullable=True)  # {temperature, pressure, solvent}
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    # Relationships
    reaction = relationship("Reaction", back_populates="predictions")
    catalyst = relationship("Catalyst", back_populates="predictions")

    __table_args__ = (
        Index("ix_predictions_reaction_id", "reaction_id"),
        Index("ix_predictions_catalyst_id", "catalyst_id"),
        Index("ix_predictions_combined_score", "combined_score"),
    )

    def __repr__(self):
        return f"<Prediction(id={self.id!r}, catalyst_id={self.catalyst_id!r}, score={self.combined_score})>"


class Experiment(Base):
    """Stores real-lab experimental results for the feedback loop."""
    __tablename__ = "experiments"

    id = Column(String(64), primary_key=True)
    creator_id = Column(String(64), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reaction_id = Column(String(64), ForeignKey("reactions.id", ondelete="CASCADE"), nullable=False)
    catalyst_id = Column(String(64), ForeignKey("catalysts.id", ondelete="CASCADE"), nullable=False)
    # Measured properties
    measured_activity = Column(Float, nullable=True)
    measured_selectivity = Column(Float, nullable=True)
    measured_stability = Column(Float, nullable=True)
    yield_percentage = Column(Float, nullable=True)
    # Prediction reference (stored snapshot)
    predicted_activity = Column(Float, nullable=True)
    predicted_selectivity = Column(Float, nullable=True)
    predicted_stability = Column(Float, nullable=True)
    # Deviations (computed)
    activity_deviation = Column(Float, nullable=True)
    selectivity_deviation = Column(Float, nullable=True)
    stability_deviation = Column(Float, nullable=True)
    # Analysis
    status = Column(String(30), default="normal")   # normal | verified_outperformer | anomaly
    hypothesis = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    researcher_name = Column(String(100), nullable=True)
    tested_at = Column(DateTime(timezone=True), nullable=True)
    logged_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    # Relationships
    creator = relationship("User", back_populates="experiments", foreign_keys=[creator_id])
    reaction = relationship("Reaction", back_populates="experiments")
    catalyst = relationship("Catalyst", back_populates="experiments")

    shared_with = Column(JSON, nullable=True, default=list)

    __table_args__ = (
        Index("ix_experiments_creator_id", "creator_id"),
        Index("ix_experiments_reaction_id", "reaction_id"),
        Index("ix_experiments_catalyst_id", "catalyst_id"),
        Index("ix_experiments_status", "status"),
        Index("ix_experiments_logged_at", "logged_at"),
    )

    def __repr__(self):
        return f"<Experiment(id={self.id!r}, creator_id={self.creator_id!r}, catalyst_id={self.catalyst_id!r}, status={self.status!r})>"


class ModelVersion(Base):
    """Tracks ML model versions, retraining history, and rollback capability."""
    __tablename__ = "model_versions"

    id = Column(String(64), primary_key=True)
    version = Column(String(30), unique=True, nullable=False)
    model_type = Column(String(100), default="GNN")
    status = Column(String(20), default="active")   # active | archived | testing | failed
    trigger_reason = Column(String(100), nullable=True)
    training_samples = Column(Integer, nullable=True)
    accuracy_score = Column(Float, nullable=True)
    accuracy_improvement = Column(Float, nullable=True)
    training_started_at = Column(DateTime(timezone=True), nullable=True)
    training_completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (
        Index("ix_model_versions_version", "version"),
        Index("ix_model_versions_status", "status"),
    )

    def __repr__(self):
        return f"<ModelVersion(version={self.version!r}, status={self.status!r})>"
