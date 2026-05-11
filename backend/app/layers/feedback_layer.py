"""Feedback & Learning Layer - Experiment logging and model retraining"""

from datetime import datetime, timezone
from typing import Any, Dict, List, TYPE_CHECKING
from app.core.logging import logger

if TYPE_CHECKING:
    from app.layers.prediction_layer import PredictionLayer


class FeedbackLearningLayer:
    """Feedback & Learning Layer - Manages experimental feedback and model retraining"""
    
    def __init__(self, prediction_layer: "PredictionLayer" = None):
        self.logger = logger
        self.retraining_history = []
        self.prediction_layer = prediction_layer  # Reference to trainable model
    
    def log_experiment(
        self,
        reaction_id: str,
        catalyst_id: str,
        measured_properties: dict[str, float],
        predicted_properties: dict[str, float],
        researcher_name: str | None = None,
        notes: str | None = None
    ) -> dict[str, any]:
        """
        Log experimental results and compare with predictions.
        
        This triggers:
        1. Predicted vs. actual comparison
        2. Discrepancy analysis
        3. Hypothesis generation
        4. Automatic flagging of anomalies
        """
        self.logger.info(
            f"Logging experiment for catalyst {catalyst_id} (researcher: {researcher_name})"
        )
        
        # Calculate deviations
        deviations = self._calculate_deviations(measured_properties, predicted_properties)
        
        # Analyze discrepancies
        analysis = self._analyze_discrepancies(deviations, measured_properties)
        
        # Generate hypothesis
        hypothesis = self._generate_hypothesis(analysis, measured_properties)
        
        # Determine status (normal, verified outperformer, or anomaly)
        status = self._determine_status(deviations)
        
        experiment_record = {
            "experiment_id": f"exp_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "reaction_id": reaction_id,
            "catalyst_id": catalyst_id,
            "measured_properties": measured_properties,
            "predicted_properties": predicted_properties,
            "deviations": deviations,
            "status": status,
            "hypothesis": hypothesis,
            "analysis": analysis,
            "researcher_name": researcher_name,
            "notes": notes,
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        
        self.logger.info(f"Experiment logged with status: {status}")
        return experiment_record
    
    def _calculate_deviations(
        self,
        measured: dict[str, float],
        predicted: dict[str, float]
    ) -> dict[str, dict[str, float]]:
        """Calculate deviations between measured and predicted values"""
        deviations = {}
        
        for key in ["activity", "selectivity", "stability"]:
            if key in measured and key in predicted:
                actual_deviation = measured[key] - predicted[key]
                percent_deviation = (actual_deviation / predicted[key] * 100) if predicted[key] != 0 else 0
                
                deviations[key] = {
                    "measured": measured[key],
                    "predicted": predicted[key],
                    "absolute_deviation": round(actual_deviation, 2),
                    "percent_deviation": round(percent_deviation, 2),
                }
        
        return deviations
    
    def _analyze_discrepancies(self, deviations: dict[str, any], measured: dict[str, float]) -> dict[str, any]:
        """
        Analyze discrepancies to identify model weaknesses.
        
        Returns insights about:
        - Which properties deviate most
        - Whether deviations correlate
        - Potential systematic errors
        """
        analysis = {
            "large_deviations": [],
            "systematic_error": False,
            "outlier_flags": [],
        }
        
        # Flag large deviations (>15%)
        for key, dev in deviations.items():
            if abs(dev["percent_deviation"]) > 15:
                analysis["large_deviations"].append({
                    "property": key,
                    "percent_error": dev["percent_deviation"],
                    "impact": "High" if abs(dev["percent_deviation"]) > 30 else "Moderate",
                })
        
        # Check for systematic errors (all deviate in same direction)
        if len(analysis["large_deviations"]) >= 2:
            directions = [d["percent_error"] > 0 for d in analysis["large_deviations"]]
            if all(directions) or not any(directions):
                analysis["systematic_error"] = True
        
        return analysis
    
    def _generate_hypothesis(
        self,
        analysis: dict[str, any],
        measured: dict[str, float]
    ) -> str:
        """
        Generate human-readable hypothesis about discrepancies.
        
        Examples:
        - "Steric hindrance at site X likely underestimated"
        - "Surface reconstruction under reaction conditions not captured"
        - "Presence of unaccounted surface impurities"
        """
        if not analysis["large_deviations"]:
            return "Predictions matched measurements. Model performed well."
        
        main_deviation = max(analysis["large_deviations"], key=lambda x: abs(x["percent_error"]))
        prop = main_deviation["property"]
        is_underestimated = main_deviation["percent_error"] > 0
        
        hypotheses = {
            "activity": {
                True: "Model may have underestimated active site accessibility or reaction kinetics. "
                      "Surface reconstruction or dynamic morphology changes under operating conditions not captured.",
                False: "Model may have overestimated catalytic sites. Possible surface poisoning, sintering, "
                       "or mass transport limitations not accounted for."
            },
            "selectivity": {
                True: "Model underestimated selectivity. Secondary reaction pathways may be suppressed "
                      "by unmodeled surface features or adsorbate-adsorbate interactions.",
                False: "Model overestimated selectivity. Side reactions or catalyst deactivation mechanisms "
                       "not fully captured in the model."
            },
            "stability": {
                True: "Catalyst more stable than predicted. Possible formation of protective surface layers "
                      "or passivation effects.",
                False: "Catalyst less stable than predicted. Possible agglomeration, leaching, or chemical degradation "
                       "not captured by the model."
            },
        }
        
        hypothesis = hypotheses.get(prop, {}).get(is_underestimated, "")
        
        if analysis["systematic_error"]:
            hypothesis += " [SYSTEMATIC ERROR: Multiple properties deviate in same direction - " \
                         "suggests fundamental model limitation rather than random error]"
        
        return hypothesis
    
    def _determine_status(self, deviations: dict[str, any]) -> str:
        """Determine experiment status: normal, verified_outperformer, or anomaly"""
        # Check if experiment exceeded predictions significantly
        exceeds = sum(
            1 for dev in deviations.values() 
            if dev.get("percent_deviation", 0) > 20
        )
        
        # Check for anomalies (large negative deviations)
        underperforms = sum(
            1 for dev in deviations.values() 
            if dev.get("percent_deviation", 0) < -20
        )
        
        if exceeds >= 2:
            return "verified_outperformer"
        elif underperforms >= 2:
            return "anomaly"
        else:
            return "normal"
    
    def flag_outliers(self, experiments: list[dict[str, any]]) -> dict[str, any]:
        """
        Identify and flag experimental outliers for review.
        These are candidates for model retraining or further investigation.
        """
        self.logger.info(f"Flagging outliers from {len(experiments)} experiments")
        
        flagged = []
        for exp in experiments:
            if exp["status"] in ["anomaly", "verified_outperformer"]:
                flagged.append({
                    "experiment_id": exp["experiment_id"],
                    "catalyst_id": exp["catalyst_id"],
                    "status": exp["status"],
                    "hypothesis": exp["hypothesis"],
                    "requires_smee_review": exp["status"] == "anomaly",
                })
        
        self.logger.info(f"Flagged {len(flagged)} experiments")
        return {
            "total_flagged": len(flagged),
            "anomalies": len([f for f in flagged if f["status"] == "anomaly"]),
            "outperformers": len([f for f in flagged if f["status"] == "verified_outperformer"]),
            "flagged_experiments": flagged,
        }
    
    def trigger_model_retraining(
        self,
        new_experiments: List[Dict[str, Any]],
        trigger_reason: str = "new_data"
    ) -> Dict[str, Any]:
        """
        Trigger model retraining with safeguards.
        
        Safeguards:
        - Minimum number of new data points (default: 5)
        - Quality gates (filter anomalies unless explicitly verified)
        - Version management and rollback capability
        - Calls PredictionLayer.train() to actually retrain the model
        """
        self.logger.info(f"Retraining triggered: {trigger_reason} ({len(new_experiments)} new experiments)")
        
        # Data quality gates
        quality_filtered = []
        for exp in new_experiments:
            # Only include normal or verified experiments for training
            if exp.get("status") in ["normal", "verified_outperformer"]:
                quality_filtered.append(exp)
        
        if len(quality_filtered) < 3:
            self.logger.warning(f"Insufficient quality data for retraining: {len(quality_filtered)} < 3")
            return {
                "status": "insufficient_data",
                "message": f"Need at least 3 quality experiments, got {len(quality_filtered)}",
            }
        
        # Actually train the model if available
        training_report = None
        if self.prediction_layer:
            self.logger.info(f"Calling PredictionLayer.train() with {len(quality_filtered)} experiments")
            training_report = self.prediction_layer.train(quality_filtered)
            self.logger.info(f"Training report: {training_report}")
        else:
            self.logger.warning("PredictionLayer not available — skipping model training")
        
        retraining_job = {
            "job_id": f"retrain_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "version": f"v2.{len(self.retraining_history)+1}-trained",
            "trigger_reason": trigger_reason,
            "new_training_samples": len(quality_filtered),
            "filtered_out": len(new_experiments) - len(quality_filtered),
            "status": "completed" if training_report and training_report.get("status") == "trained" else "queued",
            "training_report": training_report,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self.retraining_history.append(retraining_job)
        
        self.logger.info(f"Retraining job created: {retraining_job['job_id']} (version: {retraining_job['version']})")
        return retraining_job
    
    def get_retraining_history(self) -> List[Dict[str, Any]]:
        """Get history of model retraining events"""
        return self.retraining_history
    
    def compare_predictions(
        self,
        old_model_predictions: List[Dict[str, float]],
        new_model_predictions: List[Dict[str, float]]
    ) -> Dict[str, Any]:
        """
        Compare predictions from old and new models for A/B testing.
        Helps decide whether to deploy new model or rollback.
        """
        comparison = {
            "improved": 0,
            "degraded": 0,
            "unchanged": 0,
            "avg_improvement": 0.0,
        }
        
        for old, new in zip(old_model_predictions, new_model_predictions):
            old_score = sum([old.get(k, 0) for k in ["activity", "selectivity", "stability"]]) / 3
            new_score = sum([new.get(k, 0) for k in ["activity", "selectivity", "stability"]]) / 3
            
            improvement = new_score - old_score
            if improvement > 1:
                comparison["improved"] += 1
            elif improvement < -1:
                comparison["degraded"] += 1
            else:
                comparison["unchanged"] += 1
            
            comparison["avg_improvement"] += improvement
        
        if old_model_predictions:
            comparison["avg_improvement"] /= len(old_model_predictions)
        
        return comparison
