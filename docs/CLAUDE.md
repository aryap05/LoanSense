# LoanSense

## Workflow Orchestration

### 1. Plan Mode Default
* Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
* If something goes sideways, STOP and re-plan immediately
* Use plan mode for verification steps, not just building
* Write detailed specs upfront to reduce ambiguity

### 2. Subagent Strategy
* Use subagents liberally to keep main context window clean
* Offload research, exploration, and parallel analysis to subagents
* For complex problems, throw more compute at it via subagents
* One task per subagent for focused execution

### 3. Self-Improvement Loop
* After ANY correction from the user: update tasks/lessons.md with the pattern
* Write rules for yourself that prevent the same mistake
* Ruthlessly iterate on these lessons until mistake rate drops
* Review lessons at session start for relevant project

### 4. Verification Before Done
* Never mark a task complete without proving it works
* Diff behavior between main and your changes when relevant
* Ask yourself: "Would a staff engineer approve this?"
* Run tests, check logs, demonstrate correctness

### 5. Demand Elegance (Balanced)
* For non-trivial changes: pause and ask "is there a more elegant way?"
* If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
* Skip this for simple, obvious fixes — don't over-engineer it
* Challenge your own work before presenting it

### 6. Autonomous Bug Fixing
* When given a bug report: just fix it. Don't ask for hand-holding
* Point at logs, errors, failing tests — then resolve them
* Zero context switching required from the user

## Task Management
1. Plan First: Write plan to tasks/todo.md with checkable items
2. Verify Plan: Check in before starting implementation
3. Track Progress: Mark items complete as you go
4. Explain Changes: High-level summary at each step
5. Document Results: Add review section to tasks/todo.md
6. Capture Lessons: Update tasks/lessons.md after corrections

## Core Principles
* Simplicity First: Make every change as simple as possible. Impact minimal code
* No Laziness: Find root causes. No temporary fixes. Senior development standards
* Minimal Impact: Only touch what's necessary. No side effects with new bugs

---

## Project Architecture

LoanSense is an agentic underwriting intelligence system for Indian NBFCs. It jointly assesses credit risk and fraud signals, detects contradictions between them, and produces an explainable verdict via a Gemini-powered agent.

```
loansense/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI entrypoint
│   │   ├── routers/              # assess.py, verdicts.py, audit.py, health.py
│   │   ├── agent/                # orchestrator.py, tools.py, prompts.py
│   │   ├── models/               # credit.py, fraud.py, contradiction.py
│   │   ├── db/                   # database.py, schemas.py, crud.py
│   │   └── schemas/              # pydantic input/output models
│   ├── ml/
│   │   ├── data/                 # raw/, processed/, synthetic/
│   │   ├── training/             # train_credit.py, train_fraud.py, train_contradiction.py
│   │   ├── attack_generator/     # generate_attacks.py, patterns/
│   │   └── drift/                # psi.py, monitor.py
│   ├── tests/
│   │   ├── test_contradiction.py
│   │   ├── test_agent.py
│   │   ├── test_endpoints.py
│   │   └── test_db.py
│   ├── mlruns/                   # MLflow tracking directory
│   ├── .env                      # NEVER commit this
│   ├── requirements.txt
│   └── alembic/                  # DB migrations
└── frontend/
    ├── src/
    │   ├── pages/                # Dashboard, Assess, Verdict, Audit
    │   ├── components/
    │   └── api/                  # API client
    ├── package.json
    └── vite.config.js
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11 |
| ML Models | XGBoost + sklearn |
| Agent LLM | Gemini 1.5 Flash (Google AI Studio) |
| Backend | FastAPI + Uvicorn |
| ORM | SQLAlchemy + Alembic |
| Database | PostgreSQL |
| Experiment Tracking | MLflow |
| Frontend | React + Vite + Tailwind CSS |
| Testing | pytest |
| Hosting | Railway or Render |
| Data Generation | SDV + Faker |
| Explainability | SHAP + custom verdict schema |

## Environment Variables

All secrets in `.env`. Never hardcode. Never commit.

```
DATABASE_URL=postgresql://user:password@localhost:5432/loansense
GEMINI_API_KEY=your_key_here
MLFLOW_TRACKING_URI=./mlruns
ENVIRONMENT=development
```

## Coding Conventions

### Python
- All FastAPI route handlers use async def
- All DB operations through SQLAlchemy session — never raw SQL
- All external inputs validated through Pydantic schemas before any processing
- Sanitize all user-supplied text fields before passing to LLM context
- Type hints on all function signatures
- No print() in production code — use Python logging module

### Agent
- Temperature must be set to 0 on all Gemini calls (determinism)
- Structured output schema enforced — reject malformed responses and retry once
- All three model tools must be called before forming a verdict — no shortcuts
- Tool call results logged to audit_logs before agent produces verdict

### ML Models
- All training runs logged to MLflow (params, metrics, model artifact)
- Best model per component registered in MLflow Model Registry
- Models loaded from registry at FastAPI startup — never from raw pickle files
- SMOTE applied only on training split, never on validation or test

### Testing
- All contradiction test cases must be deterministic — same input, same verdict, every run
- Never mock the contradiction detector in contradiction tests — test the real model
- Prompt injection test must always be included and must always pass

### Database
- UUIDs for all primary keys
- created_at TIMESTAMPTZ on every table
- Never store raw PAN — store hashed only
- Soft deletes not needed for v1 — hard delete is fine
- All migrations through Alembic — never ALTER TABLE manually

### Frontend
- No inline styles — Tailwind utility classes only
- All API calls through a centralized api/ client module
- Loading and error states handled on every page
- Verdict badge colors: green=APPROVE, amber=FLAG_FOR_REVIEW, red=REJECT

## Security Rules (Non-Negotiable)
- `.env` in `.gitignore` before first commit
- No API keys in source code, comments, or commit messages
- All FastAPI endpoints validate input with Pydantic before any logic runs
- Loan purpose and employer description fields sanitized before LLM injection
- CORS restricted to frontend origin only — not wildcard in production

## MLflow Conventions
- Experiment names: `loansense-credit-risk`, `loansense-fraud-signal`, `loansense-contradiction`
- Model registry names: `credit-risk-scorer`, `fraud-signal-detector`, `contradiction-detector`
- Tag all runs with: `dataset_version`, `feature_set_version`, `python_version`

## Drift Detection Rules
- PSI threshold: 0.2 (standard industry threshold — verify this is appropriate)
- Check weekly against training score distribution baseline
- PSI > 0.2 on any model → write drift_alert to audit_logs → surface in dashboard
- Do not auto-retrain in v1 — alert only
