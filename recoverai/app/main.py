import uuid
import json
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from .database import engine, get_db
from . import models, schemas, recovery_engine as re

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="RecoverAI", version="1.0")

# CORS open for hackathon demo — restrict origins in real deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def log_audit(db: Session, case_id: str, event_type: str, payload: dict):
    ev = models.AuditEvent(
        id=str(uuid.uuid4()),
        case_id=case_id,
        event_type=event_type,
        payload=json.dumps(payload),
        policy_version=re.POLICY_VERSION,
    )
    db.add(ev)
    db.commit()


@app.get("/")
def root():
    return {"service": "RecoverAI", "status": "running"}


# ---------------- 1. Event ingestion ----------------
@app.post("/events/payment-failed", response_model=schemas.CaseOut)
def payment_failed(event: schemas.PaymentFailedEvent, db: Session = Depends(get_db)):
    case_id = str(uuid.uuid4())
    case = models.RecoveryCase(
        id=case_id,
        payment_id=event.payment_id,
        customer_id=event.customer_id,
        amount=event.amount,
        failure_code=event.failure_code,
        attempt_number=event.attempt_number,
        previous_success_count=event.previous_success_count,
        previous_failure_count=event.previous_failure_count,
        subscription_age_days=event.subscription_age_days,
        payment_method=event.payment_method,
        is_baseline_cohort=event.is_baseline_cohort,
        status="OPEN",
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    log_audit(db, case_id, "CASE_CREATED", event.model_dump())
    return case


# ---------------- 2. Diagnose + score ----------------
@app.post("/recovery/analyze", response_model=schemas.CaseOut)
def analyze_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")

    case_dict = {
        "amount": case.amount,
        "previous_success_count": case.previous_success_count,
        "previous_failure_count": case.previous_failure_count,
        "subscription_age_days": case.subscription_age_days,
        "failure_code": case.failure_code,
        "attempt_number": case.attempt_number,
        "created_at": case.created_at,
    }

    score = re.calculate_recovery_score(case_dict)
    diagnosis = re.diagnose_failure(case.failure_code)
    action = re.select_next_best_action(case_dict, score)
    expected_value = re.calculate_expected_value(case.amount, score, action)

    case.recovery_score = score
    case.recommended_action = action
    case.expected_value = expected_value
    case.priority = "HIGH" if expected_value > 1000 else ("MEDIUM" if expected_value > 100 else "LOW")
    db.commit()
    db.refresh(case)

    log_audit(db, case_id, "ANALYZED", {
        "diagnosis": diagnosis, "recovery_score": score,
        "recommended_action": action, "expected_value": expected_value,
    })
    return case


# ---------------- 3. Plan (policy gate check without executing) ----------------
@app.post("/recovery/plan")
def plan_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    if case.recommended_action is None:
        raise HTTPException(400, "Case not analyzed yet — call /recovery/analyze first")

    past_interventions = db.query(models.Intervention).filter(
        models.Intervention.case_id == case_id
    ).all()
    last_time = max([i.timestamp for i in past_interventions], default=None)

    case_dict = {"amount": case.amount, "attempt_number": case.attempt_number, "created_at": case.created_at}
    decision = re.policy_gate(case_dict, case.recommended_action, len(past_interventions), last_time)

    log_audit(db, case_id, "POLICY_PLAN", decision)
    return decision


# ---------------- 4. Execute action ----------------
@app.post("/recovery/execute", response_model=schemas.CaseOut)
def execute_action(req: schemas.ExecuteActionRequest, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == req.case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")

    proposed_action = req.force_action or case.recommended_action
    if not proposed_action:
        raise HTTPException(400, "No action to execute — analyze the case first")

    past_interventions = db.query(models.Intervention).filter(
        models.Intervention.case_id == req.case_id
    ).all()
    last_time = max([i.timestamp for i in past_interventions], default=None)

    case_dict = {"amount": case.amount, "attempt_number": case.attempt_number, "created_at": case.created_at}
    decision = re.policy_gate(case_dict, proposed_action, len(past_interventions), last_time)

    final_action = decision["final_action"]

    intervention = models.Intervention(
        id=str(uuid.uuid4()),
        case_id=case.id,
        action=final_action,
        result="PENDING" if decision["approved"] else "REJECTED",
        payment_state_before=case.status,
        policy_version=re.POLICY_VERSION,
    )
    db.add(intervention)

    if not decision["approved"]:
        if final_action == "HUMAN_REVIEW":
            case.status = "ESCALATED"
        else:
            case.status = "STOPPED"
    else:
        if final_action == "STOP":
            case.status = "STOPPED"
        elif final_action == "HUMAN_REVIEW":
            case.status = "ESCALATED"
        else:
            case.status = "ACTION_TAKEN"
            case.attempt_number += 1

    db.commit()
    db.refresh(case)

    log_audit(db, case.id, "ACTION_EXECUTED", {
        "proposed": proposed_action, "final": final_action,
        "approved": decision["approved"], "reason": decision["reason"],
    })
    return case


# ---------------- 5. Verify payment outcome ----------------
@app.post("/recovery/verify", response_model=schemas.CaseOut)
def verify_payment(req: schemas.VerifyPaymentRequest, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == req.case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")

    intervention = db.query(models.Intervention).filter(
        models.Intervention.case_id == case.id
    ).order_by(models.Intervention.timestamp.desc()).first()

    if req.payment_succeeded is None:
        # Verification API unavailable / unknown -> safe fallback (section 19)
        case.status = "VERIFY_PENDING"
        if intervention:
            intervention.result = "VERIFY_PENDING"
        log_audit(db, case.id, "VERIFY_PENDING", {"reason": "verification unavailable"})
    elif req.payment_succeeded:
        case.status = "RECOVERED"
        case.recovered = True
        case.recovered_amount = case.amount
        minutes = (datetime.utcnow() - case.created_at).total_seconds() / 60
        case.recovery_time_minutes = round(minutes, 2)
        if intervention:
            intervention.result = "SUCCESS"
        log_audit(db, case.id, "RECOVERED", {"amount": case.amount, "time_minutes": case.recovery_time_minutes})
    else:
        case.status = "OPEN"  # can loop back for another attempt within policy limits
        if intervention:
            intervention.result = "FAILED"
        log_audit(db, case.id, "VERIFY_FAILED", {})

    db.commit()
    db.refresh(case)
    return case


# ---------------- 6. Human review override ----------------
@app.post("/review/{case_id}", response_model=schemas.CaseOut)
def human_review(case_id: str, req: schemas.ReviewRequest, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")

    if req.approved:
        case.status = "OPEN"
        if req.action_override:
            case.recommended_action = req.action_override
    else:
        case.status = "STOPPED"

    db.commit()
    db.refresh(case)
    log_audit(db, case_id, "HUMAN_REVIEW", req.model_dump())
    return case


# ---------------- 7. Recovery queue ----------------
@app.get("/recovery/cases", response_model=list[schemas.CaseOut])
def list_cases(status: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    q = db.query(models.RecoveryCase)
    if status:
        q = q.filter(models.RecoveryCase.status == status)
    return q.order_by(models.RecoveryCase.created_at.desc()).limit(limit).all()


@app.get("/recovery/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
    case = db.query(models.RecoveryCase).filter(models.RecoveryCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Case not found")
    interventions = db.query(models.Intervention).filter(models.Intervention.case_id == case_id).all()
    audit = db.query(models.AuditEvent).filter(models.AuditEvent.case_id == case_id).order_by(models.AuditEvent.timestamp).all()
    return {
        "case": schemas.CaseOut.model_validate(case),
        "interventions": [{"action": i.action, "result": i.result, "timestamp": i.timestamp} for i in interventions],
        "audit_trail": [{"event_type": a.event_type, "payload": json.loads(a.payload) if a.payload else {}, "timestamp": a.timestamp} for a in audit],
    }


# ---------------- 8. Batch metrics (section 15/17) ----------------
@app.get("/recovery/metrics")
def get_metrics(db: Session = Depends(get_db)):
    all_cases = db.query(models.RecoveryCase).all()
    total = len(all_cases)
    at_risk = sum(c.amount for c in all_cases)

    ai_cohort = [c for c in all_cases if not c.is_baseline_cohort]
    baseline_cohort = [c for c in all_cases if c.is_baseline_cohort]

    ai_recovered = sum(c.recovered_amount for c in ai_cohort if c.recovered)
    baseline_recovered = sum(c.recovered_amount for c in baseline_cohort if c.recovered)

    ai_eligible = len(ai_cohort)
    ai_recovered_count = sum(1 for c in ai_cohort if c.recovered)

    recovery_times = [c.recovery_time_minutes for c in all_cases if c.recovery_time_minutes]
    avg_time = round(sum(recovery_times) / len(recovery_times), 2) if recovery_times else None
    median_time = None
    if recovery_times:
        s = sorted(recovery_times)
        mid = len(s) // 2
        median_time = s[mid] if len(s) % 2 else (s[mid - 1] + s[mid]) / 2

    total_recovered = sum(c.recovered_amount for c in all_cases if c.recovered)
    escalated = sum(1 for c in all_cases if c.status == "ESCALATED")
    stopped = sum(1 for c in all_cases if c.status == "STOPPED")

    return {
        "total_cases": total,
        "revenue_at_risk": round(at_risk, 2),
        "revenue_recovered_total": round(total_recovered, 2),
        "recovery_rate": round(ai_recovered_count / ai_eligible, 4) if ai_eligible else 0,
        "recovery_value_rate": round(total_recovered / at_risk, 4) if at_risk else 0,
        "baseline_recovered": round(baseline_recovered, 2),
        "ai_recovered": round(ai_recovered, 2),
        "incremental_recovery": round(ai_recovered - baseline_recovered, 2),
        "avg_time_to_recovery_minutes": avg_time,
        "median_time_to_recovery_minutes": median_time,
        "escalation_rate": round(escalated / total, 4) if total else 0,
        "stop_rate": round(stopped / total, 4) if total else 0,
        "open_cases": sum(1 for c in all_cases if c.status in ("OPEN", "ACTION_TAKEN", "VERIFY_PENDING")),
    }


# ---------------- 9. Audit log ----------------
@app.get("/audit")
def get_audit(case_id: Optional[str] = None, limit: int = 200, db: Session = Depends(get_db)):
    q = db.query(models.AuditEvent)
    if case_id:
        q = q.filter(models.AuditEvent.case_id == case_id)
    events = q.order_by(models.AuditEvent.timestamp.desc()).limit(limit).all()
    return [{"case_id": e.case_id, "event_type": e.event_type,
             "payload": json.loads(e.payload) if e.payload else {},
             "timestamp": e.timestamp} for e in events]
