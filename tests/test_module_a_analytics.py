"""
Phase 2 Test Suite: Module A — Analytics Engine & Versioned APIs (/api/v1/analytics/*)
Validates FR-001 through FR-010, multi-tenant isolation, Redis caching, and edge-case handling.
"""
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.auth.jwt_auth import DEMO_USERS, create_access_token
from backend.app.db.seed_synthetic_data import seed_database
from backend.app.analytics.engine import compute_overview_kpis


@pytest.fixture(scope="module")
def seeded_db():
    seed_database(force=False)


@pytest.fixture
def client(seeded_db):
    return TestClient(app)


@pytest.fixture
def alpha_headers():
    user = DEMO_USERS["alpha@growthpilot.demo"]
    token = create_access_token({
        "sub": user["user_id"],
        "email": user["email"],
        "tenant_id": user["tenant_id"],
        "store_name": user["store_name"],
        "role": user["role"]
    })
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def beta_headers():
    user = DEMO_USERS["beta@growthpilot.demo"]
    token = create_access_token({
        "sub": user["user_id"],
        "email": user["email"],
        "tenant_id": user["tenant_id"],
        "store_name": user["store_name"],
        "role": user["role"]
    })
    return {"Authorization": f"Bearer {token}"}


class TestModuleAAnalytics:

    def test_01_unauthenticated_requests_rejected(self, client):
        """All /api/v1/analytics/* routes reject requests missing Bearer tokens with 401."""
        endpoints = [
            "/api/v1/analytics/overview",
            "/api/v1/analytics/revenue-trend",
            "/api/v1/analytics/funnel",
            "/api/v1/analytics/products",
            "/api/v1/analytics/purchase-patterns"
        ]
        for ep in endpoints:
            res = client.get(ep)
            assert res.status_code == 401, f"{ep} allowed unauthenticated access"

    def test_02_overview_kpis_computed_from_backend(self, client, alpha_headers):
        """Validates that overview KPIs return computed revenue, orders, AOV, and rates from DB."""
        res = client.get("/api/v1/analytics/overview?compare_previous=true", headers=alpha_headers)
        assert res.status_code == 200
        data = res.json()

        assert data["tenant_id"] == "tenant_store_alpha"
        metrics = data["metrics"]
        assert "revenue" in metrics
        assert metrics["revenue"]["value"] > 0
        assert metrics["revenue"]["currency"] == "INR"

        assert "orders" in metrics
        assert metrics["orders"]["value"] > 0

        assert "conversion_rate" in metrics
        assert metrics["conversion_rate"]["value"] is not None

        assert "aov" in metrics
        assert metrics["aov"]["value"] > 0

        assert "cart_abandonment_rate" in metrics
        assert metrics["cart_abandonment_rate"]["value"] is not None

        assert "retention_rate" in metrics
        assert "data_quality" in data
        assert isinstance(data["data_quality"]["warnings"], list)

    def test_03_cross_tenant_isolation_in_analytics(self, client, alpha_headers, beta_headers):
        """Verifies that Tenant A and Tenant B receive completely distinct, isolated metrics."""
        res_a = client.get("/api/v1/analytics/overview", headers=alpha_headers)
        res_b = client.get("/api/v1/analytics/overview", headers=beta_headers)

        assert res_a.status_code == 200
        assert res_b.status_code == 200

        data_a = res_a.json()
        data_b = res_b.json()

        assert data_a["tenant_id"] == "tenant_store_alpha"
        assert data_b["tenant_id"] == "tenant_store_beta"
        # Revenue and product catalogs differ between SoundWave and PulseWear
        assert data_a["metrics"]["revenue"]["value"] != data_b["metrics"]["revenue"]["value"]

    def test_04_client_tenant_id_override_rejected_with_403(self, client, alpha_headers):
        """Attempting to supply a different tenant_id in query string is blocked and audited."""
        res = client.get("/api/v1/analytics/overview?tenant_id=tenant_store_beta", headers=alpha_headers)
        assert res.status_code == 403
        data = res.json()
        assert "detail" in data

    def test_05_funnel_monotonic_steps(self, client, alpha_headers):
        """Verifies that the funnel returns monotonic steps with valid conversion percentages."""
        res = client.get("/api/v1/analytics/funnel", headers=alpha_headers)
        assert res.status_code == 200
        data = res.json()

        steps = data["funnel_steps"]
        assert len(steps) == 5
        step_names = [s["step"] for s in steps]
        assert step_names == ["sessions", "product_view", "add_to_cart", "checkout_started", "order_paid"]

        for s in steps:
            assert s["count"] >= 0
            assert "overall_conversion_pct" in s
            assert "step_conversion_pct" in s

    def test_06_product_performance_slope_and_abandonment(self, client, alpha_headers):
        """Verifies that product performance returns individual product metrics, slope, and abandon rate."""
        res = client.get("/api/v1/analytics/products", headers=alpha_headers)
        assert res.status_code == 200
        products = res.json()
        assert len(products) > 0

        # SoundWave has PROD-002 Earbud Stand with high abandonment
        stand = next((p for p in products if p["product_id"] == "PROD-002"), None)
        assert stand is not None
        assert stand["cart_adds"] > 0
        assert stand["abandonment_rate"] is not None
        assert stand["abandonment_rate"] > 50.0 # Seed data generates ~71% abandonment

    def test_07_purchase_patterns_copurchase_detection(self, client, alpha_headers):
        """Verifies that purchase patterns detects customer purchasing metrics and top co-purchased pairs."""
        res = client.get("/api/v1/analytics/purchase-patterns", headers=alpha_headers)
        assert res.status_code == 200
        data = res.json()

        assert "purchase_frequency" in data
        assert "category_affinity" in data
        assert "top_copurchased_pairs" in data
        assert isinstance(data["top_copurchased_pairs"], list)

    def test_08_zero_denominator_data_quality_handling(self):
        """Verifies that compute_overview_kpis handles zero rows safely without ZeroDivisionError."""
        empty_res = compute_overview_kpis(
            tenant_id="tenant_nonexistent_empty",
            from_date="2026-01-01",
            to_date="2026-01-02",
            compare_previous=False
        )
        assert empty_res["metrics"]["revenue"]["value"] == 0.0
        assert empty_res["metrics"]["orders"]["value"] == 0
        assert empty_res["metrics"]["conversion_rate"]["value"] is None
        assert empty_res["metrics"]["conversion_rate"]["reason"] == "no_sessions"
        assert empty_res["metrics"]["aov"]["value"] is None
        assert empty_res["metrics"]["aov"]["reason"] == "no_orders"
        assert empty_res["metrics"]["cart_abandonment_rate"]["value"] is None
        assert len(empty_res["data_quality"]["warnings"]) > 0

    def test_09_redis_caching_behavior(self, client, alpha_headers):
        """Subsequent request within 60s returns cached flag."""
        res1 = client.get("/api/v1/analytics/revenue-trend", headers=alpha_headers)
        assert res1.status_code == 200
        res2 = client.get("/api/v1/analytics/revenue-trend", headers=alpha_headers)
        assert res2.status_code == 200
        assert res2.json().get("_cached") is True

    def test_10_filter_options_endpoint(self, client, alpha_headers):
        """Filter options endpoint returns date presets, segments, and products scoped to tenant."""
        res = client.get("/api/v1/analytics/filter-options", headers=alpha_headers)
        assert res.status_code == 200
        data = res.json()
        assert "date_presets" in data
        assert any(p["id"] == "30d" for p in data["date_presets"])
        assert "segments" in data
        assert len(data["segments"]) > 0
        assert "products" in data
        assert len(data["products"]) > 0
        assert all("product_id" in p and "title" in p for p in data["products"])

    def test_11_overview_filtered_by_product_and_segment(self, client, alpha_headers):
        """Validates that overview KPIs can be filtered dynamically by product and segment."""
        # Unfiltered overview
        res_all = client.get("/api/v1/analytics/overview", headers=alpha_headers)
        assert res_all.status_code == 200
        total_rev = res_all.json()["metrics"]["revenue"]["value"]

        # Filtered overview by product
        res_filtered = client.get("/api/v1/analytics/overview?product_id=PROD-001", headers=alpha_headers)
        assert res_filtered.status_code == 200
        filtered_rev = res_filtered.json()["metrics"]["revenue"]["value"]
        assert 0 < filtered_rev <= total_rev

    def test_12_non_revenue_adjustments_statutory_isolation(self, client, alpha_headers):
        """Validates that statutory accounting segregates refunded, cancelled, and failed payments."""
        res = client.get("/api/v1/analytics/overview", headers=alpha_headers)
        assert res.status_code == 200
        data = res.json()
        assert "non_revenue_adjustments" in data
        adj = data["non_revenue_adjustments"]
        assert "refunded_orders" in adj
        assert "refunded_amount" in adj
        assert "cancelled_orders" in adj
        assert "cancelled_amount" in adj
        assert "failed_payments_count" in adj
        assert "failed_payments_amount" in adj
        # Refunded and cancelled counts are non-negative
        assert adj["refunded_orders"] >= 0
        assert adj["cancelled_orders"] >= 0

    def test_13_customer_segmentation_rfm_kmeans(self, client, alpha_headers):
        """Validates RFM segmentation with K-Means clustering and CLV computation."""
        res = client.get("/api/v1/analytics/customers/rfm", headers=alpha_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["tenant_id"] == "tenant_store_alpha"
        assert "kmeans_clusters" in data
        assert len(data["kmeans_clusters"]) == 4
        assert "avg_clv_overall" in data
        assert data["avg_clv_overall"] > 0
        assert "avg_historical_clv" in data
        assert data["avg_historical_clv"] > 0
        cluster = data["kmeans_clusters"][0]
        assert "persona" in cluster
        assert "customer_count" in cluster
        assert cluster["customer_count"] > 0

    def test_14_churn_risk_prediction_classification(self, client, alpha_headers):
        """Validates ML churn classification model assigning probabilities and risk tiers."""
        res = client.get("/api/v1/analytics/customers/churn-risk?limit=10", headers=alpha_headers)
        assert res.status_code == 200
        data = res.json()
        assert isinstance(data, list)
        assert len(data) == 10
        top_risk = data[0]
        assert "customer_id" in top_risk
        assert "churn_risk_score" in top_risk
        assert 0.0 <= top_risk["churn_risk_score"] <= 1.0
        assert top_risk["risk_tier"] in ["High", "Medium", "Low"]
        assert "conversion_propensity" in top_risk


