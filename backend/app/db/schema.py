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
    location = Column(String(100), nullable=True)
    segment = Column(String(100), nullable=True)
    channel = Column(String(100), nullable=True)
    signup_date = Column(String(50), nullable=True)
    registration_date = Column(String(50), nullable=True)

    orders = relationship("Order", back_populates="customer")
    order_items = relationship("OrderItem", back_populates="customer")
    sessions = relationship("Session", back_populates="customer")


class Product(Base):
    __tablename__ = "products"

    product_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    name = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    price = Column(Float, nullable=True)
    stock = Column(Integer, nullable=False, default=100)
    base_price = Column(Float, nullable=False)
    margin_pct = Column(Float, nullable=False, default=40.0)
    inventory_count = Column(Integer, nullable=False, default=100)
    inventory_urgency_factor = Column(Float, nullable=False, default=1.0)
    launch_date = Column(String(50), nullable=True)

    order_items = relationship("OrderItem", back_populates="product")
    cart_events = relationship("CartEvent", back_populates="product")


class Order(Base):
    __tablename__ = "orders"

    order_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    order_date = Column(String(50), nullable=False)
    total_amount = Column(Float, nullable=False, default=0.0)
    status = Column(String(50), nullable=False, default="completed") # 'completed', 'cancelled', 'refunded'
    created_at = Column(String(50), nullable=True)

    customer = relationship("Customer", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id = Column(String(50), primary_key=True)
    order_id = Column(String(50), ForeignKey("orders.order_id"), nullable=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    product_id = Column(String(50), ForeignKey("products.product_id"), nullable=False)
    purchase_date = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Float, nullable=True)
    discount_pct = Column(Float, nullable=False, default=0.0)
    revenue = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    customer = relationship("Customer", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")


class Session(Base):
    __tablename__ = "sessions"

    session_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    customer_id = Column(String(50), ForeignKey("customers.customer_id"), nullable=False)
    start_time = Column(String(50), nullable=False)
    channel = Column(String(100), nullable=True)
    session_status = Column(String(50), nullable=True, default="completed")

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
    timestamp = Column(String(50), nullable=True)

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
    insight_id = Column(String(50), ForeignKey("insights.insight_id"), nullable=True)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    problem = Column(Text, nullable=False)
    root_cause = Column(Text, nullable=True) # JSON encoded
    affected_customers = Column(Text, nullable=True) # JSON encoded
    product_id = Column(String(50), nullable=True)
    supporting_analytics = Column(Text, nullable=True) # JSON encoded
    strategy = Column(Text, nullable=True) # JSON encoded
    expected_impact = Column(Float, nullable=False, default=0.0)
    est_revenue_impact = Column(Float, nullable=False, default=0.0)
    est_profit_impact = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=False, default=0.5)
    urgency_factor = Column(Float, nullable=False, default=1.0)
    priority_score = Column(Float, nullable=False, default=0.0)
    priority_rank = Column(Integer, nullable=False, default=1)
    risk_level = Column(String(50), nullable=False, default="medium")
    approval_status = Column(String(50), nullable=False, default="pending")
    execution_status = Column(String(50), nullable=False, default="not_started")
    lifecycle_state = Column(String(50), nullable=False, default="detected")
    recommended_action = Column(Text, nullable=True)
    status = Column(String(50), nullable=False, default="open")
    agent_run_id = Column(String(50), nullable=True)
    guardrail_result = Column(Text, nullable=True) # JSON encoded
    impact_inputs = Column(Text, nullable=True) # JSON encoded
    approved_by = Column(String(100), nullable=True)
    rejected_by = Column(String(100), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=True)
    updated_at = Column(String(50), nullable=True)

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
    event_type = Column(String(100), nullable=True, index=True)
    actor_type = Column(String(50), nullable=False, default="user")
    actor_id = Column(String(100), nullable=True)
    entity_type = Column(String(50), nullable=True)
    entity_id = Column(String(100), nullable=True)
    status = Column(String(50), nullable=False, default="success")


class Payment(Base):
    __tablename__ = "payments"

    payment_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    order_id = Column(String(50), nullable=True)
    provider_event_id = Column(String(100), nullable=True)
    amount = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default="INR")
    status = Column(String(50), nullable=False, default="succeeded")
    is_simulated = Column(Boolean, nullable=False, default=True)
    created_at = Column(String(50), nullable=False)


class Segment(Base):
    __tablename__ = "segments"

    segment_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    name = Column(String(100), nullable=False)
    definition = Column(Text, nullable=True) # JSON encoded
    is_system = Column(Boolean, nullable=False, default=True)
    created_at = Column(String(50), nullable=False)


class AgentRun(Base):
    __tablename__ = "agent_runs"

    run_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    status = Column(String(50), nullable=False, default="pending")
    started_at = Column(String(50), nullable=True)
    completed_at = Column(String(50), nullable=True)
    summary = Column(Text, nullable=True) # JSON encoded
    created_at = Column(String(50), nullable=False)


class AgentStep(Base):
    __tablename__ = "agent_steps"

    step_id = Column(String(50), primary_key=True)
    run_id = Column(String(50), ForeignKey("agent_runs.run_id"), nullable=False)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    agent = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False, default="pending")
    input_hash = Column(String(64), nullable=True)
    input_data = Column(Text, nullable=True) # JSON encoded
    output_data = Column(Text, nullable=True) # JSON encoded
    latency_ms = Column(Integer, nullable=False, default=0)
    tokens_used = Column(Integer, nullable=False, default=0)
    error = Column(Text, nullable=True)
    created_at = Column(String(50), nullable=False)


class Campaign(Base):
    __tablename__ = "campaigns"

    campaign_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    opportunity_id = Column(String(50), nullable=True)
    name = Column(String(200), nullable=True)
    objective = Column(String(100), nullable=False, default="recover_abandoned_carts")
    segment_id = Column(String(50), nullable=True)
    mode = Column(String(20), nullable=False, default="demo")
    status = Column(String(50), nullable=False, default="draft")
    discount = Column(Text, nullable=True) # JSON encoded
    budget_total = Column(Float, nullable=False, default=0.0)
    per_customer_cap = Column(Float, nullable=False, default=0.0)
    audience_size = Column(Integer, nullable=False, default=0)
    guardrail_result = Column(Text, nullable=True) # JSON encoded
    approved_by = Column(String(100), nullable=True)
    scheduled_at = Column(String(50), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    is_simulated = Column(Boolean, nullable=False, default=True)
    created_at = Column(String(50), nullable=False)
    updated_at = Column(String(50), nullable=True)


class CampaignContent(Base):
    __tablename__ = "campaign_content"

    content_id = Column(String(50), primary_key=True)
    campaign_id = Column(String(50), ForeignKey("campaigns.campaign_id"), nullable=False)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    channel = Column(String(50), nullable=False)
    variant = Column(String(50), nullable=False)
    subject = Column(String(200), nullable=True)
    preheader = Column(String(200), nullable=True)
    body = Column(Text, nullable=False)
    cta = Column(String(100), nullable=False)
    source = Column(String(50), nullable=False, default="ai")
    lint_result = Column(Text, nullable=True) # JSON encoded
    created_at = Column(String(50), nullable=False)


class CampaignDelivery(Base):
    __tablename__ = "campaign_deliveries"

    delivery_id = Column(String(50), primary_key=True)
    campaign_id = Column(String(50), ForeignKey("campaigns.campaign_id"), nullable=False)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    customer_id = Column(String(50), nullable=False)
    channel = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="queued")
    provider_message_id = Column(String(100), nullable=True)
    idempotency_key = Column(String(150), unique=True, nullable=False)
    is_simulated = Column(Boolean, nullable=False, default=True)
    status_at = Column(String(50), nullable=True)
    created_at = Column(String(50), nullable=False)


class Experiment(Base):
    __tablename__ = "experiments"

    experiment_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    campaign_id = Column(String(50), nullable=False)
    holdout_pct = Column(Float, nullable=False, default=20.0)
    start_at = Column(String(50), nullable=True)
    end_at = Column(String(50), nullable=True)
    status = Column(String(50), nullable=False, default="running")
    verdict = Column(String(100), nullable=True)
    result = Column(Text, nullable=True) # JSON encoded
    is_simulated = Column(Boolean, nullable=False, default=True)
    created_at = Column(String(50), nullable=False)


class ExperimentAssignment(Base):
    __tablename__ = "experiment_assignments"

    assignment_id = Column(String(50), primary_key=True)
    experiment_id = Column(String(50), ForeignKey("experiments.experiment_id"), nullable=False)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    customer_id = Column(String(50), nullable=False)
    arm = Column(String(50), nullable=False) # 'control' or 'treatment'
    assigned_at = Column(String(50), nullable=False)


class LearningSignal(Base):
    __tablename__ = "learning_signals"

    signal_id = Column(String(50), primary_key=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    opportunity_type = Column(String(100), nullable=False)
    product_id = Column(String(50), nullable=True)
    segment_key = Column(String(100), nullable=True)
    observed_uplift = Column(Float, nullable=True)
    sample_size = Column(Integer, nullable=True)
    source_experiment_id = Column(String(50), nullable=True)
    is_simulated = Column(Boolean, nullable=False, default=True)
    created_at = Column(String(50), nullable=False)


class CopilotMessage(Base):
    __tablename__ = "copilot_messages"

    message_id = Column(String(50), primary_key=True)
    conversation_id = Column(String(50), nullable=False, index=True)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    user_id = Column(String(50), nullable=False)
    role = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    tool_calls = Column(Text, nullable=True) # JSON encoded
    created_at = Column(String(50), nullable=False)


class OpportunityEvent(Base):
    __tablename__ = "opportunity_events"

    event_id = Column(String(50), primary_key=True)
    opportunity_id = Column(String(50), ForeignKey("opportunities.opportunity_id"), nullable=False)
    tenant_id = Column(String(50), nullable=False, default=DEFAULT_TENANT_ID, index=True)
    from_state = Column(String(50), nullable=True)
    to_state = Column(String(50), nullable=False)
    actor_id = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)
    occurred_at = Column(String(50), nullable=False)
