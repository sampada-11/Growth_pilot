"""Initial Phase 2 migration with tenant_id, RLS columns, and Razorpay fields

Revision ID: 001_phase2
Revises: 
Create Date: 2026-08-29 19:35:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_phase2'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Customers
    op.create_table(
        'customers',
        sa.Column('customer_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('segment', sa.String(100), nullable=True),
        sa.Column('channel', sa.String(100), nullable=True),
        sa.Column('signup_date', sa.String(50), nullable=True),
    )
    op.create_index('ix_customers_tenant_id', 'customers', ['tenant_id'])

    # 2. Products
    op.create_table(
        'products',
        sa.Column('product_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('base_price', sa.Float(), nullable=False),
        sa.Column('margin_pct', sa.Float(), nullable=False, server_default='40.0'),
        sa.Column('inventory_count', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('inventory_urgency_factor', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('launch_date', sa.String(50), nullable=True),
    )
    op.create_index('ix_products_tenant_id', 'products', ['tenant_id'])

    # 3. Order Items
    op.create_table(
        'order_items',
        sa.Column('order_item_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('customer_id', sa.String(50), sa.ForeignKey('customers.customer_id'), nullable=False),
        sa.Column('product_id', sa.String(50), sa.ForeignKey('products.product_id'), nullable=False),
        sa.Column('purchase_date', sa.String(50), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('discount_pct', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('revenue', sa.Float(), nullable=False),
    )
    op.create_index('ix_order_items_tenant_id', 'order_items', ['tenant_id'])

    # 4. Sessions
    op.create_table(
        'sessions',
        sa.Column('session_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('customer_id', sa.String(50), sa.ForeignKey('customers.customer_id'), nullable=False),
        sa.Column('start_time', sa.String(50), nullable=False),
        sa.Column('channel', sa.String(100), nullable=True),
    )
    op.create_index('ix_sessions_tenant_id', 'sessions', ['tenant_id'])

    # 5. Cart Events
    op.create_table(
        'cart_events',
        sa.Column('cart_event_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('session_id', sa.String(50), sa.ForeignKey('sessions.session_id'), nullable=False),
        sa.Column('customer_id', sa.String(50), nullable=False),
        sa.Column('product_id', sa.String(50), sa.ForeignKey('products.product_id'), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('event_time', sa.String(50), nullable=False),
    )
    op.create_index('ix_cart_events_tenant_id', 'cart_events', ['tenant_id'])

    # 6. Insights
    op.create_table(
        'insights',
        sa.Column('insight_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('type', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=False),
        sa.Column('generated_at', sa.String(50), nullable=False),
    )
    op.create_index('ix_insights_tenant_id', 'insights', ['tenant_id'])

    # 7. Opportunities
    op.create_table(
        'opportunities',
        sa.Column('opportunity_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('insight_id', sa.String(50), sa.ForeignKey('insights.insight_id'), nullable=False),
        sa.Column('problem', sa.Text(), nullable=False),
        sa.Column('expected_impact', sa.Float(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('urgency_factor', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('recommended_action', sa.Text(), nullable=False),
        sa.Column('priority_score', sa.Float(), nullable=False),
        sa.Column('priority_rank', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='open'),
    )
    op.create_index('ix_opportunities_tenant_id', 'opportunities', ['tenant_id'])

    # 8. Campaign Proposals
    op.create_table(
        'campaign_proposals',
        sa.Column('campaign_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('opportunity_id', sa.String(50), sa.ForeignKey('opportunities.opportunity_id'), nullable=False),
        sa.Column('target_segment', sa.String(200), nullable=False),
        sa.Column('product_id', sa.String(50), nullable=False),
        sa.Column('offer_pct', sa.Float(), nullable=False),
        sa.Column('discount_band', sa.Text(), nullable=True),
        sa.Column('channel', sa.String(100), nullable=False),
        sa.Column('generated_copy', sa.Text(), nullable=False),
        sa.Column('expected_roi', sa.Float(), nullable=False),
        sa.Column('risk_tier', sa.String(50), nullable=False),
        sa.Column('risk_reasons', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='drafted'),
        sa.Column('created_at', sa.String(50), nullable=False),
    )
    op.create_index('ix_campaign_proposals_tenant_id', 'campaign_proposals', ['tenant_id'])

    # 9. Campaign Interactions
    op.create_table(
        'campaign_interactions',
        sa.Column('interaction_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('campaign_id', sa.String(50), sa.ForeignKey('campaign_proposals.campaign_id'), nullable=False),
        sa.Column('customer_id', sa.String(50), nullable=False),
        sa.Column('interaction_type', sa.String(50), nullable=False),
        sa.Column('interaction_time', sa.String(50), nullable=False),
    )
    op.create_index('ix_campaign_interactions_tenant_id', 'campaign_interactions', ['tenant_id'])

    # 10. Executions
    op.create_table(
        'executions',
        sa.Column('execution_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('campaign_id', sa.String(50), sa.ForeignKey('campaign_proposals.campaign_id'), nullable=False),
        sa.Column('approved_by', sa.String(100), nullable=False),
        sa.Column('justification', sa.Text(), nullable=True),
        sa.Column('executed_at', sa.String(50), nullable=False),
        sa.Column('mock_api_status', sa.String(50), nullable=False),
        sa.Column('execution_token', sa.String(100), nullable=False),
        sa.Column('razorpay_order_id', sa.String(100), nullable=True),
        sa.Column('razorpay_payment_link_id', sa.String(100), nullable=True),
        sa.Column('razorpay_payment_id', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='executed'),
        sa.Column('error_message', sa.Text(), nullable=True),
    )
    op.create_index('ix_executions_tenant_id', 'executions', ['tenant_id'])

    # 11. Experiment Results
    op.create_table(
        'experiment_results',
        sa.Column('result_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('execution_id', sa.String(50), sa.ForeignKey('executions.execution_id'), nullable=False),
        sa.Column('expected_conversion', sa.Float(), nullable=False),
        sa.Column('actual_conversion', sa.Float(), nullable=False),
        sa.Column('expected_revenue', sa.Float(), nullable=False),
        sa.Column('actual_revenue', sa.Float(), nullable=False),
        sa.Column('verdict', sa.String(100), nullable=False),
        sa.Column('ai_reasoning', sa.Text(), nullable=False),
        sa.Column('evaluated_at', sa.String(50), nullable=False),
    )
    op.create_index('ix_experiment_results_tenant_id', 'experiment_results', ['tenant_id'])

    # 12. Audit Logs
    op.create_table(
        'audit_logs',
        sa.Column('log_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('timestamp', sa.String(50), nullable=False),
        sa.Column('agent_or_user', sa.String(100), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('payload_hash', sa.String(64), nullable=True),
        sa.Column('details', sa.Text(), nullable=False),
    )
    op.create_index('ix_audit_logs_tenant_id', 'audit_logs', ['tenant_id'])


def downgrade() -> None:
    op.drop_table('audit_logs')
    op.drop_table('experiment_results')
    op.drop_table('executions')
    op.drop_table('campaign_interactions')
    op.drop_table('campaign_proposals')
    op.drop_table('opportunities')
    op.drop_table('insights')
    op.drop_table('cart_events')
    op.drop_table('sessions')
    op.drop_table('order_items')
    op.drop_table('products')
    op.drop_table('customers')
