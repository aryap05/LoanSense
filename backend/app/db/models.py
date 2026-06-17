import uuid
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

class Applicant(Base):
    __tablename__ = "applicants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hashed_pan = Column(String, nullable=False, index=True)
    raw_features = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    model_outputs = relationship("ModelOutput", back_populates="applicant", cascade="all, delete-orphan")
    agent_verdicts = relationship("AgentVerdict", back_populates="applicant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="applicant", cascade="all, delete-orphan")

class ModelOutput(Base):
    __tablename__ = "model_outputs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    applicant_id = Column(UUID(as_uuid=True), ForeignKey("applicants.id"), nullable=False)
    model_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    score = Column(Float, nullable=True)
    signals = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    applicant = relationship("Applicant", back_populates="model_outputs")

class AgentVerdict(Base):
    __tablename__ = "agent_verdicts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    applicant_id = Column(UUID(as_uuid=True), ForeignKey("applicants.id"), nullable=False)
    decision = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    reason = Column(String, nullable=False)
    risk_signals = Column(JSONB, nullable=True)
    rbi_compliance = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    applicant = relationship("Applicant", back_populates="agent_verdicts")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    applicant_id = Column(UUID(as_uuid=True), ForeignKey("applicants.id"), nullable=False)
    event_type = Column(String, nullable=False)
    event_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    applicant = relationship("Applicant", back_populates="audit_logs")
