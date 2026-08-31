"""
Train an XGBoost recovery-probability model on historical case outcomes
pulled from the live API. Falls back gracefully if xgboost/sklearn aren't
available in the runtime -- the rule-based scorer in recovery_engine.py
keeps working either way.

Feature encoding here MUST match app/recovery_engine.py::_score_with_model
exactly, or predictions will be silently wrong.

Usage:
    python train_model.py --api https://recoverai-soqt.onrender.com
    python train_model.py --api http://localhost:8000 --out app/model.pkl
"""
import argparse
import pickle
import requests
import numpy as np

FAILURE_CODES = ["RETRYABLE", "INSUFFICIENT_FUNDS", "CARD_EXPIRED",
                  "CUSTOMER_ACTION_REQUIRED", "BANK_DECLINE"]


def featurize(case: dict) -> list:
    """Shared feature encoding -- mirrored exactly in recovery_engine.py."""
    total = case["previous_success_count"] + case["previous_failure_count"]
    history_ratio = case["previous_success_count"] / total if total else 0.5

    one_hot = [1.0 if case["failure_code"] == code else 0.0 for code in FAILURE_CODES]

    return [
        case["amount"],
        case["previous_success_count"],
        case["previous_failure_count"],
        history_ratio,
        case["subscription_age_days"],
        case["attempt_number"],
        1.0 if case["subscription_age_days"] > 180 else 0.0,
        *one_hot,
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--out", default="app/model.pkl")
    args = ap.parse_args()

    print("Fetching cases from API...")
    cases = requests.get(f"{args.api}/recovery/cases?limit=2000").json()

    labeled = [c for c in cases if c["recovery_score"] is not None and c["attempt_number"] >= 1]
    if len(labeled) < 30:
        print(f"Only {len(labeled)} labeled cases found -- need at least 30. "
              f"Run generate_dataset.py first. Rule-based scorer remains active.")
        return

    X = np.array([featurize(c) for c in labeled])
    y = np.array([1 if c["recovered"] else 0 for c in labeled])
    print(f"Training on {len(X)} cases, {int(y.sum())} positive ({y.mean()*100:.1f}% recovered).")

    try:
        from xgboost import XGBClassifier
        from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
        from sklearn.metrics import roc_auc_score, accuracy_score

        pos_weight = (len(y) - y.sum()) / max(y.sum(), 1)

        model_params = dict(
            n_estimators=200, max_depth=3, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, min_child_weight=3,
            reg_lambda=1.5, eval_metric="logloss", scale_pos_weight=pos_weight,
        )

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        cv_scores = cross_val_score(XGBClassifier(**model_params), X, y, cv=cv, scoring="roc_auc")
        print(f"5-fold cross-validated AUC: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
        eval_model = XGBClassifier(**model_params)
        eval_model.fit(X_train, y_train)
        preds = eval_model.predict_proba(X_test)[:, 1]
        acc = accuracy_score(y_test, preds > 0.5)
        try:
            auc = roc_auc_score(y_test, preds)
        except ValueError:
            auc = None
        print(f"Held-out accuracy: {acc:.3f}" + (f" | AUC: {auc:.3f}" if auc else ""))

        final_model = XGBClassifier(**model_params)
        final_model.fit(X, y)

        with open(args.out, "wb") as f:
            pickle.dump(final_model, f)
        print(f"Model saved to {args.out} (trained on all {len(X)} labeled cases)")

    except ImportError:
        print("xgboost/sklearn not installed -- run: pip install xgboost scikit-learn")


if __name__ == "__main__":
    main()