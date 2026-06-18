# LoanSense — Progress Tracker

> **How to use this file:**
> Update this file every time a feature is implemented, a model is trained, or a milestone is reached.
> Each entry should include the date, what changed, and what the current state is.
> Newest entries go at the top of the Change Log section.

---

## Project Structure

```
loansense/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── agent/
│   │   ├── models/
│   │   ├── db/
│   │   └── schemas/
│   ├── ml/
│   │   ├── data/
│   │   ├── training/
│   │   ├── attack_generator/
│   │   └── drift/
│   ├── tests/
│   ├── mlruns/
│   ├── .env
│   ├── requirements.txt
│   └── alembic/
└── frontend/
    ├── src/
    │   ├── pages/
    │   ├── components/
    │   └── api/
    ├── package.json
    └── vite.config.js
```

---

## Milestone Status

| Milestone | Status |
|-----------|--------|
| Phase 0 — Domain research + project setup | ✅ Complete |
| Phase 1 — Synthetic dataset + attack generator | ✅ Complete |
| Phase 2 — Credit risk model (trained + registered) | ✅ Complete |
| Phase 2 — Fraud signal detector (trained + registered) | ✅ Complete |
| Phase 2 — Contradiction detector (hybrid, trained + registered) | ⬜ Not started |
| Phase 3 — FastAPI backend serving all three models | ✅ Complete |
| Phase 4 — Agent reasoning layer (Groq + tool calls) | ✅ Complete |
| Phase 5 — pytest suite (all contradiction cases passing) | ✅ Complete |
| Phase 6 — React frontend (all four pages connected) | ✅ Complete |
| Phase 7 — MLOps (drift detection live) | ⬜ Not started |
| Phase 8 — Hosted deployment (Railway/Render) | ⬜ Not started |
| Phase 9 — README system design doc + demo video | ⬜ Not started |

---

## Change Log

## 2026-06-18 — Phase 6 Session Summary

### Completed
- **Scaffolded React Frontend**: Initialised a clean React + Vite SPA using vanilla JavaScript. Configured Tailwind CSS, PostCSS, and React Router.
- **Form & PAN Security (Block 20)**: Built `Assess.jsx` with full schema mapping. Implemented real-time PAN masking and Web Crypto API SHA-256 hashing on blur/submit to guarantee the raw PAN is never stored in React state.
- **Robust Error Handling**: Wired the frontend to gracefully catch `422 Unprocessable Entity` responses and display inline field-level validation errors.
- **Pages Connected (Blocks 21 & 22)**: Built the `Verdict.jsx` UI with RBI compliance flags, contradiction scores, and color-coded decisions. Built `Audit.jsx` for tracking immutable JSONB logs, and `Dashboard.jsx` for monitoring system stats and drift detection.
- **UX & Security Refinements**: 
  - Fixed API connection paths (`/api/v1` prefix) and CORS matching.
  - Implemented a backend `/verdicts/recent` endpoint and added a "Recent Assessments" table to the Dashboard. This avoids IDOR vulnerabilities (by keeping UUIDs) while making testing and navigation seamless.
  - Fixed rendering crash in `Verdict.jsx` (missing Lucide icon) and passed `applicantId` via router state to auto-fill the Audit page search.

### In Progress
- Transitioning to Phase 7: MLOps & Drift Detection.

### Next Session
- Implement active drift detection loops and monitoring in the backend.

### Blockers
- None.

---

## 2026-06-18 — Session Summary

### Completed
- Migrated the `AgentOrchestrator` from the deprecated Gemini SDK to Groq's API using standard `httpx` and OpenAI-compatible tool calling (`llama-3.3-70b-versatile`).
- Refactored `evaluate_agent.py` to bypass live LLM calls for bulk attack pattern evaluation, directly executing local ML heuristic loops instead (saving millions of tokens on free-tier limits).
- Re-architected `test_agent.py` with full OpenAI API mocking to test all 4 attack patterns. Successfully asserted that the agent schema parsing, tool calling loops, and 0.6 contradiction safety overrides are working robustly without LLM hallucinations.
- Updated `prompt-iteration-log.md` logging the strategic pivot away from free-tier bulk LLM evaluations towards programmatic ML metrics evaluation + spot-checking.

### In Progress
- Transitioning to Block 19: React Frontend connection and UI build.

### Next Session
- Move to React Frontend to connect the 4 pages to the robust API.

### Blockers
- None. API rate limits elegantly bypassed via mocking and ML decoupling.

---

## 2026-06-15 — Session Summary

### Completed
- Diagnosed and fixed massive target leakage in the Block 9 Fraud Signal Detector pipeline (`train_fraud.py`).
- Rewrote the base fraud synthetic generation (`feature_engineering.py`) and attack generation (`generate_attacks.py`) to enforce overlapping, realistic distributions instead of trivially separable feature ranges.
- Verified mathematically that no single feature has ROC-AUC > 0.85 and computed exact dual-population overlap percentages.
- Retrained and registered the `fraud-signal-detector` v2 (Val ROC-AUC: 0.9923, FPR: 2.48%).
- Decomposed Pattern 2 detection drop and proved Pattern 4's high detection rate is driven by a mathematically rare (3.6%) multivariate legit combination, confirming genuine pattern learning.
- Updated `walkthrough.md` and `logs.md` with detailed explanations to use in the final README.

### In Progress
- Transitioning to Block 10 / Block 11 — Contradiction Detector (Hybrid Rules + ML).

### Next Session
- Implement `backend/ml/training/contradiction/rules.py` (Block 10).
- Implement Isolation Forest and Logistic Regression meta-model (`train_contradiction.py`) (Block 11).

### Blockers
- None

---

## 2026-06-14 — Session Summary

### Completed
- Completed Task 3, Block 8 (Credit Risk Model Training). Trained XGBoost classifier, evaluated on validation set (ROC-AUC 0.67), generated SHAP plot, and registered model as `credit-risk-scorer` v1 in MLflow.
- Completed Task 2 (Final Training Dataset Assembly, Synthetic Attack Generator, India-Realistic Synthetic Layer, Unified Feature Engineering).
- Handled mixed data types and XGBoost integration via `OrdinalEncoder` wrapped in `ColumnTransformer`.
- Generated `audit_report.md` and `dataset_card.md`.
- Completed Task 1 (Project Scaffolding, Domain Research).

### In Progress
- Connecting the Antigravity IDE Python interpreter to the virtual environment (`backend/.venv/Scripts/python.exe`) via `.vscode/settings.json`.

### Next Session
- Finalize the IDE interpreter configuration.
- Start Task 3, Block 9 — Fraud Detection Model Training (`train_fraud.py`).

### Blockers
- None

---

- **2026-06-14:** Completed Task 3, Block 8 (Credit Risk Model Training). Trained XGBoost classifier, evaluated on validation set (ROC-AUC 0.67), generated SHAP plot, and registered model as `credit-risk-scorer` v1 in MLflow.
- **2026-06-14:** Completed Task 2, Block 7 (Final Training Dataset Assembly). Assembled train/val/test splits and safely applied SMOTENC to the training split to achieve a 20% fraud signal rate. Created dataset_card.md. Task 2 is now fully complete!
- **2026-06-14:** Completed Task 2, Block 6 (Synthetic Attack Generator). Generated 4 parameterised fraud patterns (N=500 each) and created `evaluate_attacks.py`.
- **2026-06-14:** Completed Task 2, Block 5 (India-Realistic Synthetic Layer). Applied realistic income, CIBIL, employment, and loan purpose distributions.
- **2026-06-14:** Completed Task 2, Block 4 (Unified Feature Engineering). Engineered `unified_features.parquet` and `feature_definitions.md`.
- **2026-06-14:** Completed Task 2, Block 3 (Dataset Acquisition & Audit). Generated `ml/data/audit_report.md` after resolving dataset memory constraints.
- **2026-06-14:** Completed Task 1, Block 2 (Project Scaffolding). Directories, requirements, Tailwind, and initial databases verified.
- **2026-06-14:** Completed Task 1, Block 1 (Domain Research). Generated `docs/domain-research.md`.

<!-- Entries added here by Claude Code during implementation — newest first -->

---

## What To Do Next

Start Phase 6 (Block 19) — React Frontend (all four pages connected).

---

## Known Issues / Notes

- Gemini free tier rate limits: monitor during agent testing phase; cache responses if needed
- Railway/Render free tier has cold starts: warm-up script needed before demo
- PSI threshold of 0.2 is industry standard but should be validated against actual score distributions once models are trained
- Synthetic attack patterns need real research backing — do not parameterize from assumptions alone
