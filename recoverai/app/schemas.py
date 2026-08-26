from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class PaymentFailedEvent(BaseModel):
    payment_id: str
    customer_id: str
    amount: float
    failure_code: str = "RETRYABLE"
    attempt_number: int = 0
    previous_success_count: int = 0
    previous_failure_count: int = 0
    subscription_age_days: int = 0
    payment_method: Optional[str] = None
    is_baseline_cohort: bool = False


class CaseOut(BaseModel):
    id: str
    payment_id: str
    customer_id: str
    amount: float
    status: str
    priority: str
    failure_code: Optional[str]
    attempt_number: int
    recovery_score: Optional[float]
    expected_value: Optional[float]
    recommended_action: Optional[str]
    created_at: datetime
    recovered: bool
    recovered_amount: float

    class Config:
        from_attributes = True


class ExecuteActionRequest(BaseModel):
    case_id: str
    force_action: Optional[str] = None  # allows human override


class VerifyPaymentRequest(BaseModel):
    case_id: str
    payment_succeeded: Optional[bool] = None  # None = simulate/unknown -> VERIFY_PENDING
    simulated_minutes: Optional[float] = None  # for seeding realistic time-to-recovery in demos


class ReviewRequest(BaseModel):
    approved: bool
    action_override: Optional[str] = None
    reviewer_note: Optional[str] = None
