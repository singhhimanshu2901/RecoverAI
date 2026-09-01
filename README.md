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
| Payment provider | Real Razorpay test-mode API — live payment links + webhook-verified confirmation |
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

## 5. Real Payment Recovery (not simulated)

The core loop is a genuine, working integration with Razorpay's test-mode
API — this is not mocked for the live path:

1. A payment-failed event creates a recovery case
2. The AI scores it and recommends an action; the policy engine approves it
3. If the action is `PAYMENT_LINK`, RecoverAI calls the real Razorpay API
   and gets back a real, clickable payment link
4. When a customer completes that payment (even a test-mode UPI/card
   payment), Razorpay sends a real webhook to `/webhooks/razorpay`
5. RecoverAI verifies the webhook signature, matches it to the case via the
   payment link ID, and marks the case `RECOVERED` — with the outcome
   coming from Razorpay itself, not a simulated random draw

The bulk 500-case dataset (used for the batch metrics and baseline
comparison) is generated synthetically since running 500 real test
payments isn't practical — but the underlying mechanism (policy gate →
real payment link → real webhook → recovery) is fully live and can be
demonstrated end-to-end with a single real test-mode payment at any time.

## 6. Safety & Bounded Automation

- Max 2 retries per case, max 2 outreach messages, 6-hour cooldown between
  interventions, 72-hour maximum recovery window
- No arbitrary discounts, no unlimited retries, no LLM with direct payment
  API access — the LLM/scoring layer only proposes
- High-value or ambiguous cases route to `HUMAN_REVIEW` automatically
- If a payment outcome can't be verified, the case goes to
  `VERIFY_PENDING` and automation pauses — **RecoverAI never claims a
  recovery without a verified outcome**
- Webhook signatures are verified against a shared secret before any case
  is updated — unsigned or tampered webhook calls are rejected outright
- Every action, decision, and policy check is written to an immutable
  audit trail (`GET /audit`)

## 7. Recovery Attribution (proving the money was actually recovered)

Every intervention gets a unique ID and timestamp. A payment is only
counted as *agent-recovered* if it succeeds after the intervention within
the attribution window. We run two cohorts side by side:
- **Baseline cohort** — simulates a naive, fixed reminder strategy (how
  merchants recover today)
- **AI cohort** — full RecoverAI pipeline

The dashboard reports both **gross recovery** and **incremental recovery**
(AI cohort minus baseline) so the actual uplift from the agent is visible,
not just total money moved. The **Analytics** tab breaks this down further
by failure reason and by recommended action.

## 8. Dashboard Screens

| Screen | What it shows |
|---|---|
| **Overview** | Live recovery pulse, headline metrics, baseline vs. AI chart |
| **Recovery Queue** | Filterable/searchable live case list with score, expected value, action, status |
| **Analytics** | Revenue recovered by action taken, recovery rate by failure reason, case status distribution |
| **Audit** | Full immutable event log across all cases (policy version, timestamps, outcomes) |
| **System** | Which scoring engine (XGBoost vs. rule-based) and payment-provider mode are active right now, plus the hard-coded policy limits |

Clicking any case in the Recovery Queue opens a detail view with the AI
reasoning (score, expected value, recommended action) and that case's full
audit trail.

## 9. Demo Script (3–5 minutes)

1. **Open the dashboard** — the pulse header shows revenue already
   recovered of total at risk in this batch.
2. **Point to the Overview tab** — recovery rate, incremental recovery vs.
   baseline, and median time to recovery.
3. **Open the Recovery Queue tab** — show a live case: amount, recovery
   score, expected value, recommended action, status.
4. **Live real-payment moment**: trigger a fresh payment-failed case via
   `/docs`, let it get scored and approved, open the real Razorpay payment
   link it generates, and pay it (UPI test ID `success@razorpay`). Refresh
   the case in the dashboard — it flips to `RECOVERED` in real time, driven
   by Razorpay's actual webhook, not a simulated outcome.
5. **Show the Baseline vs. RecoverAI chart** — the AI cohort recovers
   meaningfully more than the naive baseline on the same at-risk revenue.
6. **Open the Analytics tab** — recovery rate by failure reason, and
   revenue recovered by which action was taken.
7. **Open the System tab** — shows exactly which scoring engine and
   payment-provider mode are active, plus the hard policy limits.
8. **Close on the Audit tab** — every decision is logged with a policy
   version, timestamp, and outcome.

## 10. One-Minute Pitch

> RecoverAI is an AI revenue-recovery agent for merchants. When a payment
> fails, it doesn't just raise an alert — it diagnoses the failure,
> estimates whether the money is recoverable, decides the next best
> action, executes it within strict merchant-defined limits, verifies the
> outcome via a real Razorpay webhook, and stops when recovery succeeds or
> human review is needed. We measure results across a batch: revenue at
> risk, actual money recovered, recovery rate, and incremental recovery
> over a naive baseline. Every action is explainable, bounded, and
> auditable — and the recovery loop itself is a real, working integration
> with Razorpay, not a mockup.

## 11. Repository Structure

```
recoverai/
├── app/                       # FastAPI backend
│   ├── main.py                  # API endpoints + Razorpay webhook handler
│   ├── models.py                # SQLAlchemy models
│   ├── recovery_engine.py       # Scoring (ML + rule-based) + policy engine
│   ├── razorpay_adapter.py      # Payment provider adapter + webhook verification
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