"""
RecoverAI synthetic dataset generator.

Generates realistic failed-payment recovery cases and runs them through the
full API pipeline (create -> analyze -> plan -> execute -> verify), so the
dashboard has real batch data to show.

Includes a baseline cohort (no AI action, low fixed recovery rate) and an
AI cohort (full RecoverAI pipeline) so incremental recovery can be measured.

Usage:
    python generate_dataset.py --api https://recoverai-soqt.onrender.com --n 200
    python generate_dataset.py --api http://localhost:8000 --n 100 --baseline-ratio 0.3
"""
import argparse
import random
import time
import requests

FAILURE_CODES = ["RETRYABLE", "INSUFFICIENT_FUNDS", "CARD_EXPIRED",
                  "CUSTOMER_ACTION_REQUIRED", "BANK_DECLINE"]
PAYMENT_METHODS = ["UPI", "CARD", "NETBANKING", "WALLET"]

AMOUNT_BUCKETS = [
    (99, 999, 0.45),
    (1000, 4999, 0.35),
    (5000, 19999, 0.15),
    (20000, 75000, 0.05),
]


def random_amount():
    r = random.random()
    cum = 0
    for lo, hi, weight in AMOUNT_BUCKETS:
        cum += weight
        if r <= cum:
            return round(random.uniform(lo, hi), 2)
    return round(random.uniform(99, 999), 2)


def random_customer_history():
    """Skew toward loyal customers with a long tail of new/troubled ones."""
    profile = random.random()
    if profile < 0.55:  # loyal customer
        success = random.randint(5, 40)
        failure = random.randint(0, 2)
    elif profile < 0.85:  # mid history
        success = random.randint(1, 8)
        failure = random.randint(0, 4)
    else:  # new / risky customer
        success = random.randint(0, 2)
        failure = random.randint(1, 6)
    return success, failure


def true_recovery_probability(amount, success, failure, failure_code, sub_age_days):
    """
    'Ground truth' probability used only by the generator to decide the
    ACTUAL outcome (simulating real-world payment behavior). The AI/rule
    engine does NOT see this value -- it only sees the case fields, same
    as it would with real merchant data.
    """
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
    elif failure_code == "CUSTOMER_ACTION_REQUIRED":
        p += 0.0

    if sub_age_days > 180:
        p += 0.08
    if amount > 20000:
        p -= 0.1

    p += random.uniform(-0.1, 0.1)  # noise
    return max(0.02, min(0.97, p))


def generate_case(is_baseline: bool):
    amount = random_amount()
    success, failure = random_customer_history()
    failure_code = random.choices(
        FAILURE_CODES, weights=[0.30, 0.20, 0.15, 0.25, 0.10]
    )[0]
    sub_age = random.choice([random.randint(0, 13), random.randint(14, 179), random.randint(180, 900)])
    method = random.choice(PAYMENT_METHODS)

    true_prob = true_recovery_probability(amount, success, failure, failure_code, sub_age)

    return {
        "payment_id": f"pay_test_{random.randint(100000, 999999)}",
        "customer_id": f"C{random.randint(100, 999)}",
        "amount": amount,
        "failure_code": failure_code,
        "attempt_number": 0,
        "previous_success_count": success,
        "previous_failure_count": failure,
        "subscription_age_days": sub_age,
        "payment_method": method,
        "is_baseline_cohort": is_baseline,
    }, true_prob


def run_baseline_case(session, api, case_payload, true_prob):
    """Baseline cohort: no diagnosis/policy engine, simple fixed-strategy
    'send one generic reminder' behavior with a flat lower success rate,
    representing how merchants recover today without AI."""
    r = session.post(f"{api}/events/payment-failed", json=case_payload, timeout=30)
    r.raise_for_status()
    case = r.json()
    case_id = case["id"]

    # Baseline strategy recovers roughly the true probability minus a
    # penalty (no smart targeting/timing) -- represents a naive reminder,
    # and takes noticeably longer (no smart timing/prioritization).
    baseline_success_chance = max(0.0, true_prob - 0.25)
    succeeded = random.random() < baseline_success_chance
    minutes = random.uniform(180, 2400) if succeeded else None  # 3h to 40h

    session.post(f"{api}/recovery/verify", json={
        "case_id": case_id,
        "payment_succeeded": succeeded if succeeded else False,
        "simulated_minutes": minutes,
    }, timeout=30)
    return case_id, succeeded


def run_ai_case(session, api, case_payload, true_prob):
    r = session.post(f"{api}/events/payment-failed", json=case_payload, timeout=30)
    r.raise_for_status()
    case = r.json()
    case_id = case["id"]

    r = session.post(f"{api}/recovery/analyze", params={"case_id": case_id}, timeout=30)
    r.raise_for_status()
    analyzed = r.json()
    action = analyzed["recommended_action"]

    if action == "STOP":
        return case_id, False

    r = session.post(f"{api}/recovery/execute", json={"case_id": case_id}, timeout=30)
    r.raise_for_status()
    executed = r.json()

    if executed["status"] in ("STOPPED", "ESCALATED"):
        # ~40% of escalated/high-value cases still recover via human review
        succeeded = random.random() < (true_prob * 0.6) if executed["status"] == "ESCALATED" else False
        session.post(f"{api}/recovery/verify", json={
            "case_id": case_id, "payment_succeeded": succeeded
        }, timeout=30)
        return case_id, succeeded

    # AI-driven action recovers close to the true probability, with a
    # small boost from better targeting/timing vs baseline, and recovers
    # much faster (minutes to a few hours) due to immediate action.
    ai_success_chance = min(0.97, true_prob + 0.05)
    succeeded = random.random() < ai_success_chance
    minutes = random.uniform(5, 300) if succeeded else None  # 5 min to 5h

    # simulate an occasional unverifiable outcome (VERIFY_PENDING path)
    if random.random() < 0.03:
        session.post(f"{api}/recovery/verify", json={"case_id": case_id}, timeout=30)
        return case_id, None

    session.post(f"{api}/recovery/verify", json={
        "case_id": case_id,
        "payment_succeeded": succeeded,
        "simulated_minutes": minutes,
    }, timeout=30)
    return case_id, succeeded


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True, help="Base URL of the RecoverAI backend")
    ap.add_argument("--n", type=int, default=200, help="Number of cases to generate")
    ap.add_argument("--baseline-ratio", type=float, default=0.3,
                     help="Fraction of cases in the baseline (no-AI) cohort")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    random.seed(args.seed)
    session = requests.Session()

    n_baseline = int(args.n * args.baseline_ratio)
    n_ai = args.n - n_baseline

    print(f"Generating {args.n} cases -> {n_ai} AI cohort, {n_baseline} baseline cohort")
    print(f"Target API: {args.api}")

    recovered_count = 0
    for i in range(n_ai):
        payload, prob = generate_case(is_baseline=False)
        try:
            _, ok = run_ai_case(session, args.api, payload, prob)
            recovered_count += 1 if ok else 0
        except requests.RequestException as e:
            print(f"  [AI case {i}] request failed: {e}")
        if (i + 1) % 25 == 0:
            print(f"  AI cohort: {i + 1}/{n_ai} done")

    for i in range(n_baseline):
        payload, prob = generate_case(is_baseline=True)
        try:
            _, ok = run_baseline_case(session, args.api, payload, prob)
            recovered_count += 1 if ok else 0
        except requests.RequestException as e:
            print(f"  [baseline case {i}] request failed: {e}")
        if (i + 1) % 25 == 0:
            print(f"  Baseline cohort: {i + 1}/{n_baseline} done")

    print(f"\nDone. {recovered_count} cases recovered out of {args.n} total.")

    try:
        r = session.get(f"{args.api}/recovery/metrics", timeout=30)
        print("\nBatch metrics:")
        for k, v in r.json().items():
            print(f"  {k}: {v}")
    except requests.RequestException as e:
        print(f"Could not fetch metrics: {e}")


if __name__ == "__main__":
    main()
