from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class RecoveryCase(Base):
    __tablename__ = "recovery_cases"

    id = Column(String, primary_key=True)
    payment_id = Column(String, index=True)
    customer_id = Column(String, index=True)
    amount = Column(Float)
    status = Column(String, default="OPEN")  # OPEN, RECOVERED, STOPPED, ESCALATED, VERIFY_PENDING, CLOSED
    priority = Column(String, default="MEDIUM")
    failure_code = Column(String, nullable=True)
    attempt_number = Column(Integer, default=0)
    previous_success_count = Column(Integer, default=0)
    previous_failure_count = Column(Integer, default=0)
    subscription_age_days = Column(Integer, default=0)
    payment_method = Column(String, nullable=True)
    recovery_score = Column(Float, nullable=True)
    expected_value = Column(Float, nullable=True)
    recommended_action = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    recovered = Column(Boolean, default=False)
    recovered_amount = Column(Float, default=0)
    recovery_time_minutes = Column(Float, nullable=True)
    is_baseline_cohort = Column(Boolean, default=False)  # for baseline vs AI comparison


class Intervention(Base):
    __tablename__ = "interventions"

    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("recovery_cases.id"), index=True)
    action = Column(String)
    template_id = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    result = Column(String, default="PENDING")  # PENDING, SUCCESS, FAILED, VERIFY_PENDING
    payment_state_before = Column(String, nullable=True)
    policy_version = Column(String, default="v1")


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String, primary_key=True)
    case_id = Column(String, ForeignKey("recovery_cases.id"), index=True)
    event_type = Column(String)
    payload = Column(Text, nullable=True)
    policy_version = Column(String, default="v1")
    timestamp = Column(DateTime, default=datetime.utcnow)
