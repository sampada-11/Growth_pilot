"""
SQLAlchemy ORM Models for GrowthPilot (Supabase Postgres + Multi-Tenant Schema)
Includes tenant_id on all tables and Phase 1 Razorpay fields.
"""
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, ForeignKey, Text, Boolean, Index
)
from sqlalchemy.orm import relationship
from backend.app.db.database import Base, DEFAULT_TENANT_ID


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    age = Column(Integer, nullable=True)
    segment = Column(String(100), nullable=True)
    channel = Column(String(100), nullable=True)
    signup_date = Column(String(50), nullable=True)

    order_items = relationship("OrderItem", back_populates="customer")
    sessions = relationship("Session", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    base_price = Column(Float, nullable=False)
    margin_pct = Column(Float, nullable=False, default=40.0)
    inventory_count = Column(Integer, nullable=False, default=100)
    inventory_urgency_factor = Column(Float, nullable=False, default=1.0)
    launch_date = Column(String(50), nullable=True)

    order_items = relationship("OrderItem", back_populates="product")
    cart_events = relationship("CartEvent", back_populates="product")


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)
    purchase_date = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    discount_pct = Column(Float, nullable=False, default=0.0)
    revenue = Column(Float, nullable=False)

    customer = relationship("Customer", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")


class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    start_time = Column(String(50), nullable=False)
    channel = Column(String(100), nullable=True)

    customer = relationship("Customer", back_populates="sessions")
    cart_events = relationship("CartEvent", back_populates="session")


class CartEvent(Base):
    __tablename__ = "cart_events"

    cart_event_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    session_id = Column(String(50), ForeignKey("sessions.session_id"), nullable=False)
    customer_id = Column(String(50), nullable=False)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)
    event_type = Column(String(50), nullable=False) # 'add_to_cart', 'checkout', 'abandon'
    event_time = Column(String(50), nullable=False)

    session = relationship("Session", back_populates="cart_events")
    product = relationship("Product", back_populates="cart_events")


class Insight(Base):
    __tablename__ = "insights"

    insight_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    type = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    evidence = Column(Text, nullable=False) # JSON encoded
    generated_at = Column(String(50), nullable=False)

    opportunities = relationship("Opportunity", back_populates="insight")


class Opportunity(Base):
    __tablename__ = "opportunities"

    opportunity_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    insight_id = Column(String(50), ForeignKey("insights.insight_id"), nullable=False)
    problem = Column(Text, nullable=False)
    expected_impact = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    urgency_factor = Column(Float, nullable=False, default=1.0)
    recommended_action = Column(Text, nullable=False)
    priority_score = Column(Float, nullable=False)
    priority_rank = Column(Integer, nullable=False)
    status = Column(String(50), nullable=False, default="open")

    insight = relationship("Insight", back_populates="opportunities")
    campaign_proposals = relationship("CampaignProposal", back_populates="opportunity")


class CampaignProposal(Base):
    __tablename__ = "campaign_proposals"

    campaign_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    opportunity_id = Column(String(50), ForeignKey("opportunities.opportunity_id"), nullable=False)
    target_segment = Column(String(200), nullable=False)
    product_id = Column(String(50), nullable=False)
    offer_pct = Column(Float, nullable=False)
    discount_band = Column(Text, nullable=True) # JSON encoded
    channel = Column(String(100), nullable=False)
    generated_copy = Column(Text, nullable=False)
    expected_roi = Column(Float, nullable=False)
    risk_tier = Column(String(50), nullable=False)
    risk_reasons = Column(Text, nullable=False) # JSON encoded
    status = Column(String(50), nullable=False, default="drafted")
    created_at = Column(String(50), nullable=False)

    opportunity = relationship("Opportunity", back_populates="campaign_proposals")
    executions = relationship("Execution", back_populates="campaign")


class CampaignInteraction(Base):
    __tablename__ = "campaign_interactions"

    interaction_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    campaign_id = Column(String(50), ForeignKey("campaign_proposals.campaign_id"), nullable=False)
    customer_id = Column(String(50), nullable=False)
    interaction_type = Column(String(50), nullable=False) # 'payment_success', 'email_opened', etc.
    interaction_time = Column(String(50), nullable=False)


class Execution(Base):
    __tablename__ = "executions"

    execution_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    campaign_id = Column(String(50), ForeignKey("campaign_proposals.campaign_id"), nullable=False)
    approved_by = Column(String(100), nullable=False)
    justification = Column(Text, nullable=True)
    executed_at = Column(String(50), nullable=False)
    mock_api_status = Column(String(50), nullable=False)
    execution_token = Column(String(100), nullable=False)
    razorpay_order_id = Column(String(100), nullable=True)
    razorpay_payment_link_id = Column(String(100), nullable=True)
    razorpay_payment_id = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="executed") # 'executed' or 'failed'
    error_message = Column(Text, nullable=True)

    campaign = relationship("CampaignProposal", back_populates="executions")
    experiment_results = relationship("ExperimentResult", back_populates="execution")


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    result_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    execution_id = Column(String(50), ForeignKey("executions.execution_id"), nullable=False)
    expected_conversion = Column(Float, nullable=False)
    actual_conversion = Column(Float, nullable=False)
    expected_revenue = Column(Float, nullable=False)
    actual_revenue = Column(Float, nullable=False)
    verdict = Column(String(100), nullable=False)
    ai_reasoning = Column(Text, nullable=False)
    evaluated_at = Column(String(50), nullable=False)

    execution = relationship("Execution", back_populates="experiment_results")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    timestamp = Column(String(50), nullable=False)
    agent_or_user = Column(String(100), nullable=False)
    action_type = Column(String(100), nullable=False)
    payload_hash = Column(String(64), nullable=True) # SHA-256 hash of raw webhook or payload
    details = Column(Text, nullable=False) # JSON encoded, sanitized
