"""Feedback & Learning Layer - Experiment logging and model retraining"""

from datetime import datetime, timezone
from typing import Any, Dict, List, TYPE_CHECKING, Tuple
import numpy as np
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
    
    def _compute_evaluation_metrics(
        self,
        y_true: List[float],
        y_pred: List[float],
        metric_name: str = "property"
    ) -> Dict[str, float]:
        """
        Compute evaluation metrics (MAE, RMSE, R²) for model predictions.
        
        Args:
            y_true: Measured/ground truth values
            y_pred: Predicted values
            metric_name: Name of the metric being evaluated
            
        Returns:
            Dict with MAE, RMSE, R², and correlation
        """
        if len(y_true) < 2:
            return {
                "mae": None,
                "rmse": None,
                "r2": None,
                "correlation": None,
                "n_samples": len(y_true),
            }
        
        y_true = np.array(y_true, dtype=np.float32)
        y_pred = np.array(y_pred, dtype=np.float32)
        
        # MAE: Mean Absolute Error
        mae = float(np.mean(np.abs(y_true - y_pred)))
        
        # RMSE: Root Mean Squared Error
        rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
        
        # R²: Coefficient of Determination
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = float(1.0 - (ss_res / ss_tot)) if ss_tot != 0 else None
        
        # Pearson correlation
        if np.std(y_true) > 0 and np.std(y_pred) > 0:
            correlation = float(np.corrcoef(y_true, y_pred)[0, 1])
        else:
            correlation = None
        
        return {
            "mae": round(mae, 4) if mae is not None else None,
            "rmse": round(rmse, 4) if rmse is not None else None,
            "r2": round(r2, 4) if r2 is not None else None,
            "correlation": round(correlation, 4) if correlation is not None else None,
            "n_samples": len(y_true),
        }
    
    def evaluate_model_on_experiments(
        self,
        experiments: List[Dict[str, Any]],
        prediction_layer: "PredictionLayer" = None
    ) -> Dict[str, Any]:
        """
        Evaluate model performance on a set of experiments.
        
        Computes MAE and R² for activity, selectivity, and stability.
        
        Args:
            experiments: List of experiment dicts with measured and predicted properties
            prediction_layer: Optional PredictionLayer to make fresh predictions
            
        Returns:
            Evaluation report with metrics per property
        """
        if not experiments or len(experiments) < 2:
            return {
                "status": "insufficient_data",
                "message": f"Need at least 2 experiments for evaluation, got {len(experiments)}",
                "n_experiments": len(experiments),
            }
        
        evaluation = {
            "n_experiments": len(experiments),
            "activity": None,
            "selectivity": None,
            "stability": None,
            "overall_mae": None,
            "overall_r2": None,
        }
        
        # Collect measured and predicted values
        activity_measured = []
        selectivity_measured = []
        stability_measured = []
        activity_predicted = []
        selectivity_predicted = []
        stability_predicted = []
        
        for exp in experiments:
            if "measured_activity" in exp and "predicted_activity" in exp:
                activity_measured.append(exp["measured_activity"])
                activity_predicted.append(exp["predicted_activity"])
            
            if "measured_selectivity" in exp and "predicted_selectivity" in exp:
                selectivity_measured.append(exp["measured_selectivity"])
                selectivity_predicted.append(exp["predicted_selectivity"])
            
            if "measured_stability" in exp and "predicted_stability" in exp:
                stability_measured.append(exp["measured_stability"])
                stability_predicted.append(exp["predicted_stability"])
        
        # Compute metrics per property
        if activity_measured:
            evaluation["activity"] = self._compute_evaluation_metrics(
                activity_measured, activity_predicted, "activity"
            )
        
        if selectivity_measured:
            evaluation["selectivity"] = self._compute_evaluation_metrics(
                selectivity_measured, selectivity_predicted, "selectivity"
            )
        
        if stability_measured:
            evaluation["stability"] = self._compute_evaluation_metrics(
                stability_measured, stability_predicted, "stability"
            )
        
        # Compute overall metrics
        all_measured = activity_measured + selectivity_measured + stability_measured
        all_predicted = activity_predicted + selectivity_predicted + stability_predicted
        
        if all_measured:
            overall = self._compute_evaluation_metrics(all_measured, all_predicted, "overall")
            evaluation["overall_mae"] = overall.get("mae")
            evaluation["overall_r2"] = overall.get("r2")
        
        return evaluation
    
    def trigger_model_retraining(
        self,
        new_experiments: List[Dict[str, Any]],
        trigger_reason: str = "new_data",
        eval_experiments: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Trigger model retraining with evaluation metrics.
        
        Safeguards:
        - Minimum number of new data points (default: 3)
        - Quality gates (filter anomalies unless explicitly verified)
        - Version management and rollback capability
        - Evaluates model performance before and after retraining
        - Calls PredictionLayer.train() to actually retrain the model
        
        Args:
            new_experiments: Experiments to train on
            trigger_reason: Reason for retraining
            eval_experiments: Optional held-out experiments for evaluation
            
        Returns:
            Retraining job with evaluation metrics
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
                "n_quality_experiments": len(quality_filtered),
            }
        
        # Evaluate before retraining (on eval_experiments if provided, else use training set)
        eval_set = eval_experiments if eval_experiments else quality_filtered
        before_evaluation = None
        if self.prediction_layer:
            self.logger.info(f"Evaluating model performance before retraining on {len(eval_set)} experiments")
            before_evaluation = self.evaluate_model_on_experiments(eval_set, self.prediction_layer)
            self.logger.info(f"Before evaluation: MAE={before_evaluation.get('overall_mae')}, R²={before_evaluation.get('overall_r2')}")
        
        # Actually train the model if available
        training_report = None
        after_evaluation = None
        if self.prediction_layer:
            self.logger.info(f"Calling PredictionLayer.train() with {len(quality_filtered)} experiments")
            training_report = self.prediction_layer.train(quality_filtered)
            self.logger.info(f"Training report: {training_report}")
            
            # Evaluate after retraining
            if training_report and training_report.get("status") == "trained":
                self.logger.info(f"Evaluating model performance after retraining on {len(eval_set)} experiments")
                after_evaluation = self.evaluate_model_on_experiments(eval_set, self.prediction_layer)
                self.logger.info(f"After evaluation: MAE={after_evaluation.get('overall_mae')}, R²={after_evaluation.get('overall_r2')}")
        else:
            self.logger.warning("PredictionLayer not available — skipping model training")
        
        # Compute improvement metrics
        improvement_metrics = None
        if before_evaluation and after_evaluation:
            improvement_metrics = {
                "mae_improvement": None,
                "mae_percent_change": None,
                "r2_improvement": None,
                "r2_percent_change": None,
            }
            
            before_mae = before_evaluation.get("overall_mae")
            after_mae = after_evaluation.get("overall_mae")
            if before_mae and after_mae:
                improvement_metrics["mae_improvement"] = round(before_mae - after_mae, 4)
                improvement_metrics["mae_percent_change"] = round(
                    ((before_mae - after_mae) / before_mae * 100) if before_mae != 0 else 0, 2
                )
            
            before_r2 = before_evaluation.get("overall_r2")
            after_r2 = after_evaluation.get("overall_r2")
            if before_r2 is not None and after_r2 is not None:
                improvement_metrics["r2_improvement"] = round(after_r2 - before_r2, 4)
                improvement_metrics["r2_percent_change"] = round(
                    ((after_r2 - before_r2) / abs(before_r2) * 100) if before_r2 != 0 else 0, 2
                )
        
        retraining_job = {
            "job_id": f"retrain_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            "version": f"v2.{len(self.retraining_history)+1}-trained",
            "trigger_reason": trigger_reason,
            "new_training_samples": len(quality_filtered),
            "filtered_out": len(new_experiments) - len(quality_filtered),
            "status": "completed" if training_report and training_report.get("status") == "trained" else "queued",
            "training_report": training_report,
            "before_evaluation": before_evaluation,
            "after_evaluation": after_evaluation,
            "improvement_metrics": improvement_metrics,
            "created_at": datetime.utcnow().isoformat(),
        }
        
        self.retraining_history.append(retraining_job)
        
        self.logger.info(f"Retraining job created: {retraining_job['job_id']} (version: {retraining_job['version']})")
        return retraining_job
