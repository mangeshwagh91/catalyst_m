# Catalyst AI Platform - Current Project Audit

**Date:** May 11, 2026  
**Assessment Type:** Code-verified repository audit  
**Confidence Level:** High for implemented surfaces; medium for end-to-end runtime validation  
**Overall Status:** Functional full-stack demo with real retraining and JWT auth, but not yet production-ready

## Executive Summary

The project has moved well beyond the original proof-of-concept state. The retraining loop is now real, the app has multi-user JWT authentication, and the hardcoded researcher identity has been removed from the workspace UI. The platform still has a few visible gaps, most notably the missing 3D molecular viewer, partial ownership enforcement, and limited external data integration in the main workflow.

**Overall completion: 72%**

| Area             | Completion | Status                                                                 |
| ---------------- | ---------: | ---------------------------------------------------------------------- |
| Core Workflow    |        90% | End-to-end flow is functional                                          |
| AI / ML Layer    |        78% | Real retraining exists, but model is still linear and physics-informed |
| Data Layer       |        65% | Database-backed, with some external API stubs still unused             |
| Feedback Loop    |        90% | Experiment logging, comparison, and retraining all work                |
| Visualizations   |        60% | Charts work; 3D molecular viewer is still missing                      |
| Collaboration    |        55% | JWT auth exists; full sharing and ACLs are incomplete                  |
| Code Quality     |        70% | Strong structure, but some hardcoded logic remains                     |
| Production Ready |        40% | Usable demo, not yet hardened for production                           |

## What Changed Since the Original Audit

### 1. Model retraining is now real

The biggest correction is that the feedback loop no longer just records retraining jobs. The backend now evaluates the model before and after retraining, trains on quality experiments, persists model state, and uses the latest trained model for subsequent predictions.

Verified surfaces:

- `backend/app/layers/feedback_layer.py`
- `backend/app/api/experiments.py`
- `backend/app/api/predictions.py`

### 2. Multi-user authentication is implemented

JWT-based auth now exists end to end. Users can register, log in, fetch their profile, and the frontend stores the access token and loads the authenticated user on startup.

Verified surfaces:

- `backend/app/core/security.py`
- `backend/app/api/auth.py`
- `backend/app/models/models.py`
- `frontend/src/hooks/useAuth.ts`
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/routes/login.tsx`
- `frontend/src/routes/workspace.tsx`

### 3. The hardcoded researcher identity was removed

The workspace header no longer shows a fixed name like “Dr. Sharma”. It now displays the authenticated user’s full name and email from the auth context.

## Workflow Analysis

### Step 1: Reaction entry works

Users can still create reactions and persist them in the database. This remains functional and is the entry point for the discovery workflow.

### Step 2: Known catalyst retrieval is still largely static

The audit remains correct that the main catalyst discovery path still relies heavily on a fixed known-catalyst set. The project has endpoints for external sources, but the primary workflow is not yet dynamically sourcing catalysts from those systems.

### Step 3: Candidate generation now includes a trained VAE

The generative layer now loads a tiny offline-trained variational autoencoder to produce novel compositions, while still preserving the existing heuristic fallback when weights are unavailable.

### Step 4: Ranking now supports the latest trained model

Predictions are no longer frozen behind static coefficients. The prediction endpoint reloads the latest model state before ranking or single-catalyst prediction, so retraining now has a real downstream effect.

### Step 5: Visualizations work, but the 3D viewer is still missing

Charts and dashboard visualizations remain functional. However, the repo still does not contain a real 3D molecular viewer component, so the platform still lacks the structure visualization that a molecular discovery product should have.

### Step 6: Export is functional

Candidate export remains available from the frontend and is still a working part of the workflow.

### Step 7: Experiment logging works

Experimental results are written to the database with measured and predicted values plus deviations. This part of the feedback loop is solid.

### Step 8: Discrepancy analysis works

The feedback layer continues to classify anomalies and outperformers and generate hypotheses from prediction-vs-observation gaps.

### Step 9: Retraining now changes model state

This is the most important correction versus the original audit. Retraining is no longer theater. The system now:

- filters quality experiments
- evaluates baseline performance
- trains the model
- evaluates the updated model
- stores version history
- uses the latest model for future predictions

## AI / ML Layer

The ML layer is now materially functional, but it is still not a modern deep-learning stack.

What is real now:

- model retraining on experimental data
- before/after metrics such as MAE and R²
- persistent model versioning
- latest-model loading in prediction endpoints

What is still heuristic or limited:

- candidate generation remains rule-based
- the core predictor is still a linear / physics-informed model rather than a learned GNN or sequence model
- external datasets are not yet driving the main workflow

## Data Layer

The database layer remains the backbone of the app and is now more useful because the feedback loop actually consumes stored experiment history.

Still true:

- reactions, predictions, experiments, and model versions persist in the database
- experiment deviations are recorded
- model version history is stored

Still incomplete:

- external sources such as Materials Project and UniProt are not yet first-class inputs to the main workflow
- catalyst retrieval is still largely driven by local logic rather than live data integration

## Authentication and Ownership

This area has improved significantly.

Implemented:

- JWT login and registration
- auth context on the frontend
- localStorage token persistence
- logout flow
- current-user display in the workspace
- creator_id on Reaction and Experiment models

Still incomplete:

- protection is not yet enforced uniformly across every API route
- Catalyst ownership is not fully modeled in the schema
- team sharing / shared_with semantics are not implemented
- audit logging and role-based access control are still missing

## Visualizations

Working now:

- candidate ranking displays
- activity/selectivity and stability charts
- model feedback charts
- experiment and history views

Still missing:

- true 3D molecular viewer
- structure-driven catalyst inspection
- richer pathway or molecular interaction visualizations

## Security and Production Readiness

The app is better than before, but not production-hardened.

Positive changes:

- password hashing via bcrypt
- signed JWTs
- authenticated frontend session handling
- data ownership fields in key tables

Remaining concerns:

- not all routes appear to enforce auth yet
- no full permission model
- secrets and environment handling still need production review
- no rate limiting or audit trail

## Revised Scorecard

```
Core Workflow:           90%
AI/ML Layer:             78%
Data Layer:              65%
Feedback Loop:           90%
Visualizations:          60%
Collaboration:           55%
Code Quality:            70%
Production Readiness:    40%

OVERALL:                 72%
```

## What Judges Will See Now

What improved:

- the platform really trains from experiment data
- the latest model is used for predictions
- multiple users can sign in instead of sharing a single hardcoded identity
- the dashboard now reflects a real learning loop instead of just version increments

What will still stand out as unfinished:

- no true 3D molecular viewer
- heuristic candidate generation rather than a learned generative model
- incomplete permissions and sharing
- external databases not yet fully integrated into the main flow

## Final Verdict

This is now a strong functional demo with a genuine feedback loop and real authentication. It is no longer fair to call the project “just theater” for retraining, and it is no longer single-user only. The remaining gaps are mostly product depth and production hardening rather than the core learning loop itself.

**Current assessment: demo-ready, partially collaborative, not production-ready.**
