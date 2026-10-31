"""
Opportunity Lifecycle & State Machine Service (§9.3, FR-023 to FR-031)
Enforces server-side state transitions, deterministic impact recalculation, role-based approval, and audit trails.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from backend.app.db.models import get_db_connection
from backend.app.agents.guardrail_agent import evaluate_guardrails
from backend.app.agents.strategy_agent import calculate_opportunity_impact
from backend.app.tools.scoring import score_opportunity
from backend.app.audit.service import CentralizedAuditService


VALID_TRANSITIONS = {
    "detected": {"analysed"},
    "analysed": {"pending_approval", "approved", "rejected"},
    "pending_approval": {"approved", "rejected"},
    "approved": {"executing", "pending_approval"},
    "executing": {"completed", "failed", "evaluated"},
    "completed": {"evaluated"},
    "failed": {"executing"},
    "rejected": set(),
    "evaluated": set()
}

ALLOWED_APPROVER_ROLES = {"owner", "admin", "marketing_manager", "growth_manager"}


class OpportunityException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, details: Optional[Any] = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class InvalidTransitionException(OpportunityException):
    def __init__(self, from_state: str, to_state: str):
        super().__init__(
            code="INVALID_TRANSITION",
            message=f"Cannot transition opportunity from '{from_state}' to '{to_state}'.",
            status_code=409
        )


class InsufficientRoleException(OpportunityException):
    def __init__(self, role: str):
        super().__init__(
            code="INSUFFICIENT_ROLE",
            message=f"Role '{role}' is not authorized to approve opportunities. Required: owner, admin, or marketing_manager.",
            status_code=403
        )


class GuardrailBlockedException(OpportunityException):
    def __init__(self, rules: List[Dict[str, Any]]):
        super().__init__(
            code="GUARDRAIL_BLOCKED",
            message="Opportunity approval blocked by active safety guardrails.",
            status_code=422,
            details={"rules": rules}
        )


class MissingReasonException(OpportunityException):
    def __init__(self):
        super().__init__(
            code="MISSING_REASON",
            message="Rejection reason is mandatory and cannot be empty.",
            status_code=422
        )


class OpportunityNotFoundException(OpportunityException):
    def __init__(self, opportunity_id: str, tenant_id: str):
        super().__init__(
            code="NOT_FOUND",
            message=f"Opportunity '{opportunity_id}' not found for tenant '{tenant_id}'.",
            status_code=404
        )


def normalize_lifecycle_state(state: Optional[str]) -> str:
    s = (state or "detected").lower().strip()
    if s == "open":
        return "pending_approval"
    return s


def parse_json_safely(val: Any, default: Any = None) -> Any:
    if val is None:
        return default
    if isinstance(val, (dict, list)):
        return val
    try:
        return json.loads(val)
    except Exception:
        return default


class OpportunityService:
    @staticmethod
    def _format_opportunity_dict(row_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Formats an SQLite row dictionary into the standard Section 9.3 / Section 13 contract."""
        root_cause = parse_json_safely(row_dict.get("root_cause"), {})
        affected_customers = parse_json_safely(row_dict.get("affected_customers"), {"count": 0})
        supporting_analytics = parse_json_safely(row_dict.get("supporting_analytics"), {})
        strategy = parse_json_safely(row_dict.get("strategy"), {})
        guardrail_result = parse_json_safely(row_dict.get("guardrail_result"), {"decision": "REQUIRE_APPROVAL", "rules": []})
        impact_inputs = parse_json_safely(row_dict.get("impact_inputs"), {})

        opp_id = row_dict.get("opportunity_id") or row_dict.get("id")
        confidence = float(row_dict.get("confidence") or 0.5)
        urgency = float(row_dict.get("urgency_factor") or 1.0)
        rev_impact = float(row_dict.get("est_revenue_impact") or row_dict.get("expected_impact") or 0.0)
        profit_impact = float(row_dict.get("est_profit_impact") or (rev_impact * 0.5 - 11424.0))
        priority_score = float(row_dict.get("priority_score") or round(rev_impact * confidence * urgency, 2))
        lifecycle_state = normalize_lifecycle_state(row_dict.get("lifecycle_state"))

        score_info = score_opportunity(
            insight={},
            expected_impact_revenue=rev_impact,
            confidence=confidence,
            urgency_factor=urgency,
            feasibility=90.0
        )

        prod_id = row_dict.get("product_id") or "PROD-002"
        prod_name = "Earbud Charging Stand" if prod_id == "PROD-002" else ("Pulse GPS Smartwatch Pro" if prod_id == "PROD-B01" else ("Heart Rate Chest Strap" if prod_id == "PROD-B03" else prod_id))

        target_seg = (strategy.get("target_segment") if isinstance(strategy, dict) else None) or (affected_customers.get("segment") if isinstance(affected_customers, dict) else None) or ("18–25" if row_dict.get("tenant_id") == "tenant_store_alpha" else "Marathon Runners")
        aff_count = affected_customers.get("count", 850) if isinstance(affected_customers, dict) else 850

        disc_val = strategy.get("discount_pct", 8.0) if isinstance(strategy, dict) else 8.0
        proposed_action = (strategy.get("proposed_action") if isinstance(strategy, dict) else None) or f"Personalised {disc_val:.0f}% offer"

        root_cause_text = "Derived from event analysis"
        if isinstance(root_cause, dict):
            root_cause_text = root_cause.get("summary") or root_cause.get("narrative") or "Derived from event analysis"
        elif isinstance(root_cause, str) and root_cause:
            root_cause_text = root_cause

        status_display = "Pending Approval" if lifecycle_state in ["analysed", "pending_approval"] else lifecycle_state.replace("_", " ").title()
        if row_dict.get("status") == "rejected" or lifecycle_state == "rejected":
            status_display = "Rejected"
        elif lifecycle_state == "approved":
            status_display = "Approved"
        elif lifecycle_state == "executing":
            status_display = "Executing"
        elif lifecycle_state == "completed":
            status_display = "Completed"
        elif lifecycle_state == "evaluated":
            status_display = "Evaluated"

        # Determine Category
        opp_title_lower = (row_dict.get("title") or "").lower()
        opp_prob_lower = (row_dict.get("problem") or "").lower()
        strat_type = (strategy.get("type") or "").lower() if isinstance(strategy, dict) else ""

        if "cart" in opp_title_lower or "cart" in opp_prob_lower or "abandon" in opp_title_lower or "abandon" in opp_prob_lower or strat_type == "targeted_discount":
            category = "Cart Recovery"
            cat_badge_color = "amber"
        elif "win-back" in opp_title_lower or "winback" in opp_title_lower or "lapsed" in opp_title_lower or "churn" in opp_title_lower or strat_type == "vip_winback":
            category = "Win-Back & Retention"
            cat_badge_color = "rose"
        elif "upgrade" in opp_title_lower or "cross-sell" in opp_title_lower or "add-on" in opp_title_lower or strat_type in ["cross_sell", "upsell"]:
            category = "Cross-Sell & Upsell"
            cat_badge_color = "indigo"
        elif "bundle" in opp_title_lower or "pack" in opp_title_lower or strat_type == "bundle":
            category = "Bundle & Pricing"
            cat_badge_color = "emerald"
        else:
            category = strategy.get("category", "Growth Strategy") if isinstance(strategy, dict) else "Growth Strategy"
            cat_badge_color = "sky"

        # Estimated campaign cost
        if isinstance(impact_inputs, dict) and impact_inputs.get("discount_cost") is not None:
            est_cost = float(impact_inputs["discount_cost"])
        elif isinstance(strategy, dict) and strategy.get("budget"):
            est_cost = float(strategy["budget"])
        else:
            est_cost = round(rev_impact * (disc_val / 100.0), 2)

        # Supporting business data summary text
        supp_text = []
        if isinstance(supporting_analytics, dict):
            if supporting_analytics.get("cart_abandonment_pct"):
                supp_text.append(f"{supporting_analytics['cart_abandonment_pct']}% Cart Abandonment")
            if supporting_analytics.get("baseline_conversion_pct") and supporting_analytics.get("target_conversion_pct"):
                supp_text.append(f"Baseline CR {supporting_analytics['baseline_conversion_pct']}% → Target {supporting_analytics['target_conversion_pct']}%")
            if supporting_analytics.get("base_price"):
                supp_text.append(f"Base Price ₹{supporting_analytics['base_price']:,.0f}")
            if supporting_analytics.get("churn_risk_pct"):
                supp_text.append(f"{supporting_analytics['churn_risk_pct']}% Churn Risk")
            if supporting_analytics.get("avg_days_inactive"):
                supp_text.append(f"{supporting_analytics['avg_days_inactive']} Days Inactive")
            if supporting_analytics.get("at_risk_count"):
                supp_text.append(f"{supporting_analytics['at_risk_count']} At-Risk Profiles")
        
        supporting_data_str = " · ".join(supp_text) if supp_text else f"{aff_count} affected buyers · Est. Impact ₹{rev_impact:,.0f}"

        return {
            "id": opp_id,
            "opportunity_id": opp_id,
            "tenant_id": row_dict.get("tenant_id"),
            "insight_id": row_dict.get("insight_id"),
            "opportunity": row_dict.get("title") or (row_dict.get("problem", "").split(".")[0]) or "High cart abandonment",
            "title": row_dict.get("title") or (row_dict.get("problem", "").split(".")[0]),
            "description": row_dict.get("description") or row_dict.get("problem", ""),
            "problem": row_dict.get("problem", ""),
            "category": category,
            "category_badge_color": cat_badge_color,
            "product": prod_name,
            "product_name": prod_name,
            "product_id": prod_id,
            "target_segment": target_seg,
            "affected_customers": affected_customers,
            "affected_customers_count": aff_count,
            "root_cause": root_cause,
            "root_cause_text": root_cause_text,
            "proposed_action": proposed_action,
            "supporting_analytics": supporting_analytics,
            "supporting_business_data": supporting_data_str,
            "strategy": strategy,
            "est_revenue_impact": {
                "value": rev_impact,
                "currency": "INR",
                "inputs": impact_inputs or {"formula": "16.6"}
            },
            "est_profit_impact": {
                "value": profit_impact,
                "currency": "INR"
            },
            "estimated_impact": rev_impact,
            "estimated_campaign_cost": est_cost,
            "estimated_cost": est_cost,
            "confidence": confidence,
            "confidence_pct": round(confidence * 100, 1),
            "priority": {
                "score": priority_score,
                "normalized_score": score_info["normalized_priority"],
                "formula": score_info["formula"],
                "weights": score_info["weights"],
                "components": score_info["components"]
            },
            "priority_score": priority_score,
            "priority_normalized": score_info["normalized_priority"],
            "scoring_breakdown": score_info,
            "priority_rank": row_dict.get("priority_rank", 1),
            "risk": row_dict.get("risk_level", "medium").title(),
            "risk_level": row_dict.get("risk_level", "medium"),
            "status": status_display,
            "approval_status": row_dict.get("approval_status", "pending"),
            "execution_status": row_dict.get("execution_status", "not_started"),
            "lifecycle_state": lifecycle_state,
            "status_display": status_display,
            "recommended_action": row_dict.get("recommended_action") or proposed_action,
            "guardrail": guardrail_result,
            "guardrail_result": guardrail_result,
            "approved_by": row_dict.get("approved_by"),
            "rejected_by": row_dict.get("rejected_by"),
            "rejection_reason": row_dict.get("rejection_reason"),
            "created_at": row_dict.get("created_at"),
            "updated_at": row_dict.get("updated_at"),
            "is_simulated": False
        }

    @classmethod
    def list_opportunities(
        cls,
        tenant_id: str,
        status: Optional[str] = None,
        risk: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Returns opportunities ranked by priority, filterable by status and risk."""
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM opportunities WHERE tenant_id = ?"
        params: List[Any] = [tenant_id]

        if status:
            s_clean = status.lower().strip()
            query += " AND (LOWER(lifecycle_state) = ? OR LOWER(status) = ? OR LOWER(approval_status) = ?)"
            params.extend([s_clean, s_clean, s_clean])

        if risk:
            query += " AND LOWER(risk_level) = ?"
            params.append(risk.lower().strip())

        query += " ORDER BY priority_score DESC, priority_rank ASC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [cls._format_opportunity_dict(dict(r)) for r in rows]

    @classmethod
    def get_opportunities_analytics(cls, tenant_id: str) -> Dict[str, Any]:
        """Returns aggregated opportunity analytics: total pipeline revenue, category distribution, revenue comparison chart data, and ranked opportunities."""
        opps = cls.list_opportunities(tenant_id=tenant_id, limit=50)
        total_rev_pipeline = sum(float(o.get("estimated_impact") or 0.0) for o in opps)
        avg_priority = round(sum(float(o.get("priority_normalized") or 0.0) for o in opps) / len(opps), 1) if opps else 0.0
        
        # Category distribution
        cat_map: Dict[str, Dict[str, Any]] = {}
        for o in opps:
            cat = o.get("category", "Growth Strategy")
            if cat not in cat_map:
                cat_map[cat] = {"count": 0, "total_revenue": 0.0, "opportunities": []}
            cat_map[cat]["count"] += 1
            cat_map[cat]["total_revenue"] += float(o.get("estimated_impact") or 0.0)
            cat_map[cat]["opportunities"].append(o["id"])
            
        category_distribution = []
        palette = ["#4f46e5", "#0ea5e9", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6"]
        for idx, (cat_name, data) in enumerate(cat_map.items()):
            share = round((data["total_revenue"] / total_rev_pipeline * 100), 1) if total_rev_pipeline > 0 else 0.0
            category_distribution.append({
                "category": cat_name,
                "count": data["count"],
                "total_revenue": round(data["total_revenue"], 2),
                "percentage_share": share,
                "color": palette[idx % len(palette)]
            })
        category_distribution.sort(key=lambda x: x["total_revenue"], reverse=True)
        
        # Revenue comparison chart data
        revenue_comparison = [
            {
                "id": o["id"],
                "title": o["title"],
                "category": o.get("category", "Growth Strategy"),
                "revenue_impact": o.get("estimated_impact", 0.0),
                "estimated_cost": o.get("estimated_campaign_cost", 0.0),
                "priority_normalized": o.get("priority_normalized", 0.0),
                "confidence_pct": o.get("confidence_pct", round(o.get("confidence", 0.5) * 100, 1)),
                "risk_level": o.get("risk_level", "medium"),
                "status": o.get("status", "Pending Approval")
            }
            for o in sorted(opps, key=lambda x: float(x.get("estimated_impact") or 0.0), reverse=True)
        ]
        
        return {
            "summary": {
                "total_opportunities": len(opps),
                "total_potential_revenue": round(total_rev_pipeline, 2),
                "average_priority_score": avg_priority,
                "pending_approval_count": sum(1 for o in opps if o.get("lifecycle_state") in ["analysed", "pending_approval"]),
                "approved_count": sum(1 for o in opps if o.get("lifecycle_state") == "approved"),
                "executing_count": sum(1 for o in opps if o.get("lifecycle_state") == "executing"),
            },
            "category_distribution": category_distribution,
            "revenue_comparison": revenue_comparison,
            "ranked_opportunities": opps
        }

    @classmethod
    def get_opportunity_detail(cls, tenant_id: str, opportunity_id: str) -> Dict[str, Any]:
        """Returns full opportunity details including root cause, evidence references, guardrails, and event history."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM opportunities 
            WHERE opportunity_id = ? AND tenant_id = ?
        """, (opportunity_id, tenant_id))
        row = cursor.fetchone()

        if not row:
            conn.close()
            raise OpportunityNotFoundException(opportunity_id, tenant_id)

        opp_dict = cls._format_opportunity_dict(dict(row))

        # Fetch transition history
        cursor.execute("""
            SELECT event_id, opportunity_id, tenant_id, from_state, to_state, actor_id, reason, occurred_at
            FROM opportunity_events
            WHERE opportunity_id = ? AND tenant_id = ?
            ORDER BY occurred_at ASC
        """, (opportunity_id, tenant_id))
        history_rows = cursor.fetchall()
        opp_dict["history"] = [dict(h) for h in history_rows]

        # Check linked campaign
        cursor.execute("""
            SELECT campaign_id, objective, status, budget_total, scheduled_at, is_simulated
            FROM campaigns
            WHERE opportunity_id = ? AND tenant_id = ?
            LIMIT 1
        """, (opportunity_id, tenant_id))
        camp_row = cursor.fetchone()
        opp_dict["campaign"] = dict(camp_row) if camp_row else None

        conn.close()
        return opp_dict

    @classmethod
    def update_strategy(
        cls,
        tenant_id: str,
        opportunity_id: str,
        strategy_update: Dict[str, Any],
        actor_id: str = "user"
    ) -> Dict[str, Any]:
        """
        Edits opportunity strategy, recomputes impact & priority deterministically,
        and re-runs Guardrail Agent before approval is allowed.
        """
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM opportunities WHERE opportunity_id = ? AND tenant_id = ?", (opportunity_id, tenant_id))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise OpportunityNotFoundException(opportunity_id, tenant_id)

        opp = dict(row)
        current_state = normalize_lifecycle_state(opp.get("lifecycle_state"))
        if current_state in {"executing", "completed", "evaluated"}:
            conn.close()
            raise OpportunityException(
                code="IMMUTABLE_STATE",
                message=f"Cannot edit strategy for opportunity in '{current_state}' state.",
                status_code=409
            )

        # Merge strategy
        existing_strat = parse_json_safely(opp.get("strategy"), {})
        merged_strat = {**existing_strat, **{k: v for k, v in strategy_update.items() if v is not None}}

        # Product & pricing context
        prod_id = opp.get("product_id") or "PROD-002"
        base_price = 1200.0
        margin_pct = 45.0
        cursor.execute("SELECT base_price, margin_pct FROM products WHERE product_id = ? AND tenant_id = ?", (prod_id, tenant_id))
        p_row = cursor.fetchone()
        if p_row:
            base_price = float(p_row[0])
            margin_pct = float(p_row[1])

        affected = parse_json_safely(opp.get("affected_customers"), {"count": 850})
        audience_size = int(merged_strat.get("audience_size") or affected.get("count", 850))
        discount_pct = float(merged_strat.get("discount_pct", 8.0))
        baseline_conv = float(merged_strat.get("baseline_conversion_pct", 6.0))
        expected_conv = float(merged_strat.get("expected_conversion_pct", 14.0))

        # Deterministic impact calculation (§16.6)
        rev_impact, profit_impact, impact_inputs = calculate_opportunity_impact(
            audience_size=audience_size,
            base_price=base_price,
            baseline_conversion_pct=baseline_conv,
            expected_conversion_pct=expected_conv,
            margin_pct=margin_pct,
            discount_pct=discount_pct
        )

        confidence = float(opp.get("confidence") or 0.78)
        urgency = float(opp.get("urgency_factor") or 1.25)
        score_meta = score_opportunity({}, rev_impact, confidence, urgency)
        priority_score = score_meta["priority_score"]

        # Run Guardrail validation
        guardrail_proposal = {
            "opportunity_id": opportunity_id,
            "tenant_id": tenant_id,
            "offer_pct": discount_pct,
            "discount_pct": discount_pct,
            "audience_size": audience_size,
            "channels": merged_strat.get("channels") or [merged_strat.get("channel", "email")],
            "content": merged_strat.get("note") or opp.get("problem", ""),
            "estimated_cost": impact_inputs.get("discount_cost", 0.0),
            "mode": "demo"
        }
        product_info = {"margin_pct": margin_pct, "base_price": base_price}
        guardrail_res = evaluate_guardrails(guardrail_proposal, tenant_id=tenant_id, product_info=product_info)
        guardrail_dict = guardrail_res.model_dump()

        # Determine new lifecycle state
        new_state = "analysed"
        if guardrail_res.decision in ["ALLOW", "REQUIRE_APPROVAL"]:
            new_state = "pending_approval"

        now_iso = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            UPDATE opportunities
            SET strategy = ?,
                est_revenue_impact = ?,
                est_profit_impact = ?,
                priority_score = ?,
                impact_inputs = ?,
                guardrail_result = ?,
                risk_level = ?,
                lifecycle_state = ?,
                updated_at = ?
            WHERE opportunity_id = ? AND tenant_id = ?
        """, (
            json.dumps(merged_strat),
            rev_impact,
            profit_impact,
            priority_score,
            json.dumps(impact_inputs),
            json.dumps(guardrail_dict),
            guardrail_res.risk_tier,
            new_state,
            now_iso,
            opportunity_id,
            tenant_id
        ))

        # Record event in opportunity_events
        event_id = f"EVT-{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO opportunity_events (event_id, opportunity_id, tenant_id, from_state, to_state, actor_id, reason, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            opportunity_id,
            tenant_id,
            current_state,
            new_state,
            actor_id,
            f"Strategy modified: discount={discount_pct}%, guardrail={guardrail_res.decision}",
            now_iso
        ))

        conn.commit()
        conn.close()

        # Centralized audit event
        CentralizedAuditService.record_event(
            tenant_id=tenant_id,
            event_type="opportunity.strategy_updated",
            actor_type="user",
            actor_id=actor_id,
            entity_type="opportunity",
            entity_id=opportunity_id,
            status="success",
            metadata={
                "discount_pct": discount_pct,
                "rev_impact": rev_impact,
                "profit_impact": profit_impact,
                "priority_score": priority_score,
                "guardrail_decision": guardrail_res.decision
            }
        )

        return cls.get_opportunity_detail(tenant_id, opportunity_id)

    @classmethod
    def approve_opportunity(
        cls,
        tenant_id: str,
        opportunity_id: str,
        actor_id: str,
        actor_role: str,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approves an opportunity for campaign execution.
        Enforces:
        - Role check (owner, admin, marketing_manager, growth_manager)
        - State machine check (must be pending_approval or analysed)
        - Guardrail re-check (cannot approve if BLOCK)
        """
        clean_role = (actor_role or "growth_manager").lower().strip()
        if clean_role not in ALLOWED_APPROVER_ROLES:
            raise InsufficientRoleException(clean_role)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM opportunities WHERE opportunity_id = ? AND tenant_id = ?", (opportunity_id, tenant_id))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise OpportunityNotFoundException(opportunity_id, tenant_id)

        opp = dict(row)
        current_state = normalize_lifecycle_state(opp.get("lifecycle_state"))
        if current_state not in {"pending_approval", "analysed"}:
            conn.close()
            raise InvalidTransitionException(from_state=current_state, to_state="approved")

        # Guardrail re-check
        strat = parse_json_safely(opp.get("strategy"), {})
        discount_pct = float(strat.get("discount_pct", 8.0))
        audience_size = int(strat.get("audience_size") or 850)

        guardrail_proposal = {
            "opportunity_id": opportunity_id,
            "tenant_id": tenant_id,
            "offer_pct": discount_pct,
            "discount_pct": discount_pct,
            "audience_size": audience_size,
            "channels": strat.get("channels") or ["email"],
            "mode": "demo"
        }
        guardrail_res = evaluate_guardrails(guardrail_proposal, tenant_id=tenant_id, user_role=clean_role)
        if guardrail_res.decision == "BLOCK":
            conn.close()
            failed_rules = [r for r in guardrail_res.rules if not r.passed]
            raise GuardrailBlockedException(rules=[r.model_dump() for r in failed_rules])

        guardrail_recheck_status = "ALLOW" if guardrail_res.decision in ["ALLOW", "REQUIRE_APPROVAL"] else guardrail_res.decision

        now_iso = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            UPDATE opportunities
            SET lifecycle_state = 'approved',
                approval_status = 'approved',
                status = 'approved',
                approved_by = ?,
                updated_at = ?
            WHERE opportunity_id = ? AND tenant_id = ?
        """, (actor_id, now_iso, opportunity_id, tenant_id))

        event_id = f"EVT-{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO opportunity_events (event_id, opportunity_id, tenant_id, from_state, to_state, actor_id, reason, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            opportunity_id,
            tenant_id,
            current_state,
            "approved",
            actor_id,
            note or "Approved for execution",
            now_iso
        ))

        conn.commit()
        conn.close()

        # Audit event
        CentralizedAuditService.record_event(
            tenant_id=tenant_id,
            event_type="opportunity.approved",
            actor_type="user",
            actor_id=actor_id,
            entity_type="opportunity",
            entity_id=opportunity_id,
            status="success",
            metadata={
                "approved_by": actor_id,
                "role": clean_role,
                "note": note,
                "guardrail_recheck": guardrail_recheck_status
            }
        )

        detail = cls.get_opportunity_detail(tenant_id, opportunity_id)
        return {
            "lifecycle_state": "approved",
            "approval_status": "approved",
            "approved_by": actor_id,
            "guardrail_recheck": guardrail_recheck_status,
            "opportunity": detail
        }

    @classmethod
    def reject_opportunity(
        cls,
        tenant_id: str,
        opportunity_id: str,
        actor_id: str,
        actor_role: str,
        reason: str,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Rejects an opportunity with mandatory reason.
        Enforces:
        - Reason presence (cannot be empty)
        - State machine check (must be pending_approval or analysed)
        """
        if not reason or not reason.strip():
            raise MissingReasonException()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM opportunities WHERE opportunity_id = ? AND tenant_id = ?", (opportunity_id, tenant_id))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise OpportunityNotFoundException(opportunity_id, tenant_id)

        opp = dict(row)
        current_state = normalize_lifecycle_state(opp.get("lifecycle_state"))
        if current_state not in {"pending_approval", "analysed"}:
            conn.close()
            raise InvalidTransitionException(from_state=current_state, to_state="rejected")

        now_iso = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            UPDATE opportunities
            SET lifecycle_state = 'rejected',
                approval_status = 'rejected',
                status = 'rejected',
                rejected_by = ?,
                rejection_reason = ?,
                updated_at = ?
            WHERE opportunity_id = ? AND tenant_id = ?
        """, (actor_id, reason.strip(), now_iso, opportunity_id, tenant_id))

        event_id = f"EVT-{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO opportunity_events (event_id, opportunity_id, tenant_id, from_state, to_state, actor_id, reason, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            opportunity_id,
            tenant_id,
            current_state,
            "rejected",
            actor_id,
            reason.strip(),
            now_iso
        ))

        conn.commit()
        conn.close()

        # Audit event
        CentralizedAuditService.record_event(
            tenant_id=tenant_id,
            event_type="opportunity.rejected",
            actor_type="user",
            actor_id=actor_id,
            entity_type="opportunity",
            entity_id=opportunity_id,
            status="success",
            metadata={
                "rejected_by": actor_id,
                "reason": reason.strip(),
                "note": note
            }
        )

        detail = cls.get_opportunity_detail(tenant_id, opportunity_id)
        return {
            "lifecycle_state": "rejected",
            "approval_status": "rejected",
            "rejected_by": actor_id,
            "rejection_reason": reason.strip(),
            "opportunity": detail
        }

    @classmethod
    def transition_state(
        cls,
        tenant_id: str,
        opportunity_id: str,
        to_state: str,
        actor_id: str = "system",
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generic state machine transition for executing, completed, evaluated, failed."""
        target_state = normalize_lifecycle_state(to_state)

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM opportunities WHERE opportunity_id = ? AND tenant_id = ?", (opportunity_id, tenant_id))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise OpportunityNotFoundException(opportunity_id, tenant_id)

        opp = dict(row)
        current_state = normalize_lifecycle_state(opp.get("lifecycle_state"))

        allowed_next = VALID_TRANSITIONS.get(current_state, set())
        if target_state not in allowed_next:
            conn.close()
            raise InvalidTransitionException(from_state=current_state, to_state=target_state)

        now_iso = datetime.now(timezone.utc).isoformat()

        exec_status = opp.get("execution_status", "not_started")
        if target_state == "executing":
            exec_status = "executing"
        elif target_state == "completed":
            exec_status = "completed"
        elif target_state == "failed":
            exec_status = "failed"

        cursor.execute("""
            UPDATE opportunities
            SET lifecycle_state = ?,
                execution_status = ?,
                updated_at = ?
            WHERE opportunity_id = ? AND tenant_id = ?
        """, (target_state, exec_status, now_iso, opportunity_id, tenant_id))

        event_id = f"EVT-{uuid.uuid4().hex[:8]}"
        cursor.execute("""
            INSERT INTO opportunity_events (event_id, opportunity_id, tenant_id, from_state, to_state, actor_id, reason, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_id,
            opportunity_id,
            tenant_id,
            current_state,
            target_state,
            actor_id,
            reason or f"Transitioned to {target_state}",
            now_iso
        ))

        conn.commit()
        conn.close()

        CentralizedAuditService.record_event(
            tenant_id=tenant_id,
            event_type=f"opportunity.transition.{target_state}",
            actor_type="system" if actor_id == "system" else "user",
            actor_id=actor_id,
            entity_type="opportunity",
            entity_id=opportunity_id,
            status="success",
            metadata={"from_state": current_state, "to_state": target_state, "reason": reason}
        )

        return cls.get_opportunity_detail(tenant_id, opportunity_id)
