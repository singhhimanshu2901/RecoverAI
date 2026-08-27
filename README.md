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
| Revenue at risk | ₹28,14,392 |
| Revenue recovered | ₹13,62,187 |
| Recovery rate | 67.4% |
| Incremental recovery vs. baseline | ₹6,50,730 |
| Median time to recovery | 3h 7m |
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
| Recovery scoring | Rule-based probability model (swappable for XGBoost) |
| Policy engine | Deterministic — hard caps on retries, messages, cooldown, window |
| Frontend | React + Vite, deployed on Vercel |
| Dataset | 500 synthetic recovery cases, AI cohort vs. baseline cohort |

## 4. Why This Needed AI (Not Just a Retry Script)

A rule like "payment failed → send reminder" ignores context. RecoverAI's
AI layer:
- **Diagnoses** the failure category from the error code and context
- **Scores** recovery probability using customer history, subscription age,
  and failure type
- **Prioritizes** by *expected value* (amount × probability − cost), not
  raw amount — a ₹10,000 case at 70% probability can outrank a ₹1,00,000
  case at 15% probability
- **Selects** the next-best-action from an approved, bounded set

The policy engine then either authorizes or rejects that recommendation
before anything reaches a customer or a payment gateway.

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
not just total money moved.

## 7. Demo Script (3–5 minutes)

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
6. **Open `/docs` (FastAPI Swagger)** — show the actual API: `POST
   /events/payment-failed`, `POST /recovery/analyze`, `POST
   /recovery/execute`, `POST /recovery/verify`. This is a real, callable
   backend, not a mockup.
7. **Close on the audit tab** — every decision is logged with a policy
   version, timestamp, and outcome. Nothing is a black box.

## 8. One-Minute Pitch

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

## 9. Anticipated Judge Questions

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

**Is this production-ready?**
This prototype runs on sandbox/synthetic data end-to-end (FastAPI backend,
persistent Postgres, live React dashboard). Production would add real
Razorpay sandbox/live integration, merchant auth, and larger-scale
validation — the architecture (adapter layer between AI logic and payment
API) is already designed for that swap.

## 10. What's Deliberately Out of Scope (v1)

- Real-money transactions (sandbox/synthetic only)
- Unlimited retries or messaging
- Hinglish voice recovery (planned Phase 3, not needed for the core loop)
- Direct LLM access to payment APIs

## 11. Repository Structure

```
recoverai/
├── app/                    # FastAPI backend
│   ├── main.py              # API endpoints
│   ├── models.py             # SQLAlchemy models
│   ├── recovery_engine.py    # Scoring + policy engine (core logic)
│   ├── schemas.py            # Pydantic request/response schemas
│   └── database.py           # DB connection (SQLite local / Postgres prod)
├── frontend/                # React + Vite dashboard
│   └── src/App.jsx
├── generate_dataset.py      # Synthetic dataset generator (baseline + AI cohorts)
├── requirements.txt
└── render.yaml
```
