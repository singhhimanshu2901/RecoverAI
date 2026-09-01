"""
In-process synthetic batch generator. Same modeling logic as
generate_dataset.py, but runs directly against the DB session instead of
making HTTP calls per case -- this lets the dashboard trigger a fresh batch
in a few seconds instead of several minutes.
"""
import random
import uuid
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from . import models, recovery_engine as re

FAILURE_CODES = ["RETRYABLE", "INSUFFICIENT_FUNDS", "CARD_EXPIRED",
                  "CUSTOMER_ACTION_REQUIRED", "BANK_DECLINE"]
PAYMENT_METHODS = ["UPI", "CARD", "NETBANKING", "WALLET"]
AMOUNT_BUCKETS = [(99, 999, 0.45), (1000, 4999, 0.35), (5000, 19999, 0.15), (20000, 75000, 0.05)]


def _random_amount():
    r = random.random()
    cum = 0
    for lo, hi, weight in AMOUNT_BUCKETS:
        cum += weight
        if r <= cum:
            return round(random.uniform(lo, hi), 2)
    return round(random.uniform(99, 999), 2)


def _random_history():
    profile = random.random()
    if profile < 0.55:
        return random.randint(5, 40), random.randint(0, 2)
    elif profile < 0.85:
        return random.randint(1, 8), random.randint(0, 4)
    return random.randint(0, 2), random.randint(1, 6)


def _true_prob(amount, success, failure, failure_code, sub_age_days):
    total = success + failure
    ratio = success / total if total else 0.5
    p = 0.35 + ratio * 0.35
    if failure_code == "RETRYABLE":
        p += 0.15
    elif failure_code == "BANK_DECLINE":
        p += 0.05
    elif failure_code == "INSUFFICIENT_FUNDS":
        p -= 0.05
    elif failure_code == "CARD_EXPIRED":
        p -= 0.15
    if sub_age_days > 180:
        p += 0.08
    if amount > 20000:
        p -= 0.1
    p += random.uniform(-0.04, 0.04)
    return max(0.02, min(0.97, p))


def generate_batch(db: Session, n: int, baseline_ratio: float = 0.3) -> dict:
    n = max(1, min(n, 1000))  # hard cap to protect the request
    n_baseline = int(n * baseline_ratio)
    n_ai = n - n_baseline
    recovered_count = 0

    for is_baseline, count in [(False, n_ai), (True, n_baseline)]:
        for _ in range(count):
            amount = _random_amount()
            success, failure = _random_history()
            failure_code = random.choices(FAILURE_CODES, weights=[0.30, 0.20, 0.15, 0.25, 0.10])[0]
            sub_age = random.choice([random.randint(0, 13), random.randint(14, 179), random.randint(180, 900)])
            true_prob = _true_prob(amount, success, failure, failure_code, sub_age)

            case = models.RecoveryCase(
                id=str(uuid.uuid4()),
                payment_id=f"pay_sim_{uuid.uuid4().hex[:8]}",
                customer_id=f"C{random.randint(100, 999)}",
                amount=amount,
                failure_code=failure_code,
                previous_success_count=success,
                previous_failure_count=failure,
                subscription_age_days=sub_age,
                payment_method=random.choice(PAYMENT_METHODS),
                is_baseline_cohort=is_baseline,
                status="OPEN",
            )
            db.add(case)

            if is_baseline:
                baseline_chance = max(0.0, true_prob - 0.25)
                succeeded = random.random() < baseline_chance
                if succeeded:
                    case.status = "RECOVERED"
                    case.recovered = True
                    case.recovered_amount = amount
                    case.recovery_time_minutes = round(random.uniform(180, 2400), 2)
                    recovered_count += 1
                else:
                    case.status = "STOPPED"
                continue

            # AI cohort: run through the real scoring + policy engine
            case_dict = {
                "amount": amount, "previous_success_count": success, "previous_failure_count": failure,
                "subscription_age_days": sub_age, "failure_code": failure_code,
                "attempt_number": 0, "created_at": datetime.utcnow(),
            }
            score = re.calculate_recovery_score(case_dict)
            action = re.select_next_best_action(case_dict, score)
            expected_value = re.calculate_expected_value(amount, score, action)
            case.recovery_score = score
            case.recommended_action = action
            case.expected_value = expected_value
            case.priority = "HIGH" if expected_value > 1000 else ("MEDIUM" if expected_value > 100 else "LOW")

            if action == "STOP":
                case.status = "STOPPED"
                continue

            decision = re.policy_gate(case_dict, action, 0, None)
            final_action = decision["final_action"]
            case.attempt_number = 1

            if not decision["approved"] or final_action in ("STOP", "HUMAN_REVIEW"):
                if final_action == "HUMAN_REVIEW":
                    case.status = "ESCALATED"
                    succeeded = random.random() < (true_prob * 0.6)
                else:
                    case.status = "STOPPED"
                    succeeded = False
            else:
                ai_chance = min(0.97, true_prob + 0.05)
                succeeded = random.random() < ai_chance

            if succeeded:
                case.status = "RECOVERED"
                case.recovered = True
                case.recovered_amount = amount
                case.recovery_time_minutes = round(random.uniform(5, 300), 2)
                recovered_count += 1
            elif case.status not in ("ESCALATED", "STOPPED"):
                case.status = "STOPPED"

    db.commit()
    return {"generated": n, "ai_cohort": n_ai, "baseline_cohort": n_baseline, "recovered": recovered_count}