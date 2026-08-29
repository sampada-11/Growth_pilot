"""
Campaign & Pricing Agent (§13 & §14 Multi-Agent Architecture)
Computes optimal dynamic discount band and drafts AI campaign copy for selected opportunities.
"""
import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Any
from backend.app.db.models import get_db_connection, log_audit
from backend.app.tools.guardrails import compute_discount_band, check_guardrails

def run_campaign_agent(opportunity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Takes a selected Opportunity and produces a CampaignProposal with dynamic discount band,
    recommended offer %, target segment, channel choice, generated message copy, expected ROI,
    and guardrail risk evaluation.
    """
    opp_id = opportunity.get("opportunity_id", "OPP-001")
    print(f"[Campaign Agent] Drafting campaign proposal for opportunity {opp_id}...")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Query product margin and inventory info
    product_id = "PROD-002"
    cursor.execute("SELECT * FROM products WHERE product_id = ?", (product_id,))
    prod_row = cursor.fetchone()
    conn.close()

    product_info = dict(prod_row) if prod_row else {
        "product_id": "PROD-002",
        "name": "Earbud Case & Charging Stand",
        "base_price": 1200.0,
        "margin_pct": 50.0,
        "inventory_count": 450,
        "inventory_urgency_factor": 1.3
    }

    target_segment = "Young Adults (18-25) - Wireless Earbuds Owners"
    segment_info = {"segment": target_segment, "avg_clv": 5400.0}

    # 1. Deterministic Dynamic Discount Band Computation
    min_band, max_band, recommended_pct = compute_discount_band(product_info, segment_info, opportunity)
    offer_pct = recommended_pct # Use the dynamically computed recommended discount (e.g. 8.0%)

    channel = "Email & Push Notification"
    segment_size = 850
    base_price = product_info.get("base_price", 1200.0)

    # Calculated financial estimates
    # Incremental conversion lift: 8% of 850 = 68 units
    gross_revenue = 68 * base_price
    discount_cost = 850 * 0.14 * (base_price * (offer_pct / 100.0))
    expected_roi = round((gross_revenue - discount_cost) / max(discount_cost, 1.0), 2)

    # Generate message copy
    copy_text = (
        f"Hey sound lover! 🎧 We noticed you recently grabbed Wireless Earbuds Pro. "
        f"Keep your battery full and your case protected everywhere you go! "
        f"For a limited time, get {offer_pct:.0f}% OFF the official Earbud Charging Stand & Case. "
        f"Use code: SOUNDPOWER{int(offer_pct)} at checkout!"
    )

    discount_band_data = {
        "min_pct": min_band,
        "max_pct": max_band,
        "recommended_pct": recommended_pct,
        "margin_pct": product_info.get("margin_pct", 50.0),
        "inventory_urgency": product_info.get("inventory_urgency_factor", 1.3)
    }

    proposal_draft = {
        "campaign_id": f"CAMP-{datetime.now().strftime('%Y%m%d%H%M%S')}",
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

    # Evaluate dynamic guardrails
    guardrail_result = check_guardrails(proposal_draft, discount_band=(min_band, max_band, recommended_pct))

    proposal = {
        **proposal_draft,
        "risk_tier": guardrail_result["risk_tier"],
        "risk_reasons": guardrail_result["reasons"],
        "status": guardrail_result["status"]
    }

    # Save to DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO campaign_proposals 
        (campaign_id, opportunity_id, target_segment, product_id, offer_pct, discount_band, channel, generated_copy, expected_roi, risk_tier, risk_reasons, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        proposal["campaign_id"], proposal["opportunity_id"], proposal["target_segment"],
        proposal["product_id"], proposal["offer_pct"], json.dumps(proposal["discount_band"]),
        proposal["channel"], proposal["generated_copy"], proposal["expected_roi"],
        proposal["risk_tier"], json.dumps(proposal["risk_reasons"]), proposal["status"],
        proposal["created_at"]
    ))
    conn.commit()
    conn.close()

    log_audit("Campaign & Pricing Agent", "DRAFTED_CAMPAIGN", {
        "campaign_id": proposal["campaign_id"],
        "risk_tier": proposal["risk_tier"],
        "offer_pct": proposal["offer_pct"],
        "discount_band": discount_band_data
    })
    print(f"[Campaign Agent] Drafted proposal {proposal['campaign_id']} with dynamic band {min_band}%-{max_band}% (Offer: {offer_pct}%).")
    return proposal
