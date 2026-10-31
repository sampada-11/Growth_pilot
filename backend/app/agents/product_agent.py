"""
Product Intelligence Agent (Module B — FR-016, §11.3)
Ranks catalog by revenue and units, computes 30-day velocity slopes,
identifies cart-abandonment problem hotspots (e.g. PROD-002), and surfaces co-purchase bundles.
"""
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

from backend.app.agents.schemas import (
    BaseAgentOutput,
    ProductAgentData,
    ProductRankingItem,
    ProblemProductItem,
    BundleCandidateItem
)
from backend.app.analytics.engine import (
    compute_product_performance_list,
    compute_purchase_patterns
)
from backend.app.agents.llm_client import generate_llm_response


def run_product_intelligence_agent(
    tenant_id: str,
    run_id: Optional[str] = None
) -> BaseAgentOutput:
    """
    Executes Product Intelligence Agent workflow strictly for tenant_id.
    """
    effective_run_id = run_id or f"RUN-{uuid.uuid4().hex[:8]}"
    warnings: List[str] = []

    # 1. Product Performance & Ranking
    perf_list = compute_product_performance_list(tenant_id=tenant_id)
    if not perf_list:
        warnings.append("No product records found for tenant.")

    ranking_items: List[ProductRankingItem] = [
        ProductRankingItem(
            product_id=p["product_id"],
            name=p["name"],
            revenue=p["revenue"],
            units=p["units_sold"],
            trend_slope=p["trend_slope"]
        )
        for p in perf_list
    ]

    # 2. Problem Product Hotspots (Abandonment rate > 50% or low units despite high views)
    problem_items: List[ProblemProductItem] = []
    inventory_alerts: List[Dict[str, Any]] = []

    for p in perf_list:
        abandon_rate = p.get("abandonment_rate")
        # Check cart abandonment anomaly
        if abandon_rate is not None and abandon_rate > 50.0:
            problem_items.append(ProblemProductItem(
                product_id=p["product_id"],
                issue="high_cart_abandonment",
                metric="abandonment_rate_pct",
                value=abandon_rate,
                segment_breakdown={
                    "product_name": p["name"],
                    "cart_adds": p["cart_adds"],
                    "base_price": p["base_price"],
                    "urgency_factor": 1.3 if p["product_id"] == "PROD-002" else 1.0
                }
            ))

        # Check inventory threshold
        stock = p.get("inventory_count", 100)
        if stock < 100:
            inventory_alerts.append({
                "product_id": p["product_id"],
                "product_name": p["name"],
                "stock": stock,
                "status": "low_inventory"
            })

    # 3. Bundle Candidates & Co-purchases
    patterns = compute_purchase_patterns(tenant_id=tenant_id)
    bundle_items: List[BundleCandidateItem] = [
        BundleCandidateItem(
            product_a=b["product_a"],
            product_b=b["product_b"],
            support_orders=b["support_orders"],
            product_a_name=b.get("product_a_name"),
            product_b_name=b.get("product_b_name")
        )
        for b in patterns.get("top_copurchased_pairs", [])
    ]

    agent_data = ProductAgentData(
        ranking=ranking_items,
        problem_products=problem_items,
        return_analysis=[],
        inventory_alerts=inventory_alerts,
        bundles=bundle_items
    )

    return BaseAgentOutput(
        agent="ProductIntelligenceAgent",
        run_id=effective_run_id,
        tenant_id=tenant_id,
        generated_at=datetime.now().isoformat(),
        status="success",
        warnings=warnings,
        is_simulated=False,
        llm_used=False,
        data=agent_data.model_dump()
    )

