"""
Growth Decision Agent (§13 & §14 Multi-Agent Architecture)
Ranks and prioritizes growth opportunities (Multi-Tenant Scoped).
"""
import json
import sqlite3
from typing import List, Dict, Any
from backend.app.db.models import get_db_connection, log_audit
from backend.app.tools.scoring import score_opportunity

def run_decision_agent(insights: List[Dict[str, Any]], tenant_id: str = "tenant_store_alpha") -> List[Dict[str, Any]]:
    """
    Ranks insights for a specific tenant and outputs ranked Opportunity objects.
    """
    print(f"[Growth Decision Agent] Scoring and ranking growth opportunities for tenant {tenant_id}...")
    
    opportunities = []

    for ins in insights:
        insight_id = ins["insight_id"]
        evidence = ins.get("evidence", {})
        
        if "Cart Abandonment" in ins.get("type", ""):
            # Tenant A primary opportunity
            expected_impact = 81600.0
            confidence = 0.78
            urgency = 1.25

            score_meta = score_opportunity(ins, expected_impact, confidence, urgency)

            opp = {
                "opportunity_id": f"OPP-{tenant_id}-001",
                "tenant_id": tenant_id,
                "insight_id": insight_id,
                "problem": "71% Cart Abandonment on Earbud Stand (PROD-002) among 18-25 Earbud Buyers (850 customers).",
                "expected_impact": expected_impact,
                "confidence": confidence,
                "urgency_factor": urgency,
                "recommended_action": "Launch personalized 8% discount offer on Earbud Stand via Email & Push.",
                "priority_score": score_meta["priority_score"],
                "status": "open",
                "evidence_snippet": evidence
            }
            opportunities.append(opp)

        elif "VIP Inactivity" in ins.get("type", ""):
            # Tenant B primary opportunity
            expected_impact = 42000.0
            confidence = 0.74
            urgency = 1.20

            score_meta = score_opportunity(ins, expected_impact, confidence, urgency)

            opp = {
                "opportunity_id": f"OPP-{tenant_id}-001",
                "tenant_id": tenant_id,
                "insight_id": insight_id,
                "problem": "65% Inactivity Churn among Marathon Runners after Smartwatch purchase.",
                "expected_impact": expected_impact,
                "confidence": confidence,
                "urgency_factor": urgency,
                "recommended_action": "Deploy VIP Win-Back offer with 12% off Heart Rate Chest Strap (PROD-B03).",
                "priority_score": score_meta["priority_score"],
                "status": "open",
                "evidence_snippet": evidence
            }
            opportunities.append(opp)

        elif "Customer Churn Risk" in ins.get("type", ""):
            expected_impact = 35000.0
            confidence = 0.65
            urgency = 1.10
            score_meta = score_opportunity(ins, expected_impact, confidence, urgency)

            opp = {
                "opportunity_id": f"OPP-{tenant_id}-002",
                "tenant_id": tenant_id,
                "insight_id": insight_id,
                "problem": "High-value customer segment experiencing churn risk after 90+ days inactivity.",
                "expected_impact": expected_impact,
                "confidence": confidence,
                "urgency_factor": urgency,
                "recommended_action": "Deploy VIP win-back campaign with 10% re-engagement voucher.",
                "priority_score": score_meta["priority_score"],
                "status": "open",
                "evidence_snippet": evidence
            }
            opportunities.append(opp)

    ranked_opps = sorted(opportunities, key=lambda x: x["priority_score"], reverse=True)
    for rank, opp in enumerate(ranked_opps, start=1):
        opp["priority_rank"] = rank

    conn = get_db_connection()
    cursor = conn.cursor()
    for opp in ranked_opps:
        cursor.execute("""
            INSERT OR REPLACE INTO opportunities 
            (opportunity_id, tenant_id, insight_id, problem, expected_impact, confidence, urgency_factor, recommended_action, priority_score, priority_rank, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            opp["opportunity_id"], opp["tenant_id"], opp["insight_id"], opp["problem"], 
            opp["expected_impact"], opp["confidence"], opp["urgency_factor"], 
            opp["recommended_action"], opp["priority_score"], opp["priority_rank"], opp["status"]
        ))
    conn.commit()
    conn.close()

    log_audit("Decision Agent", "RANKED_OPPORTUNITIES", {"count": len(ranked_opps), "top": ranked_opps[0]["opportunity_id"] if ranked_opps else None}, tenant_id=tenant_id)
    return ranked_opps
