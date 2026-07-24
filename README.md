# Learning Harness

A complete reference implementation of a plug-and-play self-improving agent system that updates strategy files instead of fine-tuning model weights.

## What is implemented

- Existing **Player** agent for support-ticket routing
- Versioned JSON playbook stored in SQLite
- Fixed reference data, proven rules, trial rules and retired rules
- Structured episode logs with decisions, outcomes, latency, cost and reward
- Deterministic Reviewer with Confirmed / Falsified / Inconclusive decisions
- Champion-versus-challenger comparison
- Safe rollback by preserving the champion pointer
- Optional Watcher-style early stopping
- Audit trail
- FastAPI REST API
- Streamlit dashboard
- Docker Compose
- Unit tests

## Quick start with Python

```bash
python -m venv .venv
# Windows Git Bash:
source .venv/Scripts/activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

In another terminal:

```bash
streamlit run app/dashboard.py
```

Open:

- Dashboard: http://localhost:8501
- API documentation: http://localhost:8000/docs

## Quick start with Docker

```bash
docker compose up --build
```

## Demonstration flow

1. Open the dashboard.
2. Run 10–50 individual or simulated episodes.
3. Open **Review** and run the Reviewer.
4. Inspect the rule decision and champion/challenger outcome.
5. Open **Audit** to verify that every change is traceable.

## API examples

Run an episode:

```bash
curl -X POST http://localhost:8000/episodes \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "support-routing-agent",
    "input_context": {
      "subject": "Invoice API access request",
      "description": "Need an invoice for API usage",
      "expected_queue": "billing"
    }
  }'
```

Generate synthetic episodes:

```bash
curl -X POST "http://localhost:8000/simulate?count=100&success_bias=0.90"
```

Run the Reviewer:

```bash
curl -X POST "http://localhost:8000/review?min_relative_improvement=0.02&min_sample_size=10"
```

## Production extensions

Replace the deterministic Player with an existing LLM or multi-agent workflow. Keep the same contract:

- Read the champion playbook before each episode.
- Annotate decisions with rule IDs.
- Log a deterministic real-world outcome.
- Let the Reviewer evaluate trials only after their evaluation window.
- Require human approval for high-risk promotions.
- Keep fixed reference data immutable.
