#!/usr/bin/env python3
"""
End-to-End Test Script for Model Retraining Pipeline
Tests the complete workflow from logging experiments to retraining and predictions.
"""

import requests
import json
from datetime import datetime
import time

BASE_URL = "http://localhost:8000"

# Test configuration
TEST_REACTION_ID = "test_eth_jet"
TEST_EXPERIMENTS = [
    {
        "reaction_id": TEST_REACTION_ID,
        "catalyst_id": "cat_cu_zn_001",
        "measured_properties": {"activity": 72, "selectivity": 94, "stability": 82},
        "predicted_properties": {"activity": 65, "selectivity": 88, "stability": 75},
        "researcher_name": "Test User 1",
        "notes": "First experiment - catalyst performed well"
    },
    {
        "reaction_id": TEST_REACTION_ID,
        "catalyst_id": "cat_cu_zn_002",
        "measured_properties": {"activity": 68, "selectivity": 91, "stability": 80},
        "predicted_properties": {"activity": 62, "selectivity": 86, "stability": 73},
        "researcher_name": "Test User 2",
        "notes": "Second experiment"
    },
    {
        "reaction_id": TEST_REACTION_ID,
        "catalyst_id": "cat_pt_ni_001",
        "measured_properties": {"activity": 58, "selectivity": 85, "stability": 88},
        "predicted_properties": {"activity": 55, "selectivity": 82, "stability": 85},
        "researcher_name": "Test User 1",
        "notes": "Third experiment - good stability"
    },
    {
        "reaction_id": TEST_REACTION_ID,
        "catalyst_id": "cat_pt_ni_002",
        "measured_properties": {"activity": 62, "selectivity": 89, "stability": 86},
        "predicted_properties": {"activity": 59, "selectivity": 87, "stability": 83},
        "researcher_name": "Test User 2",
        "notes": "Fourth experiment"
    },
    {
        "reaction_id": TEST_REACTION_ID,
        "catalyst_id": "cat_cu_al_001",
        "measured_properties": {"activity": 75, "selectivity": 96, "stability": 79},
        "predicted_properties": {"activity": 70, "selectivity": 90, "stability": 76},
        "researcher_name": "Test User 1",
        "notes": "Fifth experiment - high activity and selectivity"
    },
    {
        "reaction_id": TEST_REACTION_ID,
        "catalyst_id": "cat_cu_al_002",
        "measured_properties": {"activity": 70, "selectivity": 92, "stability": 81},
        "predicted_properties": {"activity": 66, "selectivity": 89, "stability": 78},
        "researcher_name": "Test User 2",
        "notes": "Sixth experiment"
    }
]

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_success(message):
    """Print a success message"""
    print(f"✓ {message}")

def print_error(message):
    """Print an error message"""
    print(f"✗ {message}")

def print_info(message):
    """Print an info message"""
    print(f"ℹ {message}")

def test_log_experiments():
    """Test 1: Log experimental results"""
    print_section("TEST 1: Log Experimental Results")
    
    logged_ids = []
    for exp in TEST_EXPERIMENTS:
        try:
            response = requests.post(
                f"{BASE_URL}/api/experiments/log-results",
                json=exp,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            exp_id = data.get("experiment", {}).get("id")
            logged_ids.append(exp_id)
            print_success(f"Logged experiment for {exp['catalyst_id']}")
        except Exception as e:
            print_error(f"Failed to log experiment: {str(e)}")
            return False
    
    print_info(f"Total experiments logged: {len(logged_ids)}")
    return True

def test_check_summary():
    """Test 2: Check experiment summary"""
    print_section("TEST 2: Check Experiment Summary")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/experiments/summary",
            params={"reaction_id": TEST_REACTION_ID},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        total = data.get("total_experiments", 0)
        by_status = data.get("experiments_by_status", {})
        
        print_success(f"Total experiments: {total}")
        print_info(f"Normal: {by_status.get('normal', 0)}")
        print_info(f"Verified outperformers: {by_status.get('verified_outperformer', 0)}")
        print_info(f"Anomalies: {by_status.get('anomaly', 0)}")
        
        return total >= len(TEST_EXPERIMENTS)
    except Exception as e:
        print_error(f"Failed to get summary: {str(e)}")
        return False

def test_trigger_retraining():
    """Test 3: Trigger model retraining"""
    print_section("TEST 3: Trigger Model Retraining")
    
    try:
        # Prepare experiments in the format expected by the API
        retraining_exps = []
        for exp in TEST_EXPERIMENTS:
            retraining_exps.append({
                "catalyst_id": exp["catalyst_id"],
                "reaction_id": exp["reaction_id"],
                "measured_activity": exp["measured_properties"]["activity"],
                "measured_selectivity": exp["measured_properties"]["selectivity"],
                "measured_stability": exp["measured_properties"]["stability"],
                "predicted_activity": exp["predicted_properties"]["activity"],
                "predicted_selectivity": exp["predicted_properties"]["selectivity"],
                "predicted_stability": exp["predicted_properties"]["stability"],
                "status": "normal"
            })
        
        response = requests.post(
            f"{BASE_URL}/api/experiments/trigger-retraining",
            json={
                "new_experiments": retraining_exps,
                "trigger_reason": "automated_test",
                "use_all_quality_experiments": False
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("success"):
            print_success("Retraining triggered successfully")
            
            # Display job info
            job = data.get("retraining_job", {})
            print_info(f"Job ID: {job.get('job_id')}")
            print_info(f"Model Version: {job.get('version')}")
            print_info(f"Status: {job.get('status')}")
            print_info(f"Training Samples: {job.get('training_samples')}")
            
            # Display evaluation metrics
            eval_data = data.get("evaluation", {})
            before = eval_data.get("before", {})
            after = eval_data.get("after", {})
            improvement = eval_data.get("improvement", {})
            
            print_info("\nBefore Training:")
            print_info(f"  MAE: {before.get('overall_mae')}")
            print_info(f"  R²:  {before.get('overall_r2')}")
            
            print_info("\nAfter Training:")
            print_info(f"  MAE: {after.get('overall_mae')}")
            print_info(f"  R²:  {after.get('overall_r2')}")
            
            print_info("\nImprovement:")
            print_info(f"  MAE Improvement: {improvement.get('mae_improvement')} "
                      f"({improvement.get('mae_percent_change')}%)")
            print_info(f"  R² Improvement: {improvement.get('r2_improvement')} "
                      f"({improvement.get('r2_percent_change')}%)")
            
            return True
        else:
            print_error(f"Retraining failed: {data.get('error')}")
            return False
    except Exception as e:
        print_error(f"Failed to trigger retraining: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_check_model_evaluation():
    """Test 4: Check model evaluation metrics"""
    print_section("TEST 4: Check Model Evaluation Metrics")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/experiments/model-evaluation",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        if data.get("status") == "success":
            model = data.get("current_model", {})
            print_success("Retrieved model evaluation metrics")
            print_info(f"Current Version: {model.get('current_version')}")
            print_info(f"Training Samples: {model.get('training_samples')}")
            print_info(f"Accuracy Score (R²): {model.get('accuracy_score')}")
            print_info(f"Accuracy Improvement: {model.get('accuracy_improvement')}")
            print_info(f"Status: {model.get('status')}")
            print_info(f"Model Improved: {data.get('model_improved')}")
            return True
        else:
            print_info(f"No trained models yet: {data.get('message')}")
            return True  # Not a failure, just no models yet
    except Exception as e:
        print_error(f"Failed to get model evaluation: {str(e)}")
        return False

def test_model_info():
    """Test 5: Check model info endpoint"""
    print_section("TEST 5: Check Model Info")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/predictions/model-info",
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        
        print_success("Retrieved model information")
        print_info(f"Model Version: {data.get('version')}")
        print_info(f"Model Type: {data.get('model_type')}")
        print_info(f"Status: {data.get('status')}")
        
        trainable = data.get("trainable_model_info", {})
        print_info(f"Is Trained: {trainable.get('is_trained')}")
        print_info(f"Training Samples: {trainable.get('n_training_samples')}")
        print_info(f"Model State Loaded from Disk: {trainable.get('model_state_loaded_from_disk')}")
        
        return True
    except Exception as e:
        print_error(f"Failed to get model info: {str(e)}")
        return False

def test_predictions():
    """Test 6: Make predictions with updated model"""
    print_section("TEST 6: Make Predictions with Updated Model")
    
    try:
        # Create test catalysts
        catalysts = [
            {
                "id": "test_cu_zn",
                "name": "Cu-Zn Catalyst",
                "composition": "Cu0.6Zn0.4",
                "source": "known"
            },
            {
                "id": "test_pt_ni",
                "name": "Pt-Ni Catalyst",
                "composition": "Pt0.3Ni0.7",
                "source": "known"
            }
        ]
        
        response = requests.post(
            f"{BASE_URL}/api/predictions/rank",
            json={
                "catalysts": catalysts,
                "reaction_conditions": {
                    "temperature": 523.15,
                    "pressure": 50.0,
                    "solvent": "water"
                },
                "reaction_id": TEST_REACTION_ID
            },
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        
        print_success("Made predictions successfully")
        
        model_info = data.get("model_info", {})
        print_info(f"Model Used: {model_info.get('version')}")
        print_info(f"Is Trained: {model_info.get('is_trained')}")
        print_info(f"Training Samples: {model_info.get('training_samples')}")
        print_info(f"Avg Uncertainty: {model_info.get('avg_uncertainty')}")
        
        predictions = data.get("predictions", [])
        print_info(f"\nRanked {len(predictions)} catalysts:")
        for pred in predictions[:3]:
            print_info(f"  #{pred.get('rank')}. {pred.get('catalyst_name')} "
                      f"(score: {pred.get('combined_score')})")
        
        return True
    except Exception as e:
        print_error(f"Failed to make predictions: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("\n" + "█"*80)
    print("█" + " "*78 + "█")
    print("█" + "  Model Retraining End-to-End Test Suite".center(78) + "█")
    print("█" + " "*78 + "█")
    print("█"*80)
    
    print(f"\nTarget API: {BASE_URL}")
    print(f"Test started: {datetime.now().isoformat()}")
    
    # Run all tests
    tests = [
        ("Log Experiments", test_log_experiments),
        ("Check Summary", test_check_summary),
        ("Trigger Retraining", test_trigger_retraining),
        ("Check Model Evaluation", test_check_model_evaluation),
        ("Check Model Info", test_model_info),
        ("Make Predictions", test_predictions),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print_error(f"Test crashed: {str(e)}")
            results[test_name] = False
        time.sleep(0.5)  # Small delay between tests
    
    # Print summary
    print_section("TEST SUMMARY")
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "✓" if result else "✗"
        print(f"{symbol} {test_name}: {status}")
    
    print_info(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("\n🎉 All tests passed! Model retraining pipeline is working correctly.")
        return 0
    else:
        print_error(f"\n❌ {total - passed} test(s) failed. See details above.")
        return 1

if __name__ == "__main__":
    exit(main())
