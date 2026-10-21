"""
Airflow DAG (bonus): run the Olist ELT pipeline daily.

Each pipeline step is its own task, so the Airflow UI shows exactly which
step failed. A data-quality alarm raises DataQualityError, which fails the
task and stops every downstream task (staging and marts are not rebuilt on
bad data). Because every step is idempotent, a failed run can simply be
cleared and re-run.

Setup: put this repo on the Airflow worker and set OLIST_WBR_HOME to its
path (defaults to the parent folder of this file).
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG

try:  # Airflow 3.x
    from airflow.providers.standard.operators.python import PythonOperator
except ImportError:  # Airflow 2.x
    from airflow.operators.python import PythonOperator

PROJECT_HOME = Path(os.environ.get("OLIST_WBR_HOME",
                                   Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(PROJECT_HOME))

from pipeline import config  # noqa: E402
from pipeline import run_pipeline as p  # noqa: E402

DATA_DIR = Path(os.environ.get("OLIST_DATA_DIR", config.DEFAULT_DATA_DIR))
DB_PATH = Path(os.environ.get("OLIST_DB_PATH", config.DEFAULT_DB_PATH))


def _with_connection(step_fn, *args):
    """Open a DuckDB connection for one task and always close it."""
    import duckdb
    p.setup_logging()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DB_PATH))
    try:
        return step_fn(con, *args)
    finally:
        con.close()


def validate_inputs():
    _with_connection(p.validate_inputs, DATA_DIR)


def load_raw():
    _with_connection(p.load_raw, DATA_DIR)


def dq_gate(run_id: str):
    _with_connection(p.dq_gate, run_id)


def build_staging():
    _with_connection(p.build_staging)


def build_marts():
    _with_connection(p.build_marts)


def dq_post(run_id: str):
    _with_connection(p.dq_post, run_id)


default_args = {
    "owner": "data-team",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="olist_weekly_business_review_elt",
    description="Olist CSVs -> raw -> staging -> mart, with DQ alarms",
    start_date=datetime(2026, 10, 1),
    schedule="@daily",
    catchup=False,
    max_active_runs=1,          # DuckDB allows a single writer
    default_args=default_args,
    tags=["olist", "elt", "data-quality"],
) as dag:

    t_validate = PythonOperator(task_id="validate_inputs",
                                python_callable=validate_inputs)
    t_raw = PythonOperator(task_id="load_raw", python_callable=load_raw)
    t_gate = PythonOperator(task_id="dq_gate", python_callable=dq_gate,
                            op_kwargs={"run_id": "{{ run_id }}"})
    t_stg = PythonOperator(task_id="build_staging",
                           python_callable=build_staging)
    t_mart = PythonOperator(task_id="build_marts", python_callable=build_marts)
    t_post = PythonOperator(task_id="dq_post", python_callable=dq_post,
                            op_kwargs={"run_id": "{{ run_id }}"})

    t_validate >> t_raw >> t_gate >> t_stg >> t_mart >> t_post
