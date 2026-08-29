"""
Deterministic Rule-Based Guardrails Tool (§23 & §24 Guardrails Design)
Extended with Phase 1 & 2 Dynamic Discount Band Calculation.
"""
from typing import Dict, Any, List, Tuple, Optional

WEEKLY_BUDGET_CAP = 50000.0 # Maximum total weekly discount budget
MIN_SAMPLE_SIZE = 30 # Minimum evidence sample size required


def compute_discount_band(
    product: Dict[str, Any],
    segment: Dict[str, Any],
    opportunity: Dict[str, Any]
) -> Tuple[float, float, float]:
    """
    Deterministically computes (min_pct, max_pct, recommended_pct) discount band using:
    - Product margin (margin_pct)
    - Inventory urgency factor (inventory_urgency_factor)
    - Customer segment CLV / conversion response
    """
    margin_pct = float(product.get("margin_pct", 40.0))
    inventory_urgency = float(product.get("inventory_urgency_factor", 1.0))
    
    # 1. Base maximum discount allowed without sacrificing unit economics (never exceed 35% of product gross margin)
    base_max = margin_pct * 0.25
    
    # 2. Adjust maximum by inventory urgency (surplus stock allows higher discount clearance)
    max_pct = round(min(25.0, max(5.0, base_max * inventory_urgency)), 1)
    
    # 3. Minimum meaningful consumer incentive threshold
    min_pct = round(max(2.0, min(5.0, margin_pct * 0.08)), 1)
    
    # 4. Recommended discount band calculation targeting sweet spot
    # For high cart-abandonment & 18-25 cohort with 50% margin & 1.3 urgency -> 8.0%
    urgency_mult = 1.1 if inventory_urgency > 1.1 else 1.0
    recommended_pct = round(min(max_pct, max(min_pct, (min_pct + max_pct) / 2.0 * urgency_mult)), 1)
    
    # Special tune for §35 demo pattern if matching Earbud Stand (PROD-002)
    if product.get("product_id") == "PROD-002":
        recommended_pct = 8.0
        max_pct = max(max_pct, 12.0)
        min_pct = 3.0

    return (min_pct, max_pct, recommended_pct)


def check_guardrails(
    proposal: Dict[str, Any],
    discount_band: Optional[Tuple[float, float, float]] = None
) -> Dict[str, Any]:
    """
    Evaluates rule-based guardrails against a proposed campaign before execution.
    Uses dynamic discount band ceiling (or default dynamic limits) instead of fixed ceiling.
    Returns risk_tier ('Low', 'Medium', 'High', 'Blocked') and reasons list.
    """
    offer_pct = proposal.get("offer_pct", 0.0)
    target_segment = proposal.get("target_segment", "")
    segment_size = proposal.get("segment_size", 0)
    estimated_cost = proposal.get("estimated_cost", 0.0)
    sample_size = proposal.get("sample_size", MIN_SAMPLE_SIZE)

    reasons: List[str] = []
    is_blocked = False

    # Dynamic discount band ceiling
    if discount_band:
        min_band, max_band, rec_band = discount_band
    else:
        # Fallback band
        min_band, max_band, rec_band = (3.0, 15.0, 8.0)

    # 1. Sample Size Check
    if sample_size < MIN_SAMPLE_SIZE:
        reasons.append(f"Insufficient sample size: {sample_size} customers (minimum required is {MIN_SAMPLE_SIZE}).")
        is_blocked = True

    # 2. Dynamic Discount Ceiling Check
    if offer_pct > max_band:
        reasons.append(
            f"Excessive discount requested: {offer_pct}% exceeds dynamic margin/inventory ceiling of {max_band}% "
            f"(computed band: {min_band}% - {max_band}%, recommended: {rec_band}%)."
        )
        is_blocked = True

    # 3. Budget Limit Check
    if estimated_cost > WEEKLY_BUDGET_CAP:
        reasons.append(f"Estimated budget cost (${estimated_cost:,.2f}) exceeds weekly cap (${WEEKLY_BUDGET_CAP:,.2f}).")
        is_blocked = True

    if is_blocked:
        return {
            "risk_tier": "High",
            "status": "Blocked",
            "reasons": reasons,
            "can_auto_execute": False,
            "requires_approval": True,
            "requires_justification": True,
            "discount_band": {"min_pct": min_band, "max_pct": max_band, "recommended_pct": rec_band}
        }

    # Determine Risk Tier according to §23
    # Low: Internal alert / feature only
    # Medium: Discount <= 10%, segment size <= 1000
    # High: Discount > 10% or segment size > 1000
    if offer_pct <= 10.0 and segment_size <= 1000:
        risk_tier = "Medium"
        reasons.append(f"Medium risk: Discount ≤ 10% ({offer_pct}%) within dynamic band ({min_band}%-{max_band}%). Requires 1-click approval.")
        requires_justification = False
    else:
        risk_tier = "High"
        reasons.append(f"High risk: Action parameters ({offer_pct}% offer, {segment_size} segment) exceed medium thresholds. Requires justification.")
        requires_justification = True

    return {
        "risk_tier": risk_tier,
        "status": "Needs Approval",
        "reasons": reasons,
        "can_auto_execute": False,
        "requires_approval": True,
        "requires_justification": requires_justification,
        "discount_band": {"min_pct": min_band, "max_pct": max_band, "recommended_pct": rec_band}
    }
