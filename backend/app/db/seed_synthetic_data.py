"""
Synthetic E-Commerce Data Generator & Database Seeder for GrowthPilot (§35 Demo Scenario)
Extended with Multi-Tenant Support: Tenant A (SoundWave Audio) and Tenant B (PulseWear Smart Gear).
Fulfills Section A (Core Datasets):
- Customers: customer_id, age, location, registration_date
- Products: product_id, category, price, stock
- Orders: order_id, customer_id, order_date, total_amount, status
- Order Items: order_id, product_id, quantity, unit_price, revenue
- Sessions: session_id, customer_id, session_status
- Cart Events: customer_id, product_id, event_type, timestamp
- Campaigns: campaign_id, segment, discount, status
- Payments: payment_id, order_id, amount, status
"""
import os
import json
import random
import uuid
import pandas as pd
from datetime import datetime, timedelta
from backend.app.db.models import init_db, get_db_connection, log_audit

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
CSV_PATH = os.path.join(DATA_DIR, "synthetic_ecommerce_dataset.csv")

TENANT_ALPHA = "tenant_store_alpha"
TENANT_BETA = "tenant_store_beta"

LOCATIONS = ["Mumbai", "Bengaluru", "Delhi NCR", "Pune", "Hyderabad", "Chennai", "Kolkata", "Ahmedabad"]


def seed_database(force: bool = False):
    """Seeds multi-tenant synthetic data for Tenant A and Tenant B."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM orders WHERE tenant_id = ?", (TENANT_ALPHA,))
    orders_exist = cursor.fetchone()[0] > 0
    if orders_exist and not force:
        print("Database orders already seeded. Skipping seed process.")
        conn.close()
        return

    print("Generating comprehensive multi-tenant datasets for Tenant A (SoundWave) and Tenant B (PulseWear)...")
    random.seed(42)

    cursor.executescript("""
        DELETE FROM payments;
        DELETE FROM orders;
        DELETE FROM order_items;
        DELETE FROM cart_events;
        DELETE FROM sessions;
        DELETE FROM products;
        DELETE FROM customers;
        DELETE FROM campaigns;
        DELETE FROM opportunities;
        DELETE FROM opportunity_events;
    """)

    # 1. Seed Products for Tenant A: SoundWave Audio
    products_alpha = [
        {"product_id": "PROD-001", "tenant_id": TENANT_ALPHA, "name": "Wireless Earbuds Pro", "category": "Audio", "price": 2999.0, "stock": 150, "base_price": 2999.0, "margin_pct": 45.0, "inventory_count": 150, "inventory_urgency_factor": 1.0},
        {"product_id": "PROD-002", "tenant_id": TENANT_ALPHA, "name": "Earbud Case & Charging Stand", "category": "Audio Accessories", "price": 1200.0, "stock": 450, "base_price": 1200.0, "margin_pct": 50.0, "inventory_count": 450, "inventory_urgency_factor": 1.3},
        {"product_id": "PROD-003", "tenant_id": TENANT_ALPHA, "name": "Active Noise Canceling Headphones", "category": "Audio", "price": 4999.0, "stock": 80, "base_price": 4999.0, "margin_pct": 55.0, "inventory_count": 80, "inventory_urgency_factor": 0.9},
        {"product_id": "PROD-004", "tenant_id": TENANT_ALPHA, "name": "Bluetooth Speaker Mini", "category": "Audio", "price": 1499.0, "stock": 200, "base_price": 1499.0, "margin_pct": 35.0, "inventory_count": 200, "inventory_urgency_factor": 1.1},
        {"product_id": "PROD-005", "tenant_id": TENANT_ALPHA, "name": "Fast Wireless Charger Pad", "category": "Accessories", "price": 899.0, "stock": 300, "base_price": 899.0, "margin_pct": 42.0, "inventory_count": 300, "inventory_urgency_factor": 1.2},
        {"product_id": "PROD-006", "tenant_id": TENANT_ALPHA, "name": "USB-C Braided Cable Pack", "category": "Accessories", "price": 499.0, "stock": 500, "base_price": 499.0, "margin_pct": 25.0, "inventory_count": 500, "inventory_urgency_factor": 1.4},
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO products (product_id, tenant_id, name, category, price, stock, base_price, margin_pct, inventory_count, inventory_urgency_factor, launch_date)
        VALUES (:product_id, :tenant_id, :name, :category, :price, :stock, :base_price, :margin_pct, :inventory_count, :inventory_urgency_factor, '2025-01-01')
    """, products_alpha)

    # 2. Seed Products for Tenant B: PulseWear Smart Gear
    products_beta = [
        {"product_id": "PROD-B01", "tenant_id": TENANT_BETA, "name": "Pulse GPS Smartwatch Pro", "category": "Wearables", "price": 4499.0, "stock": 120, "base_price": 4499.0, "margin_pct": 35.0, "inventory_count": 120, "inventory_urgency_factor": 1.1},
        {"product_id": "PROD-B02", "tenant_id": TENANT_BETA, "name": "Active Fitness Band HR", "category": "Wearables", "price": 1799.0, "stock": 90, "base_price": 1799.0, "margin_pct": 30.0, "inventory_count": 90, "inventory_urgency_factor": 0.9},
        {"product_id": "PROD-B03", "tenant_id": TENANT_BETA, "name": "Heart Rate Chest Strap", "category": "Fitness Tech", "price": 1299.0, "stock": 180, "base_price": 1299.0, "margin_pct": 40.0, "inventory_count": 180, "inventory_urgency_factor": 1.2},
        {"product_id": "PROD-B04", "tenant_id": TENANT_BETA, "name": "Smart Water Bottle & Hydration Tracker", "category": "Smart Gear", "price": 999.0, "stock": 250, "base_price": 999.0, "margin_pct": 45.0, "inventory_count": 250, "inventory_urgency_factor": 1.3},
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO products (product_id, tenant_id, name, category, price, stock, base_price, margin_pct, inventory_count, inventory_urgency_factor, launch_date)
        VALUES (:product_id, :tenant_id, :name, :category, :price, :stock, :base_price, :margin_pct, :inventory_count, :inventory_urgency_factor, '2025-01-01')
    """, products_beta)

    # 3. Seed Customers for Tenant A (SoundWave)
    customers_alpha = []
    earbud_buyers_18_25 = []
    start_date = datetime.now() - timedelta(days=180)

    for i in range(1, 4001):
        c_id = f"CUST-A{i:04d}"
        age = random.randint(18, 65)
        location = random.choice(LOCATIONS)
        channel = random.choice(["Direct", "Google Search", "Instagram Ads", "Email Newsletter"])
        segment = "Young Adults (18-25)" if age <= 25 else ("Tech Enthusiasts (26-40)" if age <= 40 else "Value Seekers (41+)")
        signup_dt = start_date + timedelta(days=random.randint(0, 90))
        reg_date_str = signup_dt.strftime("%Y-%m-%d")
        customers_alpha.append((c_id, TENANT_ALPHA, age, location, reg_date_str, segment, channel, reg_date_str))

        if 18 <= age <= 25 and len(earbud_buyers_18_25) < 850:
            earbud_buyers_18_25.append(c_id)

    cursor.executemany("""
        INSERT OR REPLACE INTO customers (customer_id, tenant_id, age, location, registration_date, segment, channel, signup_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, customers_alpha)

    # 4. Seed Customers for Tenant B (PulseWear)
    customers_beta = []
    for i in range(1, 2001):
        c_id = f"CUST-B{i:04d}"
        age = random.randint(22, 55)
        location = random.choice(LOCATIONS)
        channel = random.choice(["Fitness Influencers", "Google Ads", "Strava Partner", "Direct"])
        segment = "Marathon Runners" if age <= 35 else "Fitness Enthusiasts"
        signup_dt = start_date + timedelta(days=random.randint(0, 90))
        reg_date_str = signup_dt.strftime("%Y-%m-%d")
        customers_beta.append((c_id, TENANT_BETA, age, location, reg_date_str, segment, channel, reg_date_str))

    cursor.executemany("""
        INSERT OR REPLACE INTO customers (customer_id, tenant_id, age, location, registration_date, segment, channel, signup_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, customers_beta)

    # 5. Orders, Order Items, Sessions, Carts, and Payments for Tenant A (SoundWave Audio)
    orders_rows = []
    order_items_rows = []
    sessions_rows = []
    cart_events_rows = []
    payments_rows = []

    order_idx = 0
    session_idx = 0

    # A. Primary purchases for 850 Young Adults (Earbuds Pro scenario)
    for c_id in earbud_buyers_18_25:
        p_date = start_date + timedelta(days=random.randint(10, 170))
        p_date_str = p_date.strftime("%Y-%m-%d")
        order_idx += 1
        ord_id = f"ORD-A{order_idx:05d}"
        item_id = f"ITEM-A{order_idx:05d}"
        
        # 94% completed, 4% refunded, 2% cancelled
        rand_status = random.random()
        if rand_status < 0.04:
            ord_status = "refunded"
        elif rand_status < 0.06:
            ord_status = "cancelled"
        else:
            ord_status = "completed"

        # Realistic item quantities and occasional accessory bundles
        qty = 2 if random.random() < 0.08 else 1
        amount = 2999.0 * qty
        orders_rows.append((ord_id, TENANT_ALPHA, c_id, p_date_str, amount, ord_status, p_date.isoformat()))
        order_items_rows.append((item_id, TENANT_ALPHA, ord_id, c_id, "PROD-001", p_date_str, qty, 2999.0, 0.0, amount))

        pay_id = f"PAY-A{order_idx:05d}"
        pay_status = "refunded" if ord_status == "refunded" else ("failed" if ord_status == "cancelled" else "captured")
        payments_rows.append((pay_id, TENANT_ALPHA, ord_id, f"pay_mock_a_{order_idx:05d}", amount, "INR", pay_status, 1, p_date.isoformat()))

        # Subsequent browsing session for Earbud Stand (PROD-002) - canonical 71% cart drop
        session_idx += 1
        if session_idx <= 668:
            s_id = f"SESS-A{session_idx:05d}"
            s_time = p_date + timedelta(days=random.randint(1, 40))
            s_time_str = s_time.strftime("%Y-%m-%d %H:%M:%S")
            sessions_rows.append((s_id, TENANT_ALPHA, c_id, s_time_str, "Instagram Ads", "completed"))

            # Cart created
            cart_id1 = f"CART-A{len(cart_events_rows)+1:05d}"
            cart_events_rows.append((cart_id1, TENANT_ALPHA, s_id, c_id, "PROD-002", "add_to_cart", s_time_str, s_time_str))

            rand_val = random.random()
            if rand_val < 0.06:
                # 6.0% conversion rate checkout
                cart_id2 = f"CART-A{len(cart_events_rows)+1:05d}"
                chk_time = (s_time + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
                cart_events_rows.append((cart_id2, TENANT_ALPHA, s_id, c_id, "PROD-002", "checkout", chk_time, chk_time))

                order_idx += 1
                ord_id2 = f"ORD-A{order_idx:05d}"
                item_id2 = f"ITEM-A{order_idx:05d}"
                orders_rows.append((ord_id2, TENANT_ALPHA, c_id, s_time.strftime("%Y-%m-%d"), 1200.0, "completed", s_time.isoformat()))
                order_items_rows.append((item_id2, TENANT_ALPHA, ord_id2, c_id, "PROD-002", s_time.strftime("%Y-%m-%d"), 1, 1200.0, 0.0, 1200.0))

                pay_id2 = f"PAY-A{order_idx:05d}"
                payments_rows.append((pay_id2, TENANT_ALPHA, ord_id2, f"pay_mock_a_{order_idx:05d}", 1200.0, "INR", "captured", 1, s_time.isoformat()))
            elif rand_val < 0.77:
                # 71% cart abandonment
                cart_id3 = f"CART-A{len(cart_events_rows)+1:05d}"
                ab_time = (s_time + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
                cart_events_rows.append((cart_id3, TENANT_ALPHA, s_id, c_id, "PROD-002", "abandon", ab_time, ab_time))

    # B. Additional natural diverse orders across other segments (Tech Enthusiasts, Value Seekers)
    other_alpha_customers = [c for c in customers_alpha if c[0] not in earbud_buyers_18_25]
    alpha_catalog = [
        {"pid": "PROD-003", "name": "Active Noise Canceling Headphones", "price": 4999.0},
        {"pid": "PROD-004", "name": "Bluetooth Speaker Mini", "price": 1499.0},
        {"pid": "PROD-005", "name": "Fast Wireless Charger Pad", "price": 899.0},
        {"pid": "PROD-006", "name": "USB-C Braided Cable Pack", "price": 499.0},
    ]

    # Select ~350 diverse buyers among remaining customers to generate authentic customer variance
    sampled_diverse_alpha = random.sample(other_alpha_customers, 350)
    for c_tuple in sampled_diverse_alpha:
        c_id = c_tuple[0]
        # Number of orders (1 to 4)
        num_orders = random.choices([1, 2, 3, 4], weights=[0.60, 0.25, 0.10, 0.05])[0]
        base_order_date = start_date + timedelta(days=random.randint(15, 120))

        for o_num in range(num_orders):
            curr_order_date = base_order_date + timedelta(days=o_num * random.randint(10, 35))
            if curr_order_date > datetime.now():
                curr_order_date = datetime.now() - timedelta(days=random.randint(1, 5))
            p_date_str = curr_order_date.strftime("%Y-%m-%d")

            chosen_prod = random.choice(alpha_catalog)
            qty = random.choices([1, 2, 3], weights=[0.80, 0.15, 0.05])[0]
            ord_amt = chosen_prod["price"] * qty

            order_idx += 1
            ord_id = f"ORD-A{order_idx:05d}"
            item_id = f"ITEM-A{order_idx:05d}"
            ord_status = "completed" if random.random() > 0.04 else "refunded"

            orders_rows.append((ord_id, TENANT_ALPHA, c_id, p_date_str, ord_amt, ord_status, curr_order_date.isoformat()))
            order_items_rows.append((item_id, TENANT_ALPHA, ord_id, c_id, chosen_prod["pid"], p_date_str, qty, chosen_prod["price"], 0.0, ord_amt))

            pay_id = f"PAY-A{order_idx:05d}"
            pay_status = "refunded" if ord_status == "refunded" else "captured"
            payments_rows.append((pay_id, TENANT_ALPHA, ord_id, f"pay_mock_a_{order_idx:05d}", ord_amt, "INR", pay_status, 1, curr_order_date.isoformat()))

    # 6. Orders, Order Items, Sessions, Carts, and Payments for Tenant B (PulseWear)
    all_b_ids = [c[0] for c in customers_beta]
    beta_catalog = [
        {"pid": "PROD-B01", "name": "Pulse GPS Smartwatch Pro", "price": 4499.0},
        {"pid": "PROD-B02", "name": "Active Fitness Band HR", "price": 1799.0},
        {"pid": "PROD-B03", "name": "Heart Rate Chest Strap", "price": 1299.0},
        {"pid": "PROD-B04", "name": "Smart Water Bottle & Hydration Tracker", "price": 999.0},
    ]

    for c_id in all_b_ids:
        # Give diverse products & repeat orders
        num_b_orders = random.choices([1, 2, 3], weights=[0.75, 0.20, 0.05])[0]
        base_b_date = start_date + timedelta(days=random.randint(5, 120))

        for b_o_idx in range(num_b_orders):
            curr_b_date = base_b_date + timedelta(days=b_o_idx * random.randint(12, 30))
            if curr_b_date > datetime.now():
                curr_b_date = datetime.now() - timedelta(days=random.randint(1, 4))
            p_date_str = curr_b_date.strftime("%Y-%m-%d")

            order_idx += 1
            ord_id = f"ORD-B{order_idx:05d}"
            item_id = f"ITEM-B{order_idx:05d}"

            rand_status = random.random()
            if rand_status < 0.04:
                ord_status = "refunded"
            elif rand_status < 0.06:
                ord_status = "cancelled"
            else:
                ord_status = "completed"

            # Primary order usually watch or band, repeats usually accessories/bottles
            if b_o_idx == 0:
                chosen_b = random.choices(beta_catalog, weights=[0.60, 0.25, 0.10, 0.05])[0]
            else:
                chosen_b = random.choices(beta_catalog, weights=[0.10, 0.20, 0.40, 0.30])[0]

            qty = 1 if random.random() < 0.90 else 2
            amount = chosen_b["price"] * qty

            orders_rows.append((ord_id, TENANT_BETA, c_id, p_date_str, amount, ord_status, curr_b_date.isoformat()))
            order_items_rows.append((item_id, TENANT_BETA, ord_id, c_id, chosen_b["pid"], p_date_str, qty, chosen_b["price"], 0.0, amount))

            pay_id = f"PAY-B{order_idx:05d}"
            pay_status = "refunded" if ord_status == "refunded" else ("failed" if ord_status == "cancelled" else "captured")
            payments_rows.append((pay_id, TENANT_BETA, ord_id, f"pay_mock_b_{order_idx:05d}", amount, "INR", pay_status, 1, curr_b_date.isoformat()))

        # Cart event for Heart Rate Chest Strap (PROD-B03)
        session_idx += 1
        s_id = f"SESS-B{session_idx:05d}"
        s_time_str = base_b_date.strftime("%Y-%m-%d %H:%M:%S")
        sessions_rows.append((s_id, TENANT_BETA, c_id, s_time_str, "Strava Partner", "completed"))

        cart_id1 = f"CART-B{len(cart_events_rows)+1:05d}"
        cart_events_rows.append((cart_id1, TENANT_BETA, s_id, c_id, "PROD-B03", "add_to_cart", s_time_str, s_time_str))

        rand_b = random.random()
        if rand_b < 0.04:
            # 4.0% checkout conversion
            cart_id2 = f"CART-B{len(cart_events_rows)+1:05d}"
            chk_time = (base_b_date + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")
            cart_events_rows.append((cart_id2, TENANT_BETA, s_id, c_id, "PROD-B03", "checkout", chk_time, chk_time))
        elif rand_b < 0.69:
            # 65% cart abandonment
            cart_id3 = f"CART-B{len(cart_events_rows)+1:05d}"
            ab_time = (base_b_date + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")
            cart_events_rows.append((cart_id3, TENANT_BETA, s_id, c_id, "PROD-B03", "abandon", ab_time, ab_time))

    # Insert Orders
    cursor.executemany("""
        INSERT OR REPLACE INTO orders (order_id, tenant_id, customer_id, order_date, total_amount, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, orders_rows)

    # Insert Order Items
    cursor.executemany("""
        INSERT OR REPLACE INTO order_items (order_item_id, tenant_id, order_id, customer_id, product_id, purchase_date, quantity, unit_price, discount_pct, revenue)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, order_items_rows)

    # Insert Sessions
    cursor.executemany("""
        INSERT OR REPLACE INTO sessions (session_id, tenant_id, customer_id, start_time, channel, session_status)
        VALUES (?, ?, ?, ?, ?, ?)
    """, sessions_rows)

    # Insert Cart Events
    cursor.executemany("""
        INSERT OR REPLACE INTO cart_events (cart_event_id, tenant_id, session_id, customer_id, product_id, event_type, event_time, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, cart_events_rows)

    # Insert Payments
    cursor.executemany("""
        INSERT OR REPLACE INTO payments (payment_id, tenant_id, order_id, provider_event_id, amount, currency, status, is_simulated, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, payments_rows)

    # 7. Seed Sample Campaigns (§A Campaigns Dataset)
    campaigns_rows = [
        ("CAMP-ALPHA-01", TENANT_ALPHA, "Young Adults (18-25)", "8%", "active", "recover_abandoned_carts", "Young Adults Earbud Stand Recovery", datetime.now().isoformat()),
        ("CAMP-ALPHA-02", TENANT_ALPHA, "Tech Enthusiasts (26-40)", "10%", "draft", "upgrade_headphones", "Audiophile Headphones Upgrade", datetime.now().isoformat()),
        ("CAMP-BETA-01", TENANT_BETA, "Marathon Runners", "12%", "active", "winback_inactive_runners", "Marathon Heart Sensor Win-Back", datetime.now().isoformat()),
        ("CAMP-BETA-02", TENANT_BETA, "Fitness Enthusiasts", "15%", "draft", "hydration_tracker_launch", "Hydration Tracker Bundle", datetime.now().isoformat()),
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO campaigns (campaign_id, tenant_id, segment, discount, status, objective, name, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, campaigns_rows)

    # 8. Seed Canonical Growth Opportunities & Lifecycle Events
    opps_rows = [
        (
            "OPP-tenant_store_alpha-001",
            TENANT_ALPHA,
            "INS-A-001",
            "High cart abandonment",
            "71% Cart Abandonment detected on Earbud Charging Stand (PROD-002) among Young Adults (18-25).",
            "High cart abandonment (71%) on Earbud Charging Stand among Young Adults aged 18-25.",
            json.dumps({
                "summary": "Derived from event analysis: Accessory price friction immediately following primary purchase",
                "narrative": "850 cart additions analyzed; 88% abandoned within 45s on checkout review page.",
                "hypotheses": [
                    {"text": "Accessory price friction immediately following primary purchase", "evidence_refs": ["cart_events.abandon", "products.PROD-002.abandonment_rate"], "strength": "high"}
                ]
            }),
            json.dumps({"count": 850, "segment": "18–25", "segment_id": "seg_young_adults_18_25", "definition": "18-25 Earbud buyers with abandoned cart"}),
            "PROD-002",
            json.dumps({"cart_abandonment_pct": 71.0, "baseline_conversion_pct": 6.0, "target_conversion_pct": 14.0, "base_price": 1200.0, "cogs": 600.0, "margin_pct": 50.0}),
            json.dumps({
                "type": "targeted_discount",
                "proposed_action": "Personalised 8% offer via Email & Push",
                "discount_pct": 8.0,
                "channels": ["email", "push"],
                "audience_size": 850,
                "duration_days": 7,
                "target_segment": "18–25"
            }),
            81600.0,
            81600.0,
            29376.0,
            0.78,
            1.25,
            79560.0,
            1,
            "medium",
            "pending",
            "not_started",
            "analysed",
            "Launch personalized 8% discount offer on Earbud Stand via Email & Push.",
            json.dumps({
                "decision": "REQUIRE_APPROVAL",
                "rules": [
                    {"rule_id": "GR-01", "name": "Margin Floor", "passed": True, "message": "Post-discount margin 42% exceeds 20% floor."},
                    {"rule_id": "GR-02", "name": "Discount Band", "passed": True, "message": "8% offer within 15% maximum band."},
                    {"rule_id": "GR-03", "name": "Batch Size", "passed": True, "message": "850 audience size within 5000 limit."},
                    {"rule_id": "GR-06", "name": "Budget Cap", "passed": True, "message": "₹11,424 discount cost within ₹50,000 threshold."}
                ]
            }),
            json.dumps({
                "formula": "Audience * DeltaConversion * Price",
                "audience_size": 850,
                "base_price": 1200.0,
                "baseline_conversion_pct": 6.0,
                "expected_conversion_pct": 14.0,
                "incremental_buyers": 68,
                "gross_revenue_lift": 81600.0,
                "margin_pct": 50.0,
                "discount_pct": 8.0,
                "discount_cost": 11424.0,
                "net_profit_lift": 29376.0
            }),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ),
        (
            "OPP-tenant_store_beta-001",
            TENANT_BETA,
            "INS-B-001",
            "VIP Inactivity Churn",
            "65% Inactivity Churn among Marathon Runners after Smartwatch purchase.",
            "65% Inactivity Churn among Marathon Runners after Smartwatch purchase.",
            json.dumps({
                "summary": "Derived from event analysis: Post-marathon training disengagement without heart sensor trigger",
                "hypotheses": [
                    {"text": "Lack of training sensor accessory integration leads to app and store drop-off.", "evidence_refs": ["customers.churn_risk", "products.PROD-B03.velocity"], "strength": "high"}
                ]
            }),
            json.dumps({"count": 420, "segment": "Marathon Runners", "segment_id": "seg_marathon_runners", "definition": "Marathon Runners inactive >90 days"}),
            "PROD-B03",
            json.dumps({"churn_risk_pct": 65.0, "baseline_conversion_pct": 4.0, "target_conversion_pct": 12.0, "base_price": 1299.0}),
            json.dumps({
                "type": "vip_winback",
                "proposed_action": "Personalised 12% offer on Heart Rate Chest Strap",
                "discount_pct": 12.0,
                "channels": ["email", "push"],
                "audience_size": 420,
                "duration_days": 10,
                "target_segment": "Marathon Runners"
            }),
            43646.4,
            43646.4,
            10911.6,
            0.74,
            1.20,
            38758.0,
            1,
            "medium",
            "pending",
            "not_started",
            "analysed",
            "Deploy VIP Win-Back offer with 12% off Heart Rate Chest Strap via Email & Push.",
            json.dumps({"decision": "REQUIRE_APPROVAL", "rules": []}),
            json.dumps({
                "formula": "Audience * DeltaConversion * Price",
                "audience_size": 420,
                "base_price": 1299.0,
                "baseline_conversion_pct": 4.0,
                "expected_conversion_pct": 12.0,
                "incremental_buyers": 34,
                "gross_revenue_lift": 43646.4
            }),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        )
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO opportunities (
            opportunity_id, tenant_id, insight_id, title, description, problem,
            root_cause, affected_customers, product_id, supporting_analytics, strategy,
            expected_impact, est_revenue_impact, est_profit_impact, confidence, urgency_factor,
            priority_score, priority_rank, risk_level, approval_status, execution_status,
            lifecycle_state, recommended_action, guardrail_result, impact_inputs,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, opps_rows)

    # Initial opportunity lifecycle events
    now_iso = datetime.now().isoformat()
    events_rows = [
        ("EVT-INIT-A01", "OPP-tenant_store_alpha-001", TENANT_ALPHA, "detected", "analysed", "system", "Cart telemetry scanned & root cause analyzed", now_iso),
        ("EVT-INIT-B01", "OPP-tenant_store_beta-001", TENANT_BETA, "detected", "analysed", "system", "Inactivity patterns detected & win-back strategy computed", now_iso),
    ]
    cursor.executemany("""
        INSERT OR REPLACE INTO opportunity_events (event_id, opportunity_id, tenant_id, from_state, to_state, actor_id, reason, occurred_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, events_rows)

    conn.commit()
    conn.close()
    print("Multi-tenant dataset successfully seeded with consistent IDs across all 8 core tables.")


if __name__ == "__main__":
    seed_database(force=True)
