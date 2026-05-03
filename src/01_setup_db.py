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
        print("Missing data files:")
        for f in missing:
            print(f"   {f}")
        print("\nDownload from: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce")
        print("   Place all CSVs in the data/ folder then re-run this script.")
        sys.exit(1)
    print("All data files found.")


def load_tables(con):
    for table, filename in TABLES.items():
        path = os.path.join(DATA_DIR, filename)
        print(f"   Loading {table}...", end=" ")
        con.execute(f"DROP TABLE IF EXISTS {table}")
        con.execute(f"CREATE TABLE {table} AS SELECT * FROM read_csv_auto('{path}')")
        print("Done")


def main():
    print("Setting up Olist database...")
    check_data_files()
    print("Loading tables into DuckDB...")
    con = duckdb.connect(DB_PATH)
    load_tables(con)
    con.close()
    print("Database setup complete!")


if __name__ == "__main__":
    main()