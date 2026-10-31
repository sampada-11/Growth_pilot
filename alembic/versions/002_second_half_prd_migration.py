"""Second Half PRD migration: payments, segments, agent runs, campaigns, experiments, copilot, opportunity extensions

Revision ID: 002_second_half_prd
Revises: 001_phase2
Create Date: 2026-10-30 18:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_second_half_prd'
down_revision: Union[str, None] = '001_phase2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Payments table
    op.create_table(
        'payments',
        sa.Column('payment_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('order_id', sa.String(50), nullable=True),
        sa.Column('provider_event_id', sa.String(100), nullable=True),
        sa.Column('amount', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('currency', sa.String(10), nullable=False, server_default='INR'),
        sa.Column('status', sa.String(50), nullable=False, server_default='succeeded'),
        sa.Column('is_simulated', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.UniqueConstraint('tenant_id', 'provider_event_id', name='uq_payments_tenant_provider_event')
    )
    op.create_index('ix_payments_tenant_id', 'payments', ['tenant_id'])

    # 2. Segments table
    op.create_table(
        'segments',
        sa.Column('segment_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('definition', sa.Text(), nullable=True),
        sa.Column('is_system', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_segments_tenant_name')
    )
    op.create_index('ix_segments_tenant_id', 'segments', ['tenant_id'])

    # 3. Agent Runs & Steps
    op.create_table(
        'agent_runs',
        sa.Column('run_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.String(50), nullable=True),
        sa.Column('completed_at', sa.String(50), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False)
    )
    op.create_index('ix_agent_runs_tenant_id', 'agent_runs', ['tenant_id'])

    op.create_table(
        'agent_steps',
        sa.Column('step_id', sa.String(50), primary_key=True),
        sa.Column('run_id', sa.String(50), sa.ForeignKey('agent_runs.run_id'), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('agent', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('input_hash', sa.String(64), nullable=True),
        sa.Column('input_data', sa.Text(), nullable=True),
        sa.Column('output_data', sa.Text(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False)
    )
    op.create_index('ix_agent_steps_tenant_id', 'agent_steps', ['tenant_id'])

    # 4. Campaigns, Content & Deliveries
    op.create_table(
        'campaigns',
        sa.Column('campaign_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('opportunity_id', sa.String(50), nullable=True),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('objective', sa.String(100), nullable=False, server_default='recover_abandoned_carts'),
        sa.Column('segment_id', sa.String(50), nullable=True),
        sa.Column('mode', sa.String(20), nullable=False, server_default='demo'),
        sa.Column('status', sa.String(50), nullable=False, server_default='draft'),
        sa.Column('discount', sa.Text(), nullable=True),
        sa.Column('budget_total', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('per_customer_cap', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('scheduled_at', sa.String(50), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_simulated', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.String(50), nullable=False),
        sa.Column('updated_at', sa.String(50), nullable=True)
    )
    op.create_index('ix_campaigns_tenant_id', 'campaigns', ['tenant_id'])

    op.create_table(
        'campaign_content',
        sa.Column('content_id', sa.String(50), primary_key=True),
        sa.Column('campaign_id', sa.String(50), sa.ForeignKey('campaigns.campaign_id'), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('variant', sa.String(50), nullable=False),
        sa.Column('subject', sa.String(200), nullable=True),
        sa.Column('preheader', sa.String(200), nullable=True),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('cta', sa.String(100), nullable=False),
        sa.Column('source', sa.String(50), nullable=False, server_default='ai'),
        sa.Column('lint_result', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False)
    )
    op.create_index('ix_campaign_content_tenant_id', 'campaign_content', ['tenant_id'])

    op.create_table(
        'campaign_deliveries',
        sa.Column('delivery_id', sa.String(50), primary_key=True),
        sa.Column('campaign_id', sa.String(50), sa.ForeignKey('campaigns.campaign_id'), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('customer_id', sa.String(50), nullable=False),
        sa.Column('channel', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False, server_default='queued'),
        sa.Column('provider_message_id', sa.String(100), nullable=True),
        sa.Column('idempotency_key', sa.String(150), unique=True, nullable=False),
        sa.Column('is_simulated', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('status_at', sa.String(50), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False)
    )
    op.create_index('ix_campaign_deliveries_tenant_id', 'campaign_deliveries', ['tenant_id'])

    # 5. Experiments, Assignments & Learning Signals
    op.create_table(
        'experiments',
        sa.Column('experiment_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('campaign_id', sa.String(50), nullable=False),
        sa.Column('holdout_pct', sa.Float(), nullable=False, server_default='20.0'),
        sa.Column('start_at', sa.String(50), nullable=True),
        sa.Column('end_at', sa.String(50), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='running'),
        sa.Column('verdict', sa.String(100), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('is_simulated', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.String(50), nullable=False)
    )
    op.create_index('ix_experiments_tenant_id', 'experiments', ['tenant_id'])

    op.create_table(
        'experiment_assignments',
        sa.Column('assignment_id', sa.String(50), primary_key=True),
        sa.Column('experiment_id', sa.String(50), sa.ForeignKey('experiments.experiment_id'), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('customer_id', sa.String(50), nullable=False),
        sa.Column('arm', sa.String(50), nullable=False),
        sa.Column('assigned_at', sa.String(50), nullable=False),
        sa.UniqueConstraint('experiment_id', 'customer_id', name='uq_exp_assignments_exp_cust')
    )
    op.create_index('ix_experiment_assignments_tenant_id', 'experiment_assignments', ['tenant_id'])

    op.create_table(
        'learning_signals',
        sa.Column('signal_id', sa.String(50), primary_key=True),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('opportunity_type', sa.String(100), nullable=False),
        sa.Column('product_id', sa.String(50), nullable=True),
        sa.Column('segment_key', sa.String(100), nullable=True),
        sa.Column('observed_uplift', sa.Float(), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('source_experiment_id', sa.String(50), nullable=True),
        sa.Column('is_simulated', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.String(50), nullable=False)
    )
    op.create_index('ix_learning_signals_tenant_id', 'learning_signals', ['tenant_id'])

    # 6. Copilot Messages
    op.create_table(
        'copilot_messages',
        sa.Column('message_id', sa.String(50), primary_key=True),
        sa.Column('conversation_id', sa.String(50), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('user_id', sa.String(50), nullable=False),
        sa.Column('role', sa.String(50), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tool_calls', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(50), nullable=False)
    )
    op.create_index('ix_copilot_messages_tenant_id', 'copilot_messages', ['tenant_id'])
    op.create_index('ix_copilot_messages_conv_id', 'copilot_messages', ['conversation_id'])

    # 7. Opportunity Events
    op.create_table(
        'opportunity_events',
        sa.Column('event_id', sa.String(50), primary_key=True),
        sa.Column('opportunity_id', sa.String(50), sa.ForeignKey('opportunities.opportunity_id'), nullable=False),
        sa.Column('tenant_id', sa.String(50), nullable=False, server_default='tenant_demo_001'),
        sa.Column('from_state', sa.String(50), nullable=True),
        sa.Column('to_state', sa.String(50), nullable=False),
        sa.Column('actor_id', sa.String(100), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('occurred_at', sa.String(50), nullable=False)
    )
    op.create_index('ix_opportunity_events_tenant_id', 'opportunity_events', ['tenant_id'])

    # 8. Opportunities extensions
    with op.batch_alter_table('opportunities') as batch_op:
        batch_op.add_column(sa.Column('title', sa.String(200), nullable=True))
        batch_op.add_column(sa.Column('description', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('root_cause', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('affected_customers', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('product_id', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('supporting_analytics', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('strategy', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('est_revenue_impact', sa.Float(), nullable=False, server_default='0.0'))
        batch_op.add_column(sa.Column('est_profit_impact', sa.Float(), nullable=False, server_default='0.0'))
        batch_op.add_column(sa.Column('risk_level', sa.String(50), nullable=False, server_default='medium'))
        batch_op.add_column(sa.Column('approval_status', sa.String(50), nullable=False, server_default='pending'))
        batch_op.add_column(sa.Column('execution_status', sa.String(50), nullable=False, server_default='not_started'))
        batch_op.add_column(sa.Column('lifecycle_state', sa.String(50), nullable=False, server_default='detected'))
        batch_op.add_column(sa.Column('agent_run_id', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('guardrail_result', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('impact_inputs', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('updated_at', sa.String(50), nullable=True))

    # 9. Audit Logs extensions
    with op.batch_alter_table('audit_logs') as batch_op:
        batch_op.add_column(sa.Column('event_type', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('actor_type', sa.String(50), nullable=False, server_default='user'))
        batch_op.add_column(sa.Column('actor_id', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('entity_type', sa.String(50), nullable=True))
        batch_op.add_column(sa.Column('entity_id', sa.String(100), nullable=True))
        batch_op.add_column(sa.Column('status', sa.String(50), nullable=False, server_default='success'))


def downgrade() -> None:
    op.drop_table('opportunity_events')
    op.drop_table('copilot_messages')
    op.drop_table('learning_signals')
    op.drop_table('experiment_assignments')
    op.drop_table('experiments')
    op.drop_table('campaign_deliveries')
    op.drop_table('campaign_content')
    op.drop_table('campaigns')
    op.drop_table('agent_steps')
    op.drop_table('agent_runs')
    op.drop_table('segments')
    op.drop_table('payments')

