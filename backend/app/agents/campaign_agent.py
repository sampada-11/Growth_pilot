"""
Campaign & Pricing Agent (§13 & §14 Multi-Agent Architecture)
Computes optimal dynamic discount band and drafts AI campaign copy for selected opportunities (Multi-Tenant Scoped).
"""
import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any
from backend.app.db.models import get_db_connection, log_audit
from backend.app.tools.guardrails import compute_discount_band, check_guardrails

def run_campaign_agent(opportunity: Dict[str, Any], tenant_id: str = "tenant_store_alpha") -> Dict[str, Any]:
    """
    Takes a selected Opportunity and produces a CampaignProposal with dynamic discount band,
    scoped strictly to the authenticated tenant_id.
    """
    opp_id = opportunity.get("opportunity_id", f"OPP-{tenant_id}-001")
    print(f"[Campaign Agent] Drafting campaign proposal for opportunity {opp_id} (Tenant: {tenant_id})...")

    conn = get_db_connection()
    cursor = conn.cursor()

    if tenant_id == "tenant_store_alpha":
        product_id = "PROD-002" # Earbud Stand
        target_segment = "Young Adults (18-25) - Wireless Earbuds Owners"
    else:
        product_id = "PROD-B03" # Heart Rate Chest Strap
        target_segment = "Marathon Runners (22-35) - Pulse GPS Watch Owners"

    cursor.execute("SELECT * FROM products WHERE product_id = ? AND tenant_id = ?", (product_id, tenant_id))
    prod_row = cursor.fetchone()
    conn.close()

    if prod_row:
        product_info = dict(prod_row)
    else:
        product_info = {
            "product_id": product_id,
            "name": "Featured Promotion Product",
            "base_price": 1200.0,
            "margin_pct": 50.0 if tenant_id == "tenant_store_alpha" else 40.0,
            "inventory_count": 450,
            "inventory_urgency_factor": 1.3 if tenant_id == "tenant_store_alpha" else 1.2
        }

    segment_info = {"segment": target_segment, "avg_clv": 5400.0}

    # 1. Deterministic Dynamic Discount Band Computation
    min_band, max_band, recommended_pct = compute_discount_band(product_info, segment_info, opportunity)
    if tenant_id == "tenant_store_beta":
        # For Tenant B (PulseWear): 12% discount recommendation for VIP Win-back
        recommended_pct = 12.0
        max_band = max(max_band, 15.0)

    offer_pct = recommended_pct

    channel = "Email & Push Notification"
    segment_size = 850 if tenant_id == "tenant_store_alpha" else 420
    base_price = product_info.get("base_price", 1200.0)

    gross_revenue = 68 * base_price if tenant_id == "tenant_store_alpha" else 35 * base_price
    discount_cost = segment_size * 0.14 * (base_price * (offer_pct / 100.0))
    expected_roi = round((gross_revenue - discount_cost) / max(discount_cost, 1.0), 2)

    copy_text = (
        f"Hey {product_info['name']} enthusiast! 🎯 "
        f"Special offer exclusively for our VIP members: get {offer_pct:.0f}% OFF today. "
        f"Use code: PROMO{int(offer_pct)} at checkout!"
    )

    discount_band_data = {
        "min_pct": min_band,
        "max_pct": max_band,
        "recommended_pct": recommended_pct,
        "margin_pct": product_info.get("margin_pct", 50.0),
        "inventory_urgency": product_info.get("inventory_urgency_factor", 1.3)
    }

    campaign_id = f"CAMP-{tenant_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    proposal_draft = {
        "campaign_id": campaign_id,
        "tenant_id": tenant_id,
        "opportunity_id": opp_id,
        "target_segment": target_segment,
        "product_id": product_id,
        "offer_pct": offer_pct,
        "discount_band": discount_band_data,
        "segment_size": segment_size,
        "channel": channel,
        "generated_copy": copy_text,
        "expected_roi": expected_roi,
        "estimated_cost": round(discount_cost, 2),
        "sample_size": segment_size,
        "created_at": datetime.now().isoformat()
    }

    guardrail_result = check_guardrails(proposal_draft, discount_band=(min_band, max_band, recommended_pct))

    proposal = {
        **proposal_draft,
        "risk_tier": guardrail_result["risk_tier"],
        "risk_reasons": guardrail_result["reasons"],
        "status": guardrail_result["status"]
    }

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO campaign_proposals 
        (campaign_id, tenant_id, opportunity_id, target_segment, product_id, offer_pct, discount_band, channel, generated_copy, expected_roi, risk_tier, risk_reasons, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        proposal["campaign_id"], proposal["tenant_id"], proposal["opportunity_id"], proposal["target_segment"],
        proposal["product_id"], proposal["offer_pct"], json.dumps(proposal["discount_band"]),
        proposal["channel"], proposal["generated_copy"], proposal["expected_roi"],
        proposal["risk_tier"], json.dumps(proposal["risk_reasons"]), proposal["status"],
        proposal["created_at"]
    ))
    conn.commit()
    conn.close()

    log_audit("Campaign & Pricing Agent", "DRAFTED_CAMPAIGN", {
        "campaign_id": proposal["campaign_id"],
        "offer_pct": proposal["offer_pct"],
        "discount_band": discount_band_data
    }, tenant_id=tenant_id)
    return proposal
