"""
src/03_rfm.py
─────────────
Recency, Frequency, Monetary (RFM) segmentation
+ K-Means clustering to group customers.

Usage:
    python src/03_rfm.py
"""

import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
import os
import warnings
warnings.filterwarnings("ignore")

DB_PATH = "ecommerce.duckdb"
OUT_DIR = "outputs"
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": "#0f1117", "axes.facecolor": "#0f1117",
    "axes.edgecolor": "#444",      "axes.labelcolor": "#ccc",
    "text.color": "#eee",          "xtick.color": "#aaa",
    "ytick.color": "#aaa",         "grid.color": "#333",
    "grid.linestyle": "--",        "grid.alpha": 0.5,
    "font.family": "monospace",
})
PALETTE = ["#00d4ff", "#7c3aed", "#10b981", "#f59e0b",
           "#ef4444", "#ec4899", "#84cc16", "#06b6d4"]


# ── Step 1: Pull raw RFM data via SQL ────────────────────────
def get_rfm_data(con) -> pd.DataFrame:
    print("  Fetching RFM data from DuckDB...")
    df = con.execute("""
        WITH reference_date AS (
            SELECT MAX(CAST(order_purchase_timestamp AS TIMESTAMP)) AS max_date
            FROM orders
        )
        SELECT
            o.customer_id,
            DATEDIFF('day',
                MAX(CAST(o.order_purchase_timestamp AS TIMESTAMP)),
                (SELECT max_date FROM reference_date))        AS recency,
            COUNT(DISTINCT o.order_id)                        AS frequency,
            ROUND(SUM(oi.price + oi.freight_value), 2)        AS monetary
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY o.customer_id
        HAVING monetary > 0
    """).fetchdf()
    print(f"  {len(df):,} customers fetched")
    return df


# Step 2: RFM Scoring (1–5 quintiles)
def score_rfm(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["r_score"] = pd.qcut(df["recency"],   q=5, labels=[5, 4, 3, 2, 1])  # lower=better
    df["f_score"] = pd.qcut(df["frequency"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5])
    df["m_score"] = pd.qcut(df["monetary"],  q=5, labels=[1, 2, 3, 4, 5])

    df["r_score"] = df["r_score"].astype(int)
    df["f_score"] = df["f_score"].astype(int)
    df["m_score"] = df["m_score"].astype(int)
    df["rfm_score"] = df["r_score"] + df["f_score"] + df["m_score"]

    # Segment labels
    def label(row):
        r, f, m = row["r_score"], row["f_score"], row["m_score"]
        if r >= 4 and f >= 4 and m >= 4: return "Champions"
        if r >= 3 and f >= 3 and m >= 3: return "Loyal Customers"
        if r >= 4 and f <= 2:            return "New Customers"
        if r >= 3 and m >= 3:            return "Potential Loyalists"
        if r <= 2 and f >= 3 and m >= 3: return "At Risk"
        if r <= 2 and f >= 4:            return "Can't Lose Them"
        if r <= 2 and f <= 2:            return "Lost"
        return "Needs Attention"

    df["segment"] = df.apply(label, axis=1)
    return df


# Step 3: K-Means Clustering
def cluster_customers(df: pd.DataFrame, n_clusters: int = 4) -> pd.DataFrame:
    features = ["recency", "frequency", "monetary"]
    X = df[features].copy()

    # Log-transform monetary and frequency (skewed)
    X["monetary"]  = np.log1p(X["monetary"])
    X["frequency"] = np.log1p(X["frequency"])

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Elbow method to pick k
    inertias, silhouettes = [], []
    k_range = range(2, 9)
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        km.fit(X_scaled)
        inertias.append(km.inertia_)
        silhouettes.append(silhouette_score(X_scaled, km.labels_))

    # Plot elbow
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    ax1.plot(list(k_range), inertias, "o-", color="#00d4ff", lw=2)
    ax1.set_title("Elbow Method")
    ax1.set_xlabel("Number of Clusters (k)")
    ax1.set_ylabel("Inertia")
    ax1.grid(True)

    ax2.plot(list(k_range), silhouettes, "o-", color="#10b981", lw=2)
    ax2.set_title("Silhouette Score")
    ax2.set_xlabel("Number of Clusters (k)")
    ax2.set_ylabel("Score")
    ax2.grid(True)

    plt.suptitle("Optimal Number of Clusters", fontsize=13)
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/06_elbow_silhouette.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {OUT_DIR}/06_elbow_silhouette.png")

    # Final model
    km_final = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    df["cluster"] = km_final.fit_predict(X_scaled)

    return df, X_scaled


# Step 4: PCA visualisation of clusters
def plot_clusters_pca(df: pd.DataFrame, X_scaled):
    pca = PCA(n_components=2)
    components = pca.fit_transform(X_scaled)

    fig, ax = plt.subplots(figsize=(10, 7))
    for i, cluster in enumerate(sorted(df["cluster"].unique())):
        mask = df["cluster"] == cluster
        ax.scatter(components[mask, 0], components[mask, 1],
                   s=12, alpha=0.5, color=PALETTE[i],
                   label=f"Cluster {cluster}")

    ax.set_title("K-Means Customer Clusters (PCA projection)", fontsize=13)
    ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)")
    ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)")
    ax.legend()
    ax.grid(True)

    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/07_clusters_pca.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {OUT_DIR}/07_clusters_pca.png")


# Step 5: RFM Segment Treemap-style bar chart 
def plot_rfm_segments(df: pd.DataFrame):
    seg = df.groupby("segment").agg(
        customers=("customer_id", "count"),
        avg_monetary=("monetary", "mean"),
        total_revenue=("monetary", "sum")
    ).reset_index().sort_values("total_revenue", ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Customer count
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(seg))]
    axes[0].barh(seg["segment"][::-1], seg["customers"][::-1], color=colors[::-1])
    axes[0].set_title("Customers per Segment")
    axes[0].set_xlabel("Customer Count")
    axes[0].grid(axis="x")

    # Revenue
    axes[1].barh(seg["segment"][::-1], seg["total_revenue"][::-1], color=colors[::-1])
    axes[1].set_title("Revenue per Segment")
    axes[1].set_xlabel("Total Revenue (BRL)")
    axes[1].grid(axis="x")
    axes[1].xaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"R${x/1e6:.1f}M"))

    plt.suptitle("RFM Customer Segmentation", fontsize=14)
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/08_rfm_segments.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {OUT_DIR}/08_rfm_segments.png")


# Step 6: Cluster profile summary
def plot_cluster_profiles(df: pd.DataFrame):
    profile = df.groupby("cluster").agg(
        count=("customer_id", "count"),
        avg_recency=("recency", "mean"),
        avg_frequency=("frequency", "mean"),
        avg_monetary=("monetary", "mean")
    ).reset_index()

    print("\n  Cluster Profiles:")
    print(profile.to_string(index=False))

    # Radar-style grouped bar
    metrics = ["avg_recency", "avg_frequency", "avg_monetary"]
    labels  = ["Avg Recency (days)", "Avg Frequency", "Avg Monetary (BRL)"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for ax, metric, label in zip(axes, metrics, labels):
        bars = ax.bar(
            [f"C{c}" for c in profile["cluster"]],
            profile[metric],
            color=[PALETTE[c % len(PALETTE)] for c in profile["cluster"]]
        )
        ax.set_title(label)
        ax.grid(axis="y")
        for bar, val in zip(bars, profile[metric]):
            ax.text(bar.get_x() + bar.get_width()/2,
                    bar.get_height() * 1.02,
                    f"{val:.1f}", ha="center", fontsize=9)

    plt.suptitle("Cluster Profile Comparison", fontsize=14)
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/09_cluster_profiles.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {OUT_DIR}/09_cluster_profiles.png")


# Step 7: Save RFM results back to DuckDB 
def save_rfm_to_db(df: pd.DataFrame, con):
    con.execute("CREATE OR REPLACE TABLE rfm_segments AS SELECT * FROM df")
    print("  rfm_segments table saved to DuckDB")


def main():
    print("=" * 50)
    print("  RFM Segmentation + K-Means Clustering")
    print("=" * 50)

    con = duckdb.connect(DB_PATH)

    print("\nStep 1: Compute RFM values")
    df = get_rfm_data(con)

    print("\nStep 2: Assign RFM scores & segments")
    df = score_rfm(df)

    print("\nStep 3: K-Means clustering")
    df, X_scaled = cluster_customers(df, n_clusters=4)

    print("\nStep 4: Generating visualisations")
    plot_clusters_pca(df, X_scaled)
    plot_rfm_segments(df)
    plot_cluster_profiles(df)

    print("\nStep 5: Saving results to database")
    save_rfm_to_db(df, con)

    con.close()
    print(f"\nRFM analysis complete. Charts in {OUT_DIR}/")
    print("   Next step: python src/04_forecasting.py")


if __name__ == "__main__":
    main()