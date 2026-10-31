"""
RFM Customer Segmentation & CLV Estimation Tool (§21 AI/ML Component & Feature B)
Multi-tenant aware.
Implements:
- RFM (Recency, Frequency, Monetary) Analysis
- K-Means Unsupervised Clustering (sklearn) for customer grouping
- Historical and Predictive Customer Lifetime Value (CLV)
- Separation of refunded/cancelled orders from completed revenue
"""
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime
from typing import List, Dict, Any
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from backend.app.db.models import get_db_connection


def compute_customer_segmentation(tenant_id: str = "tenant_store_alpha") -> Dict[str, Any]:
    """
    Computes RFM scores, K-Means clustering customer groups, and CLV metrics scoped to tenant_id.
    """
    conn = get_db_connection()
    
    query = """
        SELECT 
            c.customer_id,
            c.age,
            c.location,
            c.segment AS raw_segment,
            c.channel,
            COUNT(CASE WHEN ord.status = 'completed' THEN ord.order_id ELSE NULL END) AS frequency,
            COALESCE(SUM(CASE WHEN ord.status = 'completed' THEN ord.total_amount ELSE 0 END), 0) AS total_monetary,
            COALESCE(AVG(CASE WHEN ord.status = 'completed' THEN ord.total_amount ELSE NULL END), 0) AS avg_order_value,
            MAX(CASE WHEN ord.status = 'completed' THEN ord.order_date ELSE NULL END) AS last_purchase_date
        FROM customers c
        LEFT JOIN orders ord ON c.customer_id = ord.customer_id AND ord.tenant_id = c.tenant_id
        WHERE c.tenant_id = ?
        GROUP BY c.customer_id
    """
    df = pd.read_sql_query(query, conn, params=(tenant_id,))
    conn.close()

    if df.empty:
        return {
            "segments": [],
            "kmeans_clusters": [],
            "total_customers": 0,
            "avg_clv_overall": 0.0,
            "avg_historical_clv": 0.0
        }

    now = datetime.now()
    df["last_purchase_date"] = pd.to_datetime(df["last_purchase_date"])
    max_date = df["last_purchase_date"].max() if not df["last_purchase_date"].isna().all() else now
    df["recency_days"] = (max_date - df["last_purchase_date"]).dt.days.fillna(180)

    # Historical & Predictive CLV
    df["historical_clv"] = df["total_monetary"].round(2)
    df["predicted_annual_freq"] = np.clip(df["frequency"] * 2.0, 1.0, 24.0)
    df["clv_estimate"] = (df["avg_order_value"] * df["predicted_annual_freq"]).round(2)

    # -------------------------------------------------------------
    # K-Means Clustering on RFM features
    # -------------------------------------------------------------
    rfm_features = df[["recency_days", "frequency", "total_monetary"]].copy()
    scaler = StandardScaler()
    scaled_rfm = scaler.fit_transform(rfm_features)

    n_clusters = min(4, len(df))
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster"] = kmeans.fit_predict(scaled_rfm)

    # Derive cluster personas from centroids
    cluster_centers = df.groupby("cluster").agg(
        avg_recency=("recency_days", "mean"),
        avg_freq=("frequency", "mean"),
        avg_mon=("total_monetary", "mean"),
        cust_count=("customer_id", "count")
    ).reset_index()

    def label_cluster(row):
        if row["avg_mon"] > cluster_centers["avg_mon"].median() and row["avg_recency"] <= cluster_centers["avg_recency"].median():
            return "Champions / High Value"
        elif row["avg_freq"] >= cluster_centers["avg_freq"].median():
            return "Loyal Customers"
        elif row["avg_recency"] > cluster_centers["avg_recency"].median():
            return "At Risk / Inactive"
        else:
            return "Recent / Potential Loyalists"

    cluster_centers["persona"] = cluster_centers.apply(label_cluster, axis=1)
    persona_map = dict(zip(cluster_centers["cluster"], cluster_centers["persona"]))
    df["kmeans_segment"] = df["cluster"].map(persona_map)

    # -------------------------------------------------------------
    # Aggregated Segment Results (Both demographic segment & K-Means)
    # -------------------------------------------------------------
    segment_counts = df.groupby("raw_segment").agg(
        customer_count=("customer_id", "count"),
        avg_clv=("clv_estimate", "mean"),
        avg_historical_clv=("historical_clv", "mean"),
        avg_recency=("recency_days", "mean"),
        avg_monetary=("total_monetary", "mean"),
        total_revenue=("total_monetary", "sum")
    ).reset_index()

    segment_list = []
    for _, row in segment_counts.iterrows():
        segment_list.append({
            "segment_name": str(row["raw_segment"]),
            "customer_count": int(row["customer_count"]),
            "avg_clv": round(float(row["avg_clv"]), 2),
            "avg_historical_clv": round(float(row["avg_historical_clv"]), 2),
            "avg_recency_days": round(float(row["avg_recency"]), 1),
            "avg_monetary": round(float(row["avg_monetary"]), 2),
            "total_revenue": round(float(row["total_revenue"]), 2)
        })

    kmeans_groups = []
    for _, row in cluster_centers.iterrows():
        kmeans_groups.append({
            "cluster_id": int(row["cluster"]),
            "persona": str(row["persona"]),
            "customer_count": int(row["cust_count"]),
            "avg_recency_days": round(float(row["avg_recency"]), 1),
            "avg_frequency": round(float(row["avg_freq"]), 2),
            "avg_monetary": round(float(row["avg_mon"]), 2)
        })

    return {
        "tenant_id": tenant_id,
        "segments": segment_list,
        "kmeans_clusters": kmeans_groups,
        "total_customers": len(df),
        "avg_clv_overall": round(float(df["clv_estimate"].mean()), 2),
        "avg_historical_clv": round(float(df["historical_clv"].mean()), 2)
    }
