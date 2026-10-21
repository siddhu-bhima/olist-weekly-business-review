"""
Olist Weekly Business Review - ELT pipeline.

Layers (all inside one DuckDB file):
    raw.*      CSVs loaded as-is (plus load metadata)
    staging.*  typed, de-duplicated, cleaned tables
    mart.*     analysis-ready tables (mart.fct_orders = one row per order)
    dq.*       data-quality results (latest run + history)

Steps:
    1. validate_inputs   every file exists and has its required columns
    2. load_raw          CSV -> raw.*            (CREATE OR REPLACE)
    3. dq_gate           SQL checks on raw data   (alarm if over threshold)
    4. build_staging     raw -> staging.*        (CREATE OR REPLACE)
    5. build_marts       staging -> mart.*       (CREATE OR REPLACE)
    6. dq_post           SQL checks on the mart   (alarm on any failure)

Idempotency: every table is rebuilt with CREATE OR REPLACE inside a
transaction, so running the pipeline any number of times gives the same
tables and the same row counts. Nothing is ever appended except the
dq.check_history audit log, which is keyed by run_id.

Usage:
    python -m pipeline.run_pipeline
    python -m pipeline.run_pipeline --data-dir data/raw --db warehouse/olist.duckdb
"""
from __future__ import annotations

import argparse
import logging
import re
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import duckdb

from pipeline import config

log = logging.getLogger("olist_pipeline")


# --------------------------------------------------------------------------
# Errors: each failure type has its own class so the message says what broke
# --------------------------------------------------------------------------
class PipelineError(Exception):
    """Base class for pipeline failures."""


class MissingFileError(PipelineError):
    pass


class SchemaError(PipelineError):
    pass


class DataQualityError(PipelineError):
    """Raised when a data-quality check fails (the 'alarm')."""


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def setup_logging(log_dir: Path = config.LOG_DIR) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    fmt = logging.Formatter("%(asctime)s | %(levelname)-7s | %(message)s",
                            "%Y-%m-%d %H:%M:%S")
    root = logging.getLogger("olist_pipeline")
    root.setLevel(logging.INFO)
    root.handlers.clear()
    for handler in (logging.StreamHandler(sys.stdout),
                    logging.FileHandler(log_dir / "pipeline.log")):
        handler.setFormatter(fmt)
        root.addHandler(handler)


def sql_files(folder: Path) -> list[Path]:
    files = sorted(folder.glob("*.sql"))
    if not files:
        raise PipelineError(f"No .sql files found in {folder}")
    return files


def run_sql_file(con: duckdb.DuckDBPyConnection, path: Path) -> None:
    """Run every statement in a .sql file inside one transaction."""
    sql = path.read_text()
    con.execute("BEGIN TRANSACTION")
    try:
        con.execute(sql)
        con.execute("COMMIT")
    except Exception as exc:
        con.execute("ROLLBACK")
        raise PipelineError(f"SQL failed in {path.name}: {exc}") from exc


def parse_header(sql: str) -> dict[str, str]:
    """Read '-- key: value' metadata lines at the top of a check file."""
    meta = {}
    for line in sql.splitlines():
        m = re.match(r"--\s*(\w+)\s*:\s*(.+)", line)
        if m:
            meta[m.group(1).lower()] = m.group(2).strip()
        elif line.strip() and not line.strip().startswith("--"):
            break
    return meta


def step(name: str):
    """Decorator: log start, end, duration and failures of each step."""
    def wrap(fn):
        def inner(*args, **kwargs):
            log.info("START  %s", name)
            t0 = time.perf_counter()
            try:
                out = fn(*args, **kwargs)
            except PipelineError as exc:
                log.error("FAILED %s -> %s", name, exc)
                raise
            log.info("DONE   %s (%.1fs)", name, time.perf_counter() - t0)
            return out
        inner.__name__ = fn.__name__
        return inner
    return wrap


# --------------------------------------------------------------------------
# Steps
# --------------------------------------------------------------------------
@step("validate_inputs")
def validate_inputs(con, data_dir: Path) -> None:
    """Fail loudly if a file is missing or a required column is absent."""
    missing = [f for f, _ in config.RAW_SOURCES.values()
               if not (data_dir / f).is_file()]
    if missing:
        raise MissingFileError(
            f"Missing input file(s) in {data_dir}: {', '.join(missing)}. "
            "Download the Olist dataset from Kaggle and unzip it there.")

    for table, (fname, required) in config.RAW_SOURCES.items():
        cols = [r[0] for r in con.execute(
            "DESCRIBE SELECT * FROM read_csv_auto(?, header=true)",
            [str(data_dir / fname)]).fetchall()]
        # Some exports carry a UTF-8 byte-order mark on the first header
        cols = [c.lstrip("﻿") for c in cols]
        absent = [c for c in required if c not in cols]
        if absent:
            raise SchemaError(
                f"{fname} is missing expected column(s): {', '.join(absent)}. "
                f"Found: {', '.join(cols)}")
        log.info("  ok  %-42s %d columns", fname, len(cols))


@step("load_raw")
def load_raw(con, data_dir: Path) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    for table, (fname, _) in config.RAW_SOURCES.items():
        path = str(data_dir / fname)
        con.execute("BEGIN TRANSACTION")
        try:
            # all_varchar keeps raw = exactly what was in the file;
            # typing happens in staging where we can control it.
            con.execute(f"""
                CREATE OR REPLACE TABLE raw.{table} AS
                SELECT *,
                       '{fname}'          AS _source_file,
                       current_timestamp  AS _loaded_at
                FROM read_csv_auto(?, header=true, all_varchar=true)
            """, [path])
            # strip a possible BOM from the first column name
            first = con.execute(
                f"SELECT column_name FROM information_schema.columns "
                f"WHERE table_schema='raw' AND table_name='{table}' "
                f"ORDER BY ordinal_position LIMIT 1").fetchone()[0]
            if first.startswith("﻿"):
                con.execute(f'ALTER TABLE raw.{table} RENAME "{first}" '
                            f'TO "{first.lstrip(chr(0xFEFF))}"')
            con.execute("COMMIT")
        except Exception as exc:
            con.execute("ROLLBACK")
            raise PipelineError(f"Could not load {fname}: {exc}") from exc
        n = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        log.info("  raw.%-22s %9d rows", table, n)


def _run_checks(con, folder: Path, stage: str, run_id: str) -> list[dict]:
    """Run every check in a folder, record results, raise on any failure."""
    con.execute("CREATE SCHEMA IF NOT EXISTS dq")
    con.execute("""
        CREATE TABLE IF NOT EXISTS dq.check_history (
            run_id VARCHAR, run_at TIMESTAMP, stage VARCHAR, check_id VARCHAR,
            check_name VARCHAR, failing_rows BIGINT, total_rows BIGINT,
            fail_ratio DOUBLE, max_fail_ratio DOUBLE, passed BOOLEAN,
            handling VARCHAR)
    """)
    results, failed = [], []
    for path in sql_files(folder):
        sql = path.read_text()
        meta = parse_header(sql)
        failing, total = con.execute(sql).fetchone()
        ratio = (failing / total) if total else 0.0
        limit = float(meta.get("max_fail_ratio", 0))
        passed = ratio <= limit
        row = dict(run_id=run_id, run_at=datetime.now(), stage=stage,
                   check_id=meta.get("check_id", path.stem),
                   check_name=meta.get("name", path.stem),
                   failing_rows=int(failing), total_rows=int(total),
                   fail_ratio=ratio, max_fail_ratio=limit, passed=passed,
                   handling=meta.get("handling", ""))
        results.append(row)
        con.execute("INSERT INTO dq.check_history VALUES "
                    "(?,?,?,?,?,?,?,?,?,?,?)", list(row.values()))
        status = "PASS" if passed else "FAIL"
        log.info("  %s %-5s %-48s %7d / %-8d (limit %.2f%%)", status,
                 row["check_id"], row["check_name"][:48], failing, total,
                 limit * 100)
        if not passed:
            failed.append(row)

    # latest results per check (replaced each run -> no duplicates)
    con.execute(f"""
        CREATE OR REPLACE TABLE dq.latest_{stage} AS
        SELECT * FROM dq.check_history WHERE run_id = '{run_id}'
          AND stage = '{stage}'
    """)
    if failed:
        lines = "; ".join(
            f"{r['check_id']} {r['check_name']}: {r['failing_rows']} failing "
            f"of {r['total_rows']} rows ({r['fail_ratio']:.3%}), allowed "
            f"{r['max_fail_ratio']:.2%}"
            for r in failed)
        raise DataQualityError(f"DATA QUALITY ALARM - {lines}")
    return results


@step("dq_gate (checks on raw data)")
def dq_gate(con, run_id: str) -> list[dict]:
    return _run_checks(con, config.DQ_GATE_DIR, "gate", run_id)


@step("build_staging")
def build_staging(con) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS staging")
    for path in sql_files(config.STAGING_DIR):
        run_sql_file(con, path)
        table = path.stem.split("_", 1)[1]
        n = con.execute(f"SELECT count(*) FROM staging.{table}").fetchone()[0]
        log.info("  staging.%-20s %9d rows", table, n)


@step("build_marts")
def build_marts(con) -> None:
    con.execute("CREATE SCHEMA IF NOT EXISTS mart")
    for path in sql_files(config.MARTS_DIR):
        run_sql_file(con, path)
        table = path.stem.split("_", 1)[1]
        n = con.execute(f"SELECT count(*) FROM mart.{table}").fetchone()[0]
        log.info("  mart.%-23s %9d rows", table, n)


@step("dq_post (checks on the mart)")
def dq_post(con, run_id: str) -> list[dict]:
    return _run_checks(con, config.DQ_POST_DIR, "post", run_id)


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------
def run(data_dir: Path = config.DEFAULT_DATA_DIR,
        db_path: Path = config.DEFAULT_DB_PATH) -> None:
    run_id = datetime.now().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:6]
    log.info("=" * 70)
    log.info("Pipeline run %s | data=%s | db=%s", run_id, data_dir, db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    try:
        validate_inputs(con, data_dir)
        load_raw(con, data_dir)
        dq_gate(con, run_id)
        build_staging(con)
        build_marts(con)
        dq_post(con, run_id)
    finally:
        con.close()
    log.info("Pipeline run %s finished successfully", run_id)


def main() -> int:
    parser = argparse.ArgumentParser(description="Olist ELT pipeline")
    parser.add_argument("--data-dir", type=Path, default=config.DEFAULT_DATA_DIR)
    parser.add_argument("--db", type=Path, default=config.DEFAULT_DB_PATH)
    args = parser.parse_args()
    setup_logging()
    try:
        run(args.data_dir, args.db)
    except PipelineError as exc:
        log.critical("PIPELINE STOPPED: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
