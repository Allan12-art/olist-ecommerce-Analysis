"""

──────────────────
Loads all Olist CSV files into a local DuckDB database.
Run this FIRST before any other script.

Usage:
    python src/01_setup_db.py
"""

import duckdb
import os
import sys

DB_PATH   = "ecommerce.duckdb"
DATA_DIR  = "data"

TABLES = {
    "orders":               "olist_orders_dataset.csv",
    "order_items":          "olist_order_items_dataset.csv",
    "order_payments":       "olist_order_payments_dataset.csv",
    "order_reviews":        "olist_order_reviews_dataset.csv",
    "customers":            "olist_customers_dataset.csv",
    "products":             "olist_products_dataset.csv",
    "sellers":              "olist_sellers_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "geolocation":          "olist_geolocation_dataset.csv",
}


def check_data_files():
    missing = []
    for table, filename in TABLES.items():
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            missing.append(path)
    if missing:
        print("❌ Missing data files:")
        for f in missing:
            print(f"   {f}")
        print("\n👉 Download from: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce")
        print("   Place all CSVs in the data/ folder then re-run this script.")
        sys.exit(1)
    print("✅ All data files found.")


def load_tables(con):
    for table, filename in TABLES.items():
        path = os.path.join(DATA_DIR, filename)
        print(f"   Loading {table}...", end=" ")
        con.execute(f"""
            CREATE OR REPLACE TABLE {table} AS
            SELECT * FROM read_csv_auto('{path}')
        """)
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{count:,} rows")


def verify_schema(con):
    print("\n📋 Table Summary:")
    print(f"{'Table':<25} {'Rows':>10} {'Columns':>10}")
    print("-" * 47)
    for table in TABLES:
        rows = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        cols = len(con.execute(f"DESCRIBE {table}").fetchall())
        print(f"{table:<25} {rows:>10,} {cols:>10}")


def run_sample_join(con):
    print("\n🔗 Sample join — Revenue by top 5 categories:")
    result = con.execute("""
        SELECT
            COALESCE(ct.product_category_name_english,
                     p.product_category_name, 'Unknown') AS category,
            COUNT(DISTINCT oi.order_id)                  AS orders,
            ROUND(SUM(oi.price), 2)                      AS revenue
        FROM order_items oi
        JOIN products p             ON oi.product_id = p.product_id
        JOIN orders o               ON oi.order_id   = o.order_id
        LEFT JOIN category_translation ct
                                    ON p.product_category_name = ct.product_category_name
        WHERE o.order_status = 'delivered'
        GROUP BY 1
        ORDER BY revenue DESC
        LIMIT 5
    """).fetchdf()
    print(result.to_string(index=False))


def main():
    print("=" * 50)
    print("  Olist E-Commerce — Database Setup")
    print("=" * 50)

    check_data_files()

    print(f"\n📦 Connecting to {DB_PATH}...")
    con = duckdb.connect(DB_PATH)

    print("⬆️  Loading tables:")
    load_tables(con)

    verify_schema(con)
    run_sample_join(con)

    con.close()
    print(f"\n✅ Database ready: {DB_PATH}")
    print("   Next step: python src/02_eda.py")


if __name__ == "__main__":
    main()