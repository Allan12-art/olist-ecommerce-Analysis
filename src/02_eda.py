"""
src/02_eda.py
─────────────
Exploratory Data Analysis

Usage:
    python src/02_eda.py
"""

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import os

DB_PATH  = "ecommerce.duckdb"
OUT_DIR  = "outputs"
os.makedirs(OUT_DIR, exist_ok=True)

# Styling 
plt.rcParams.update({
    "figure.facecolor": "#0f1117",
    "axes.facecolor":   "#0f1117",
    "axes.edgecolor":   "#444",
    "axes.labelcolor":  "#ccc",
    "text.color":       "#eee",
    "xtick.color":      "#aaa",
    "ytick.color":      "#aaa",
    "grid.color":       "#333",
    "grid.linestyle":   "--",
    "grid.alpha":       0.5,
    "font.family":      "monospace",
})
PALETTE = ["#00d4ff", "#7c3aed", "#10b981", "#f59e0b",
           "#ef4444", "#ec4899", "#84cc16", "#06b6d4"]


def get_con():
    return duckdb.connect(DB_PATH)


#  Monthly Revenue Trend 
def plot_monthly_revenue(con):
    df = con.execute("""
        SELECT
            DATE_TRUNC('month', CAST(order_purchase_timestamp AS TIMESTAMP)) AS month,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue,
            COUNT(DISTINCT o.order_id)                  AS orders
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY 1 ORDER BY 1
    """).fetchdf()

    df["month"] = pd.to_datetime(df["month"])

    fig, ax1 = plt.subplots(figsize=(14, 5))
    ax2 = ax1.twinx()

    ax1.fill_between(df["month"], df["revenue"], alpha=0.3, color="#00d4ff")
    ax1.plot(df["month"], df["revenue"], color="#00d4ff", lw=2.5, label="Revenue")
    ax2.bar(df["month"], df["orders"], width=20, alpha=0.4,
            color="#7c3aed", label="Orders")

    ax1.set_ylabel("Revenue (BRL)", color="#00d4ff")
    ax2.set_ylabel("# Orders", color="#7c3aed")
    ax1.set_title("Monthly Revenue & Order Volume", fontsize=14, pad=15)
    ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x:,.0f}"))

    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")
    ax1.grid(True)

    plt.tight_layout()
    path = f"{OUT_DIR}/01_monthly_revenue.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Saved: {path}")
    plt.close()


# Top Categories 
def plot_top_categories(con):
    df = con.execute("""
        SELECT
            COALESCE(ct.product_category_name_english,
                     p.product_category_name, 'Unknown') AS category,
            ROUND(SUM(oi.price), 2) AS revenue
        FROM order_items oi
        JOIN products p  ON oi.product_id = p.product_id
        JOIN orders o    ON oi.order_id   = o.order_id
        LEFT JOIN category_translation ct
                         ON p.product_category_name = ct.product_category_name
        WHERE o.order_status = 'delivered'
        GROUP BY 1 ORDER BY revenue DESC LIMIT 15
    """).fetchdf()

    fig, ax = plt.subplots(figsize=(10, 7))
    colors = [PALETTE[i % len(PALETTE)] for i in range(len(df))]
    bars = ax.barh(df["category"][::-1], df["revenue"][::-1], color=colors[::-1])
    ax.set_xlabel("Revenue (BRL)")
    ax.set_title("Top 15 Product Categories by Revenue", fontsize=14, pad=15)
    ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x/1e6:.1f}M"))
    ax.grid(axis="x")

    plt.tight_layout()
    path = f"{OUT_DIR}/02_top_categories.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Saved: {path}")
    plt.close()


# Revenue by State (heatmap-style bar) 
def plot_revenue_by_state(con):
    df = con.execute("""
        SELECT
            c.customer_state AS state,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue
        FROM orders o
        JOIN order_items oi ON o.order_id    = oi.order_id
        JOIN customers c    ON o.customer_id = c.customer_id
        WHERE o.order_status = 'delivered'
        GROUP BY 1 ORDER BY revenue DESC
    """).fetchdf()

    fig, ax = plt.subplots(figsize=(14, 5))
    norm = plt.Normalize(df["revenue"].min(), df["revenue"].max())
    cmap = plt.cm.plasma
    colors = [cmap(norm(v)) for v in df["revenue"]]

    ax.bar(df["state"], df["revenue"], color=colors)
    ax.set_xlabel("State")
    ax.set_ylabel("Revenue (BRL)")
    ax.set_title("Revenue by Brazilian State", fontsize=14, pad=15)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x/1e6:.1f}M"))
    ax.grid(axis="y")

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    plt.colorbar(sm, ax=ax, label="Revenue")

    plt.tight_layout()
    path = f"{OUT_DIR}/03_revenue_by_state.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Saved: {path}")
    plt.close()


# Day of Week Order Heatmap
def plot_orders_by_hour_dow(con):
    df = con.execute("""
        SELECT
            DAYOFWEEK(CAST(order_purchase_timestamp AS TIMESTAMP)) AS dow,
            EXTRACT(HOUR FROM CAST(order_purchase_timestamp AS TIMESTAMP)) AS hour,
            COUNT(*) AS orders
        FROM orders
        GROUP BY 1, 2
    """).fetchdf()

    pivot = df.pivot(index="dow", columns="hour", values="orders").fillna(0)
    dow_labels = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    pivot.index = [dow_labels[i] for i in pivot.index]

    fig, ax = plt.subplots(figsize=(16, 4))
    sns.heatmap(pivot, ax=ax, cmap="YlOrRd",
                linewidths=0.5, linecolor="#222",
                cbar_kws={"label": "# Orders"})
    ax.set_title("Order Volume by Day & Hour", fontsize=14, pad=15)
    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("")

    plt.tight_layout()
    path = f"{OUT_DIR}/04_heatmap_orders.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Saved: {path}")
    plt.close()


#  Review Score Distribution
def plot_review_scores(con):
    df = con.execute("""
        SELECT review_score, COUNT(*) AS count
        FROM order_reviews
        GROUP BY review_score ORDER BY review_score
    """).fetchdf()

    fig, ax = plt.subplots(figsize=(7, 4))
    score_colors = ["#ef4444", "#f97316", "#f59e0b", "#84cc16", "#10b981"]
    bars = ax.bar(df["review_score"].astype(str), df["count"],
                  color=score_colors, edgecolor="#000", linewidth=0.5)
    for bar, count in zip(bars, df["count"]):
        ax.text(bar.get_x() + bar.get_width()/2,
                bar.get_height() + 200,
                f"{count:,}", ha="center", fontsize=9)

    ax.set_xlabel("Review Score")
    ax.set_ylabel("Number of Reviews")
    ax.set_title("Review Score Distribution", fontsize=14, pad=15)
    ax.grid(axis="y")

    plt.tight_layout()
    path = f"{OUT_DIR}/05_review_scores.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    print(f"  Saved: {path}")
    plt.close()


# Print Summary KPIs
def print_kpis(con):
    row = con.execute("""
        SELECT
            COUNT(DISTINCT o.order_id)                AS orders,
            COUNT(DISTINCT o.customer_id)             AS customers,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue,
            ROUND(AVG(oi.price + oi.freight_value), 2) AS aov
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
    """).fetchone()

    print("\n" + "=" * 40)
    print("  KEY BUSINESS METRICS")
    print("=" * 40)
    print(f"  Total Orders    : {row[0]:>10,}")
    print(f"  Total Customers : {row[1]:>10,}")
    print(f"  Total Revenue   : R${row[2]:>12,.2f}")
    print(f"  Avg Order Value : R${row[3]:>12,.2f}")
    print("=" * 40 + "\n")


def main():
    print("=" * 50)
    print("  EDA — Exploratory Data Analysis")
    print("=" * 50)

    con = get_con()
    print_kpis(con)

    print("Generating charts:")
    plot_monthly_revenue(con)
    plot_top_categories(con)
    plot_revenue_by_state(con)
    plot_orders_by_hour_dow(con)
    plot_review_scores(con)

    con.close()
    print(f"\nAll charts saved to {OUT_DIR}/")
    print("   Next step: python src/03_rfm.py")


if __name__ == "__main__":
    main()