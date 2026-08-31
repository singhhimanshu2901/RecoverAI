# RecoverAI — Intelligent Revenue Recovery Agent
**Track 03 — AI Revenue Recovery | Razorpay AI Builder Hackathon**

Live demo: https://recover-ai-2901.vercel.app
API: https://recoverai-soqt.onrender.com/docs

---

## 1. What RecoverAI Does

When a payment fails — a subscription renewal, a one-time checkout, a card
decline — most systems stop at "send a reminder." RecoverAI closes the full
loop:

**detect → diagnose → score → decide → act → verify → measure**

The AI layer never touches money directly. It *recommends* a diagnosis,
a recovery probability, and a next-best-action. A deterministic **policy
engine** is the only thing authorized to approve and execute that action —
with hard limits on retries, messages, cooldowns, and recovery windows.
Every step is logged to an audit trail.

## 2. Live Results (current batch)

| Metric | Value |
|---|---|
| Revenue at risk | ₹27,34,692 |
| Revenue recovered | ₹11,53,976 |
| Recovery rate | 65.7% |
| Incremental recovery vs. baseline | ₹5,51,469 |
| Median time to recovery | 3h 10m |
| Cases in batch | 500 (synthetic, sandbox) |

These numbers update live on the dashboard as new payment-failed events are
processed through the pipeline.

## 3. System Architecture

```
Payment Event → FastAPI Ingestion → Revenue-at-Risk Detector → Recovery Case
     → AI Diagnosis + Scoring → Next-Best-Action Engine → Policy Gate
     → Action Execution (Retry / Payment Link / Reminder / Escalate)
     → Outcome Verification → Recovered Revenue → Audit Trail + Dashboard
```

| Layer | Technology |
|---|---|
| Backend API | FastAPI (Python), deployed on Render |
| Database | PostgreSQL (Neon, persistent) |
| Recovery scoring | XGBoost model (one-hot features, cross-validated) with automatic rule-based fallback |
| Policy engine | Deterministic — hard caps on retries, messages, cooldown, window |
| Payment provider | Razorpay sandbox adapter — real test-mode API if credentials are set, transparent mock mode otherwise |
| Frontend | React + Vite, deployed on Vercel — 5 screens (Overview, Recovery Queue, Analytics, Audit, System) |
| Dataset | 500 synthetic recovery cases, AI cohort vs. baseline cohort |

## 4. Why This Needed AI (Not Just a Retry Script)

A rule like "payment failed → send reminder" ignores context. RecoverAI's
AI layer:
- **Diagnoses** the failure category from the error code and context
- **Scores** recovery probability using a trained XGBoost model (customer
  history, subscription age, failure type — one-hot encoded, cross-validated)
  that automatically falls back to a transparent rule-based scorer if the
  model is unavailable or errors during inference
- **Prioritizes** by *expected value* (amount × probability − cost), not
  raw amount — a ₹10,000 case at 70% probability can outrank a ₹1,00,000
  case at 15% probability
- **Selects** the next-best-action from an approved, bounded set

The policy engine then either authorizes or rejects that recommendation
before anything reaches a customer or a payment gateway. The `/model/status`
endpoint (and the dashboard's **System** tab) always shows which scoring
mode and payment-provider mode are currently active — nothing is hidden.

## 5. Safety & Bounded Automation

- Max 2 retries per case, max 2 outreach messages, 6-hour cooldown between
  interventions, 72-hour maximum recovery window
- No arbitrary discounts, no unlimited retries, no LLM with direct payment
  API access — the LLM/scoring layer only proposes
- High-value or ambiguous cases route to `HUMAN_REVIEW` automatically
- If a payment outcome can't be verified, the case goes to
  `VERIFY_PENDING` and automation pauses — **RecoverAI never claims a
  recovery without a verified outcome**
- Every action, decision, and policy check is written to an immutable
  audit trail (`GET /audit`)

## 6. Recovery Attribution (proving the money was actually recovered)

Every intervention gets a unique ID and timestamp. A payment is only
counted as *agent-recovered* if it succeeds after the intervention within
the attribution window. We run two cohorts side by side:
- **Baseline cohort** — simulates a naive, fixed reminder strategy (how
  merchants recover today)
- **AI cohort** — full RecoverAI pipeline

The dashboard reports both **gross recovery** and **incremental recovery**
(AI cohort minus baseline) so the actual uplift from the agent is visible,
not just total money moved. The **Analytics** tab breaks this down further
by failure reason and by recommended action, so it's clear *which*
interventions and *which* failure types drive the recovered revenue.

## 7. Dashboard Screens

| Screen | What it shows |
|---|---|
| **Overview** | Live recovery pulse, headline metrics, baseline vs. AI chart |
| **Recovery Queue** | Filterable/searchable live case list with score, expected value, action, status |
| **Analytics** | Revenue recovered by action taken, recovery rate by failure reason, case status distribution |
| **Audit** | Full immutable event log across all cases (policy version, timestamps, outcomes) |
| **System** | Which scoring engine (XGBoost vs. rule-based) and payment-provider mode (live sandbox vs. mock) are active right now, plus the hard-coded policy limits |

Clicking any case in the Recovery Queue opens a detail view with the AI
reasoning (score, expected value, recommended action) and that case's full
audit trail.

## 8. Demo Script (3–5 minutes)

1. **Open the dashboard** (`recover-ai-2901.vercel.app`) — the pulse header
   shows ₹13.6L already recovered of ₹28.1L at risk in this batch.
2. **Point to the Overview tab** — recovery rate (67.4%), incremental
   recovery vs. baseline (₹6.5L), and median time to recovery (3h 7m).
3. **Open the Recovery Queue tab** — show a live case: amount, recovery
   score, expected value, recommended action, status.
4. **Click into one case** — walk through the AI reasoning panel (recovery
   score, expected value, recommended action) and the full audit trail for
   that case: created → analyzed → policy-approved → action executed →
   verified → recovered.
5. **Show the Baseline vs. RecoverAI chart** — this is the proof: the AI
   cohort recovers meaningfully more than the naive baseline on the same
   at-risk revenue.
6. **Open the Analytics tab** — recovery rate broken down by failure
   reason, and revenue recovered broken down by which action was taken.
   This shows the system isn't a black box about *why* money came back.
7. **Open the System tab** — shows exactly which scoring engine (XGBoost
   model vs. rule-based fallback) and which payment-provider mode (live
   Razorpay sandbox vs. mock) are active right now, plus the hard policy
   limits. Full transparency, nothing hidden from the judges.
8. **Open `/docs` (FastAPI Swagger)** — show the actual API: `POST
   /events/payment-failed`, `POST /recovery/analyze`, `POST
   /recovery/execute`, `POST /recovery/verify`. This is a real, callable
   backend, not a mockup.
9. **Close on the Audit tab** — every decision is logged with a policy
   version, timestamp, and outcome. Nothing is a black box.

## 9. One-Minute Pitch

> RecoverAI is an AI revenue-recovery agent for merchants. When a payment
> fails, it doesn't just raise an alert — it diagnoses the failure,
> estimates whether the money is recoverable, decides the next best
> action, executes it within strict merchant-defined limits, verifies the
> outcome, and stops when recovery succeeds or human review is needed. We
> measure results across a batch: revenue at risk, actual money recovered,
> recovery rate, and incremental recovery over a naive baseline. Every
> action is explainable, bounded, and auditable — right now, live, it has
> recovered ₹13.6L of ₹28.1L at risk across 500 sandbox cases, a 67.4%
> recovery rate.

## 10. Anticipated Judge Questions

**How do you prove the agent recovered the money?**
Each intervention has a unique ID and timestamp; we verify the payment
status afterward and compare against a baseline/no-intervention cohort to
isolate incremental impact.

**Why AI instead of a retry script?**
The AI diagnoses failures, scores recoverability, prioritizes by expected
value, and picks among approved interventions — the policy engine, not the
AI, controls execution.

**Can the agent retry forever or spam customers?**
No — retry count, message count, cooldown, and recovery-window limits are
hard-coded, deterministic constraints enforced by the policy gate, not
suggestions to the model.

**What happens if payment status can't be verified?**
The case moves to `VERIFY_PENDING`, automation pauses, and it's queued for
human verification. The system never reports a recovery without evidence.

**How good is the ML model, really?**
Trained via 5-fold cross-validation on the current synthetic batch (~500
cases, ~190 with a resolved outcome). On a dataset this size the model
gives a modest but real lift over chance. We report cross-validated AUC
rather than a single train/test split because a single split on ~190 rows
is too noisy to trust on its own. If the model errors or underperforms,
`calculate_recovery_score()` automatically falls back to the transparent
rule-based scorer — the system is designed to never depend on the ML model
working. More historical data in production would directly improve it;
the training/serving code is already structured for that (`train_model.py`
retrains from live case outcomes with one command).

**Is this production-ready?**
This prototype runs on sandbox/synthetic data end-to-end (FastAPI backend,
persistent Postgres, live React dashboard). Production would add real
Razorpay live-mode integration (the adapter already supports real sandbox
credentials via env vars — it's a config change, not a rewrite), merchant
auth, and larger-scale validation.

## 11. What's Deliberately Out of Scope (v1)

- Real-money transactions (sandbox/synthetic only)
- Unlimited retries or messaging
- Hinglish voice recovery (planned Phase 3, not needed for the core loop)
- Direct LLM access to payment APIs

## 12. Repository Structure

```
recoverai/
├── app/                       # FastAPI backend
│   ├── main.py                  # API endpoints
│   ├── models.py                # SQLAlchemy models
│   ├── recovery_engine.py       # Scoring (ML + rule-based) + policy engine
│   ├── razorpay_adapter.py      # Payment provider adapter (live sandbox / mock)
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── database.py              # DB connection (SQLite local / Postgres prod)
│   └── model.pkl                # Trained XGBoost model (generated by train_model.py)
├── frontend/                  # React + Vite dashboard (5 screens)
│   └── src/App.jsx
├── generate_dataset.py        # Synthetic dataset generator (baseline + AI cohorts)
├── train_model.py             # Trains/retrains the XGBoost model from live case outcomes
├── requirements.txt
└── render.yaml
```