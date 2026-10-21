"""
Pipeline configuration: where things live, which raw files we expect,
and the columns each file must contain.

If Olist ever changes a file layout, this is the only place to update.
"""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DEFAULT_DB_PATH = PROJECT_ROOT / "warehouse" / "olist.duckdb"
LOG_DIR = PROJECT_ROOT / "logs"
SQL_DIR = PROJECT_ROOT / "sql"

# raw table name -> (csv file name, required columns)
RAW_SOURCES = {
    "orders": (
        "olist_orders_dataset.csv",
        ["order_id", "customer_id", "order_status", "order_purchase_timestamp",
         "order_approved_at", "order_delivered_carrier_date",
         "order_delivered_customer_date", "order_estimated_delivery_date"],
    ),
    "order_items": (
        "olist_order_items_dataset.csv",
        ["order_id", "order_item_id", "product_id", "seller_id",
         "shipping_limit_date", "price", "freight_value"],
    ),
    "order_payments": (
        "olist_order_payments_dataset.csv",
        ["order_id", "payment_sequential", "payment_type",
         "payment_installments", "payment_value"],
    ),
    "order_reviews": (
        "olist_order_reviews_dataset.csv",
        ["review_id", "order_id", "review_score", "review_creation_date",
         "review_answer_timestamp"],
    ),
    "customers": (
        "olist_customers_dataset.csv",
        ["customer_id", "customer_unique_id", "customer_zip_code_prefix",
         "customer_city", "customer_state"],
    ),
    "sellers": (
        "olist_sellers_dataset.csv",
        ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    ),
    "products": (
        "olist_products_dataset.csv",
        ["product_id", "product_category_name"],
    ),
    "category_translation": (
        "product_category_name_translation.csv",
        ["product_category_name", "product_category_name_english"],
    ),
    "geolocation": (
        "olist_geolocation_dataset.csv",
        ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng",
         "geolocation_city", "geolocation_state"],
    ),
}

# Order in which SQL layers are built. Files inside each folder run in
# alphabetical order, so they are prefixed with numbers.
STAGING_DIR = SQL_DIR / "staging"
MARTS_DIR = SQL_DIR / "marts"
DQ_GATE_DIR = SQL_DIR / "dq"          # checks on raw data, before staging
DQ_POST_DIR = SQL_DIR / "dq_post"     # checks on the finished mart
ANALYSIS_DIR = SQL_DIR / "analysis"   # Part C queries
