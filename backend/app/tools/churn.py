"""
Churn Prediction Tool (§21 AI/ML Component & Feature B)
Multi-tenant aware.
Implements:
- Classification Model (LogisticRegression from sklearn)
- Churn Probability scoring (0.0 to 1.0)
- Risk tier categorization (High, Medium, Low)
- Completed revenue and verified session engagement features
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from backend.app.db.models import get_db_connection


def compute_churn_risk_list(tenant_id: str = "tenant_store_alpha", limit: int = 50) -> List[Dict[str, Any]]:
    """
    Computes churn probability score using a classification model scoped to tenant_id.
    """
    conn = get_db_connection()
    
    query = """
        SELECT 
            c.customer_id,
            c.age,
            c.location,
            c.segment,
            c.channel,
            COUNT(DISTINCT CASE WHEN ord.status = 'completed' THEN ord.order_id ELSE NULL END) AS total_orders,
            COALESCE(SUM(CASE WHEN ord.status = 'completed' THEN ord.total_amount ELSE 0 END), 0) AS total_spent,
            MAX(CASE WHEN ord.status = 'completed' THEN ord.order_date ELSE NULL END) AS last_order_date,
            COUNT(DISTINCT s.session_id) AS total_sessions,
            MAX(s.start_time) AS last_session_date
        FROM customers c
        LEFT JOIN orders ord ON c.customer_id = ord.customer_id AND ord.tenant_id = c.tenant_id
        LEFT JOIN sessions s ON c.customer_id = s.customer_id AND s.tenant_id = c.tenant_id
        WHERE c.tenant_id = ?
        GROUP BY c.customer_id
    """
    df = pd.read_sql_query(query, conn, params=(tenant_id,))
    conn.close()

    if df.empty:
        return []

    now = datetime.now()
    max_order_dt = pd.to_datetime(df["last_order_date"]).max() if not df["last_order_date"].isna().all() else pd.to_datetime("now")
    df["last_order_dt"] = pd.to_datetime(df["last_order_date"])
    df["last_session_dt"] = pd.to_datetime(df["last_session_date"])

    df["days_since_order"] = (max_order_dt - df["last_order_dt"]).dt.days.fillna(180)
    df["days_since_session"] = (max_order_dt - df["last_session_dt"]).dt.days.fillna(180)

    # -------------------------------------------------------------
    # Classification Model for Churn Probability
    # -------------------------------------------------------------
    feature_cols = ["days_since_order", "days_since_session", "total_orders", "total_spent", "total_sessions"]
    X = df[feature_cols].copy()
    
    # Ground-truth heuristic label for training: inactive > 90 days or zero repeat orders
    y = ((df["days_since_order"] > 90) | (df["days_since_session"] > 75)).astype(int)

    if len(np.unique(y)) > 1 and len(df) >= 10:
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        clf = LogisticRegression(class_weight="balanced", random_state=42, max_iter=200)
        clf.fit(X_scaled, y)
        probs = clf.predict_proba(X_scaled)[:, 1]
    else:
        # Logistic sigmoid fallback
        z = (df["days_since_order"] / 60.0) + (df["days_since_session"] / 45.0) - (df["total_orders"] * 0.5)
        probs = 1.0 / (1.0 + np.exp(-np.clip(z - 2.0, -10, 10)))

    df["churn_risk_score"] = np.round(np.clip(probs, 0.01, 0.99), 3)
    df["conversion_propensity"] = np.round(1.0 - df["churn_risk_score"], 3)

    high_risk_df = df.sort_values(by="churn_risk_score", ascending=False).head(limit)

    results = []
    for _, row in high_risk_df.iterrows():
        score = float(row["churn_risk_score"])
        risk_tier = "High" if score >= 0.70 else ("Medium" if score >= 0.40 else "Low")
        results.append({
            "customer_id": str(row["customer_id"]),
            "age": int(row["age"]),
            "location": str(row.get("location") or "N/A"),
            "segment": str(row["segment"]),
            "channel": str(row["channel"]),
            "total_orders": int(row["total_orders"]),
            "total_spent": round(float(row["total_spent"]), 2),
            "days_since_last_order": int(row["days_since_order"]),
            "churn_risk_score": score,
            "risk_tier": risk_tier,
            "conversion_propensity": float(row["conversion_propensity"])
        })

    return results
