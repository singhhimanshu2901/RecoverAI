"""
Core recovery decision logic.
Rule-based scoring for MVP speed (swap with XGBoost model later via score_with_model()).
Deterministic policy engine — AI/scoring only RECOMMENDS, this layer AUTHORIZES.
"""
from datetime import datetime, timedelta

# ---- Hard policy limits (from project blueprint, section 18) ----
MAX_RETRIES = 2
MAX_MESSAGES = 2
COOLDOWN_HOURS = 6
MAX_RECOVERY_WINDOW_HOURS = 72
POLICY_VERSION = "v1"


def calculate_recovery_score(case: dict) -> float:
    """
    Rule-based recovery probability (0-1). Inputs come from the case dict.
    Swap this function for an XGBoost model call later without changing callers.
    """
    score = 0.5  # base

    success = case.get("previous_success_count", 0)
    failure = case.get("previous_failure_count", 0)
    total = success + failure
    if total > 0:
        history_ratio = success / total
        score += (history_ratio - 0.5) * 0.4  # +/- up to 0.2

    # subscription age -> loyalty signal
    age_days = case.get("subscription_age_days", 0)
    if age_days > 180:
        score += 0.1
    elif age_days < 14:
        score -= 0.1

    # failure code signal
    failure_code = case.get("failure_code", "")
    if failure_code == "RETRYABLE":
        score += 0.15
    elif failure_code == "INSUFFICIENT_FUNDS":
        score -= 0.05
    elif failure_code == "CUSTOMER_ACTION_REQUIRED":
        score += 0.05
    elif failure_code == "CARD_EXPIRED":
        score -= 0.1

    # attempt number -> diminishing returns
    attempt = case.get("attempt_number", 0)
    score -= attempt * 0.1

    return max(0.0, min(1.0, round(score, 3)))


INTERVENTION_COST = {
    "RETRY": 2,
    "PAYMENT_LINK": 5,
    "REMINDER": 3,
    "HUMAN_REVIEW": 50,
    "STOP": 0,
}


def calculate_expected_value(amount: float, recovery_score: float, action: str) -> float:
    cost = INTERVENTION_COST.get(action, 0)
    return round(amount * recovery_score - cost, 2)


def select_next_best_action(case: dict, recovery_score: float) -> str:
    """Deterministic next-best-action selection (section 12)."""
    failure_code = case.get("failure_code", "")
    attempt = case.get("attempt_number", 0)
    amount = case.get("amount", 0)

    if recovery_score <= 0.20:
        return "STOP"

    if amount > 5000 and (0.21 <= recovery_score <= 0.65):
        return "HUMAN_REVIEW"

    if failure_code == "RETRYABLE" and attempt < MAX_RETRIES:
        return "RETRY"

    if failure_code in ("CUSTOMER_ACTION_REQUIRED", "CARD_EXPIRED", "INSUFFICIENT_FUNDS"):
        return "PAYMENT_LINK"

    if recovery_score <= 0.50:
        return "REMINDER"

    return "PAYMENT_LINK"


def policy_gate(case: dict, proposed_action: str, past_intervention_count: int,
                 last_intervention_time: datetime | None) -> dict:
    """
    Deterministic authorization layer. The AI/scoring layer proposes; this
    function is the only thing allowed to authorize execution.
    Returns {"approved": bool, "final_action": str, "reason": str}
    """
    now = datetime.utcnow()

    # Recovery window check
    created_at = case.get("created_at")
    if created_at and (now - created_at) > timedelta(hours=MAX_RECOVERY_WINDOW_HOURS):
        return {"approved": False, "final_action": "STOP",
                "reason": "Max recovery window (72h) exceeded"}

    # Cooldown check
    if last_intervention_time and (now - last_intervention_time) < timedelta(hours=COOLDOWN_HOURS):
        return {"approved": False, "final_action": "STOP",
                "reason": f"Cooldown active ({COOLDOWN_HOURS}h between interventions)"}

    # Retry cap
    if proposed_action == "RETRY" and case.get("attempt_number", 0) >= MAX_RETRIES:
        return {"approved": False, "final_action": "STOP",
                "reason": "Max retries exceeded"}

    # Message cap (payment link / reminder count as outreach)
    if proposed_action in ("PAYMENT_LINK", "REMINDER") and past_intervention_count >= MAX_MESSAGES:
        return {"approved": False, "final_action": "STOP",
                "reason": "Max messages exceeded"}

    # No arbitrary action types allowed
    allowed_actions = set(INTERVENTION_COST.keys())
    if proposed_action not in allowed_actions:
        return {"approved": False, "final_action": "HUMAN_REVIEW",
                "reason": "Unrecognized action proposed — routed to human review"}

    return {"approved": True, "final_action": proposed_action, "reason": "Policy checks passed"}


def diagnose_failure(failure_code: str) -> str:
    mapping = {
        "RETRYABLE": "temporary_processing_issue",
        "INSUFFICIENT_FUNDS": "customer_action_required",
        "CARD_EXPIRED": "customer_action_required",
        "CUSTOMER_ACTION_REQUIRED": "customer_action_required",
        "BANK_DECLINE": "temporary_processing_issue",
    }
    return mapping.get(failure_code, "unknown")
