"""
Synthetic E-Commerce Data Generator & Database Seeder for GrowthPilot (§35 Demo Scenario)
Extended with Multi-Tenant Support: Tenant A (SoundWave Audio) and Tenant B (PulseWear Smart Gear).
"""
import os
import random
import uuid
import pandas as pd
from datetime import datetime, timedelta
from backend.app.db.models import init_db, get_db_connection, log_audit

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data")
CSV_PATH = os.path.join(DATA_DIR, "synthetic_ecommerce_dataset.csv")

TENANT_ALPHA = "tenant_store_alpha"
TENANT_BETA = "tenant_store_beta"


def seed_database(force: bool = False):
    """Seeds multi-tenant synthetic data for Tenant A and Tenant B."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM customers WHERE tenant_id = ?", (TENANT_ALPHA,))
    if cursor.fetchone()[0] > 0 and not force:
        print("Database already seeded. Skipping seed process.")
        conn.close()
        return

    if force:
        cursor.executescript("""
            DELETE FROM experiment_results;
            DELETE FROM executions;
            DELETE FROM campaign_interactions;
            DELETE FROM campaign_proposals;
            DELETE FROM opportunities;
            DELETE FROM insights;
            DELETE FROM cart_events;
            DELETE FROM sessions;
            DELETE FROM order_items;
            DELETE FROM products;
            DELETE FROM customers;
        """)

    print("Generating multi-tenant datasets for Tenant A (SoundWave) and Tenant B (PulseWear)...")
    random.seed(42)

    # 1. Seed Tenant A: SoundWave Audio (Audio Specialists)
    products_alpha = [
        {"product_id": "PROD-001", "tenant_id": TENANT_ALPHA, "name": "Wireless Earbuds Pro", "category": "Audio", "base_price": 2999.0, "margin_pct": 45.0, "inventory_count": 150, "inventory_urgency_factor": 1.0},
        {"product_id": "PROD-002", "tenant_id": TENANT_ALPHA, "name": "Earbud Case & Charging Stand", "category": "Audio", "base_price": 1200.0, "margin_pct": 50.0, "inventory_count": 450, "inventory_urgency_factor": 1.3},
        {"product_id": "PROD-003", "tenant_id": TENANT_ALPHA, "name": "Active Noise Canceling Headphones", "category": "Audio", "base_price": 4999.0, "margin_pct": 55.0, "inventory_count": 80, "inventory_urgency_factor": 0.9},
        {"product_id": "PROD-004", "tenant_id": TENANT_ALPHA, "name": "Bluetooth Speaker Mini", "category": "Audio", "base_price": 1499.0, "margin_pct": 35.0, "inventory_count": 200, "inventory_urgency_factor": 1.1},
        {"product_id": "PROD-005", "tenant_id": TENANT_ALPHA, "name": "Fast Wireless Charger Pad", "category": "Accessories", "base_price": 899.0, "margin_pct": 42.0, "inventory_count": 300, "inventory_urgency_factor": 1.2},
        {"product_id": "PROD-006", "tenant_id": TENANT_ALPHA, "name": "USB-C Braided Cable Pack", "category": "Accessories", "base_price": 499.0, "margin_pct": 25.0, "inventory_count": 500, "inventory_urgency_factor": 1.4},
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO products (product_id, tenant_id, name, category, base_price, margin_pct, inventory_count, inventory_urgency_factor, launch_date)
        VALUES (:product_id, :tenant_id, :name, :category, :base_price, :margin_pct, :inventory_count, :inventory_urgency_factor, '2025-01-01')
    """, products_alpha)

    # 2. Seed Tenant B: PulseWear Smart Gear (Wearables & Fitness)
    products_beta = [
        {"product_id": "PROD-B01", "tenant_id": TENANT_BETA, "name": "Pulse GPS Smartwatch Pro", "category": "Wearables", "base_price": 4499.0, "margin_pct": 35.0, "inventory_count": 120, "inventory_urgency_factor": 1.1},
        {"product_id": "PROD-B02", "tenant_id": TENANT_BETA, "name": "Active Fitness Band HR", "category": "Wearables", "base_price": 1799.0, "margin_pct": 30.0, "inventory_count": 90, "inventory_urgency_factor": 0.9},
        {"product_id": "PROD-B03", "tenant_id": TENANT_BETA, "name": "Heart Rate Chest Strap", "category": "Fitness Tech", "base_price": 1299.0, "margin_pct": 40.0, "inventory_count": 180, "inventory_urgency_factor": 1.2},
        {"product_id": "PROD-B04", "tenant_id": TENANT_BETA, "name": "Smart Water Bottle & Hydration Tracker", "category": "Smart Gear", "base_price": 999.0, "margin_pct": 45.0, "inventory_count": 250, "inventory_urgency_factor": 1.3},
    ]

    cursor.executemany("""
        INSERT OR REPLACE INTO products (product_id, tenant_id, name, category, base_price, margin_pct, inventory_count, inventory_urgency_factor, launch_date)
        VALUES (:product_id, :tenant_id, :name, :category, :base_price, :margin_pct, :inventory_count, :inventory_urgency_factor, '2025-01-01')
    """, products_beta)

    # 3. Generate Customers for Tenant A (SoundWave)
    customers_alpha = []
    earbud_buyers_18_25 = []
    start_date = datetime.now() - timedelta(days=180)

    for i in range(1, 4001):
        c_id = f"CUST-A{i:04d}"
        age = random.randint(18, 65)
        channel = random.choice(["Direct", "Google Search", "Instagram Ads", "Email Newsletter"])
        segment = "Young Adults (18-25)" if age <= 25 else ("Tech Enthusiasts (26-40)" if age <= 40 else "Value Seekers (41+)")
        signup_dt = start_date + timedelta(days=random.randint(0, 90))
        customers_alpha.append((c_id, TENANT_ALPHA, age, segment, channel, signup_dt.strftime("%Y-%m-%d")))

        if 18 <= age <= 25 and len(earbud_buyers_18_25) < 850:
            earbud_buyers_18_25.append(c_id)

    cursor.executemany("INSERT OR REPLACE INTO customers (customer_id, tenant_id, age, segment, channel, signup_date) VALUES (?, ?, ?, ?, ?, ?)", customers_alpha)

    # 4. Generate Customers for Tenant B (PulseWear)
    customers_beta = []
    for i in range(1, 2001):
        c_id = f"CUST-B{i:04d}"
        age = random.randint(22, 55)
        channel = random.choice(["Fitness Influencers", "Google Ads", "Strava Partner", "Direct"])
        segment = "Marathon Runners" if age <= 35 else "Fitness Enthusiasts"
        signup_dt = start_date + timedelta(days=random.randint(0, 90))
        customers_beta.append((c_id, TENANT_BETA, age, segment, channel, signup_dt.strftime("%Y-%m-%d")))

    cursor.executemany("INSERT OR REPLACE INTO customers (customer_id, tenant_id, age, segment, channel, signup_date) VALUES (?, ?, ?, ?, ?, ?)", customers_beta)

    # 5. Orders, Sessions, Carts for Tenant A
    order_items = []
    sessions = []
    cart_events = []
    order_count = 0
    session_count = 0

    for c_id in earbud_buyers_18_25:
        p_date = start_date + timedelta(days=random.randint(10, 100))
        order_count += 1
        item_id = f"ORD-A{order_count:05d}"
        order_items.append((item_id, TENANT_ALPHA, c_id, "PROD-001", p_date.strftime("%Y-%m-%d"), 1, 0.0, 2999.0))

        session_count += 1
        s_id = f"SESS-A{session_count:05d}"
        s_time = p_date + timedelta(days=random.randint(1, 40))
        sessions.append((s_id, TENANT_ALPHA, c_id, s_time.strftime("%Y-%m-%d %H:%M:%S"), "Instagram Ads"))

        cart_events.append((f"CART-A{len(cart_events)+1:05d}", TENANT_ALPHA, s_id, c_id, "PROD-002", "add_to_cart", s_time.strftime("%Y-%m-%d %H:%M:%S")))
        rand_val = random.random()
        if rand_val < 0.06:
            cart_events.append((f"CART-A{len(cart_events)+1:05d}", TENANT_ALPHA, s_id, c_id, "PROD-002", "checkout", (s_time + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M:%S")))
            order_count += 1
            order_items.append((f"ORD-A{order_count:05d}", TENANT_ALPHA, c_id, "PROD-002", s_time.strftime("%Y-%m-%d"), 1, 0.0, 1200.0))
        elif rand_val < 0.77:
            cart_events.append((f"CART-A{len(cart_events)+1:05d}", TENANT_ALPHA, s_id, c_id, "PROD-002", "abandon", (s_time + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S")))

    # 6. Orders, Sessions, Carts for Tenant B (PulseWear)
    all_b_ids = [c[0] for c in customers_beta]
    for c_id in all_b_ids:
        p_date = start_date + timedelta(days=random.randint(5, 120))
        order_count += 1
        order_items.append((f"ORD-B{order_count:05d}", TENANT_BETA, c_id, "PROD-B01", p_date.strftime("%Y-%m-%d"), 1, 0.0, 4499.0))
        session_count += 1
        s_id = f"SESS-B{session_count:05d}"
        sessions.append((s_id, TENANT_BETA, c_id, p_date.strftime("%Y-%m-%d %H:%M:%S"), "Strava Partner"))

    cursor.executemany("INSERT OR REPLACE INTO order_items (order_item_id, tenant_id, customer_id, product_id, purchase_date, quantity, discount_pct, revenue) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", order_items)
    cursor.executemany("INSERT OR REPLACE INTO sessions (session_id, tenant_id, customer_id, start_time, channel) VALUES (?, ?, ?, ?, ?)", sessions)
    cursor.executemany("INSERT OR REPLACE INTO cart_events (cart_event_id, tenant_id, session_id, customer_id, product_id, event_type, event_time) VALUES (?, ?, ?, ?, ?, ?, ?)", cart_events)

    conn.commit()
    conn.close()
    print("Multi-tenant dataset seeded successfully for SoundWave Audio (Tenant A) and PulseWear (Tenant B).")


if __name__ == "__main__":
    seed_database(force=True)
