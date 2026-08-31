"""
Train an XGBoost recovery-probability model on historical case outcomes
pulled from the live API. Falls back gracefully if xgboost/sklearn aren't
available in the runtime -- the rule-based scorer in recovery_engine.py
keeps working either way.

Usage:
    python train_model.py --api https://recoverai-soqt.onrender.com
    python train_model.py --api http://localhost:8000 --out app/model.pkl
"""
import argparse
import pickle
import requests
import numpy as np

FAILURE_CODE_MAP = {
    "RETRYABLE": 0, "INSUFFICIENT_FUNDS": 1, "CARD_EXPIRED": 2,
    "CUSTOMER_ACTION_REQUIRED": 3, "BANK_DECLINE": 4,
}


def featurize(case: dict) -> list:
    total = case["previous_success_count"] + case["previous_failure_count"]
    history_ratio = case["previous_success_count"] / total if total else 0.5
    return [
        case["amount"],
        case["previous_success_count"],
        case["previous_failure_count"],
        history_ratio,
        case["subscription_age_days"],
        case["attempt_number"],
        FAILURE_CODE_MAP.get(case["failure_code"], 5),
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--out", default="app/model.pkl")
    args = ap.parse_args()

    print("Fetching closed cases (RECOVERED or STOPPED/verified) from API...")
    cases = requests.get(f"{args.api}/recovery/cases?limit=1000").json()

    labeled = [c for c in cases if c["recovery_score"] is not None and c["attempt_number"] >= 1]
    if len(labeled) < 30:
        print(f"Only {len(labeled)} labeled cases found -- need at least 30 to train. "
              f"Run generate_dataset.py first. Skipping training; rule-based scorer remains active.")
        return

    X, y = [], []
    for c in labeled:
        try:
            X.append(featurize(c))
            y.append(1 if c["recovered"] else 0)
        except KeyError:
            continue

    X = np.array(X)
    y = np.array(y)
    print(f"Training on {len(X)} cases, {y.sum()} positive (recovered).")

    try:
        from xgboost import XGBClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import roc_auc_score, accuracy_score

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

        model = XGBClassifier(
            n_estimators=100, max_depth=4, learning_rate=0.1,
            eval_metric="logloss",
        )
        model.fit(X_train, y_train)

        preds = model.predict_proba(X_test)[:, 1]
        acc = accuracy_score(y_test, preds > 0.5)
        try:
            auc = roc_auc_score(y_test, preds)
        except ValueError:
            auc = None

        print(f"Held-out accuracy: {acc:.3f}" + (f" | AUC: {auc:.3f}" if auc else ""))

        with open(args.out, "wb") as f:
            pickle.dump(model, f)
        print(f"Model saved to {args.out}")

    except ImportError:
        print("xgboost/sklearn not installed -- run: pip install xgboost scikit-learn --break-system-packages")


if __name__ == "__main__":
    main()