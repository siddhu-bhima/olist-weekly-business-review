# Olist Weekly Business Review - ELT pipeline, data quality and analysis

**Name:** B.Siddhu  |  **Reg No:** 127003037  |  **Course:** Big Data in Industry - Take-Home Assignment 1

A small, idempotent ELT pipeline over the [Olist Brazilian E-Commerce dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce):
raw CSVs → DuckDB `raw` → `staging` → `mart`, guarded by SQL data-quality checks that stop the run
(an "alarm") when they fail. It also contains the Part C SQL queries, the Part D metrics and charts, and a
script that builds the PDF report.

## Repository layout

```
olist-weekly-business-review/
├── pipeline/
│   ├── config.py            # file names, required columns, paths
│   └── run_pipeline.py      # the ELT pipeline (entry point)
├── sql/
│   ├── dq/                  # Part B: 8 data-quality checks on raw data (DQ01-DQ08)
│   ├── staging/             # raw -> staging (typed, de-duplicated, fixes applied)
│   ├── marts/               # staging -> mart.fct_orders, mart.fct_order_items
│   ├── dq_post/             # 3 checks on the finished mart (POST01-POST03)
│   ├── analysis/            # Part C: q1..q5 + x1 (back-test used in the memo)
│   └── metrics/             # Part D: weekly_metrics.sql (North Star + guardrails)
├── dags/olist_wbr_dag.py    # Bonus: Airflow DAG, @daily
├── report/
│   ├── make_charts.py       # Part D charts (matplotlib)
│   ├── build_report.py      # builds the PDF report
│   └── figures/
├── data/raw/                # put the Kaggle CSVs here (see data/raw/README.md)
├── requirements.txt
└── README.md
```

## How to run (step by step)

1. **Clone and install** (Python 3.10+):
   ```bash
   git clone https://github.com/siddhu-bhima/olist-weekly-business-review.git
   cd olist-weekly-business-review
   python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. **Get the data.** Download the dataset from Kaggle and unzip all 9 CSVs into `data/raw/`:
   ```bash
   kaggle datasets download -d olistbr/brazilian-ecommerce -p data/raw --unzip
   ```
   (or download the zip from the Kaggle page and unzip it there by hand).
3. **Run the pipeline:**
   ```bash
   python -m pipeline.run_pipeline
   # optional: --data-dir path/to/csvs --db path/to/olist.duckdb
   ```
   It creates `warehouse/olist.duckdb` and logs every step to the console and to `logs/pipeline.log`.
   Exit code is `0` on success and `1` on any failure.
4. **Run a Part C query** (any file in `sql/analysis/`), for example with the DuckDB CLI:
   ```bash
   duckdb warehouse/olist.duckdb < sql/analysis/q1_mom_revenue_growth.sql
   ```
   or from Python:
   ```bash
   python -c "import duckdb; c = duckdb.connect('warehouse/olist.duckdb', read_only=True); print(c.execute(open('sql/analysis/q4_repeat_purchase_rate.sql').read()).df())"
   ```
5. **Build the charts and the PDF report:**
   ```bash
   python -m report.make_charts
   python -m report.build_report      # -> report/BDA_Assignment1_B_Siddhu_127003037.pdf
   ```

### Bonus: Airflow

```bash
pip install "apache-airflow>=3.1"           # in its own virtualenv; Airflow 2.10 works on Python <= 3.12
export AIRFLOW__CORE__DAGS_FOLDER=$(pwd)/dags
airflow db migrate
airflow dags test olist_weekly_business_review_elt 2026-10-12   # one full run
airflow standalone                                                # UI + scheduler (@daily)
```
The DAG has six tasks (`validate_inputs → load_raw → dq_gate → build_staging → build_marts → dq_post`).
A data-quality alarm fails `dq_gate` or `dq_post`, and the downstream tasks do not run.
Optional environment variables: `OLIST_WBR_HOME`, `OLIST_DATA_DIR`, `OLIST_DB_PATH`.

## Design notes

**Idempotency.** Every table is rebuilt with `CREATE OR REPLACE` inside a transaction, so running the pipeline
twice gives identical tables. The only append-only table is the audit log `dq.check_history`, which has one
set of rows per `run_id`. `dq.latest_gate` and `dq.latest_post` always hold the most recent results.

**Failure handling.**

| Situation | What happens |
|---|---|
| A CSV is missing | `MissingFileError: Missing input file(s) in data/raw: olist_sellers_dataset.csv ...` |
| A required column is absent | `SchemaError: olist_order_items_dataset.csv is missing expected column(s): price. Found: ...` |
| A data-quality check fails | `DataQualityError: DATA QUALITY ALARM - DQ01 Null or duplicate order_id in orders: 2 failing of 99442 rows ...` |
| A SQL step errors | The transaction is rolled back; `PipelineError: SQL failed in 01_orders.sql: ...` |

**Data-quality checks.** Each file in `sql/dq/` returns `failing_rows, total_rows`, and its header sets
`max_fail_ratio` and documents the handling:

| ID | Check | Allowed | Handling |
|---|---|---|---|
| DQ01 | Null or duplicate `order_id` | 0 | hard stop |
| DQ02 | Delivered date before purchase date | 0 | hard stop |
| DQ03 | Carrier hand-over before purchase | 1% | fixed: set to NULL + flag |
| DQ04 | Payment total ≠ item price + freight | 1% | flagged, kept |
| DQ05 | Order without a customer | 0 | hard stop |
| DQ06 | *(own)* Status contradicts delivery date | 0.1% | flagged, excluded from delay metrics |
| DQ07 | *(own)* More than one review per order | 1% | fixed: keep latest answered review |
| DQ08 | *(own)* Orphan / zero-price order items | 0 | hard stop |

**Avoiding double counting.** Order items and payments are aggregated to order level in separate CTEs before
they are joined to orders. `mart.fct_orders` is therefore exactly one row per order, and check POST01 enforces
this on every run.

**Customer identity.** `customer_id` is new for every order; `customer_unique_id` identifies the person. The
repeat-purchase query (Q4) shows both, to make the difference visible.

**Revenue definition.** GMV = item `price + freight_value` for orders not `canceled` or `unavailable`, dated
by purchase timestamp. Money is cast to `DECIMAL(12,2)` (floats created false payment mismatches).
