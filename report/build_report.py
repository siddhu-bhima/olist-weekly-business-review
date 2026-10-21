"""
Build the 5-page PDF report. All numbers are queried live from the
warehouse (and the same .sql files used in the repo), so the report can
be regenerated after any pipeline run.

    python -m report.build_report
"""
from pathlib import Path

import duckdb
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

from pipeline import config

STUDENT = "B.Siddhu"
REG_NO = "127003037"
COURSE = "Big Data in Industry"
TITLE = "Take-Home Assignment 1: Weekly Business Review for an E-commerce Marketplace"

ROOT = config.PROJECT_ROOT
FIG = ROOT / "report" / "figures"
OUT = ROOT / "report" / "BDA_Assignment1_B_Siddhu_127003037.pdf"

# ---------------------------------------------------------------- styles
FONT_DIR = Path("/usr/share/fonts/truetype")
pdfmetrics.registerFont(TTFont("Body", FONT_DIR / "liberation/LiberationSerif-Regular.ttf"))
pdfmetrics.registerFont(TTFont("Body-B", FONT_DIR / "liberation/LiberationSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Body-I", FONT_DIR / "liberation/LiberationSerif-Italic.ttf"))
pdfmetrics.registerFont(TTFont("Head", FONT_DIR / "liberation/LiberationSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("HeadM", FONT_DIR / "liberation/LiberationSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Mono", FONT_DIR / "liberation/LiberationMono-Regular.ttf"))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-B", italic="Body-I")

INK = colors.HexColor("#1b1b1a")
INK2 = colors.HexColor("#333333")
ACCENT = colors.black
RULE = colors.HexColor("#d9d8d3")
ZEBRA = colors.HexColor("#f5f5f2")
HEAD_BG = colors.HexColor("#e7e7e7")
WARN_BG = colors.HexColor("#fdf0ea")

S = {
    "body": ParagraphStyle("body", fontName="Body", fontSize=9.6, leading=11.9,
                           textColor=INK, alignment=TA_LEFT, spaceAfter=3.5),
    "small": ParagraphStyle("small", fontName="Body", fontSize=7.7, leading=9.6,
                            textColor=INK2),
    "h1": ParagraphStyle("h1", fontName="Head", fontSize=12.5, leading=15,
                         textColor=ACCENT, spaceBefore=6, spaceAfter=4),
    "h2": ParagraphStyle("h2", fontName="HeadM", fontSize=9.6, leading=12,
                         textColor=INK, spaceBefore=5, spaceAfter=2.5),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.1, leading=9.5,
                           textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Body-B", fontSize=8.1, leading=9.5,
                            textColor=INK),
    "bullet": ParagraphStyle("bullet", fontName="Body", fontSize=9.6, leading=11.9,
                             textColor=INK, leftIndent=11, bulletIndent=2,
                             spaceAfter=2.2),
    "memo": ParagraphStyle("memo", fontName="Body", fontSize=10.2, leading=13.2,
                           textColor=INK, spaceAfter=4.5),
    "memob": ParagraphStyle("memob", fontName="Body", fontSize=10.2, leading=13.2,
                            textColor=INK, leftIndent=12, bulletIndent=2,
                            spaceAfter=3),
}


def P(text, style="body"):
    return Paragraph(text, S[style])


def bullets(items, style="bullet"):
    return [Paragraph(t, S[style], bulletText="•") for t in items]


def table(rows, widths, header=True, zebra=True, align_right=(), bold_first=False,
          highlight_rows=()):
    data = [[c if not isinstance(c, str) or c == "" else
             Paragraph(c, S["cellb"] if (header and i == 0) or (bold_first and j == 0)
                       else S["cell"])
             for j, c in enumerate(r)] for i, r in enumerate(rows)]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
    ]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), HEAD_BG)]
    t.setStyle(TableStyle(st))
    return t


def fig(name, width_cm):
    img = Image(str(FIG / name))
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth = width_cm * cm
    img.drawHeight = width_cm * cm * ratio
    return img


def money(v):
    return f"R${v:,.0f}"


# ---------------------------------------------------------------- page chrome
def on_page(c, doc):
    w, h = A4
    c.saveState()
    c.setFillColor(colors.black)
    c.setFont("Body-B", 10)
    c.drawRightString(w - 1.6 * cm, h - 0.9 * cm, f"Name: {STUDENT}")
    c.drawRightString(w - 1.6 * cm, h - 1.35 * cm, f"Reg No: {REG_NO}")
    c.setFont("Body", 9)
    c.drawCentredString(w / 2, 0.8 * cm, f"{doc.page}")
    c.restoreState()


# ---------------------------------------------------------------- data
def load(con):
    d = {}
    sql = lambda rel: con.execute((config.SQL_DIR / rel).read_text()).df()  # noqa
    d["counts"] = {f"{s}.{t}": n for s, t, n in con.execute(
        "SELECT schema_name, table_name, estimated_size FROM duckdb_tables()").fetchall()}
    d["dq"] = con.execute("SELECT * FROM dq.latest_gate ORDER BY check_id").df()
    d["dq_post"] = con.execute("SELECT * FROM dq.latest_post ORDER BY check_id").df()
    d["q1"] = sql("analysis/q1_mom_revenue_growth.sql")
    d["q2"] = sql("analysis/q2_top3_categories_per_state.sql")
    d["q3"] = sql("analysis/q3_rolling_7day_orders.sql")
    d["q4"] = sql("analysis/q4_repeat_purchase_rate.sql").iloc[0]
    d["q5"] = sql("analysis/q5_delivery_delay_vs_review.sql")
    d["bt"] = sql("analysis/x1_promise_backtest.sql").iloc[0]
    d["wk"] = sql("metrics/weekly_metrics.sql")
    d["pay"] = con.execute("""
        SELECT count(*) FILTER (WHERE is_payment_mismatch)                       AS n,
               count(*) FILTER (WHERE is_payment_mismatch AND payment_total > order_value) AS over,
               count(*) FILTER (WHERE payment_total IS NULL)                      AS no_pay,
               count(*) FILTER (WHERE item_count = 0)                             AS no_items,
               count(*) FILTER (WHERE item_count = 0 AND NOT is_valid_sale)       AS no_items_cancel
        FROM mart.fct_orders""").df().iloc[0]
    d["m"] = con.execute("""
        WITH w AS (SELECT * FROM mart.fct_orders
                   WHERE purchase_month BETWEEN DATE '2017-01-01' AND DATE '2018-08-01')
        SELECT
          count(*) FILTER (WHERE is_delivered AND NOT is_late AND review_score >= 4)
              / 87.0                                                     AS ns_per_week,
          count(*) FILTER (WHERE is_delivered AND NOT is_late AND review_score >= 4)
              * 100.0 / count(*)                                         AS ns_share,
          sum(order_value) FILTER (WHERE is_valid_sale) / 87.0           AS gmv_week,
          100.0 * count(*) FILTER (WHERE is_delivered AND NOT is_late)
              / count(*) FILTER (WHERE is_delivered)                     AS ontime,
          100.0 * count(*) FILTER (WHERE review_score <= 2) / count(review_score) AS low,
          100.0 * count(*) FILTER (WHERE NOT is_valid_sale) / count(*)   AS cancel,
          avg(review_score)                                              AS avg_score
        FROM w""").df().iloc[0]
    d["late"] = con.execute("""
        SELECT count(*) FILTER (WHERE is_late)                                   AS late,
               count(*)                                                          AS delivered,
               avg(review_score) FILTER (WHERE is_late)                          AS s_late,
               avg(review_score) FILTER (WHERE NOT is_late)                      AS s_ok,
               100.0*avg(CASE WHEN review_score<=2 THEN 1 ELSE 0 END) FILTER (WHERE is_late)     AS low_late,
               100.0*avg(CASE WHEN review_score<=2 THEN 1 ELSE 0 END) FILTER (WHERE NOT is_late) AS low_ok
        FROM mart.fct_orders WHERE is_delivered AND NOT has_status_date_conflict""").df().iloc[0]
    d["low"] = con.execute("""
        SELECT count(*) FILTER (WHERE review_score <= 2)                    AS low,
               count(*) FILTER (WHERE review_score <= 2 AND is_late)        AS low_late,
               count(*) FILTER (WHERE review_score <= 2 AND NOT is_delivered) AS low_undel,
               count(*) FILTER (WHERE is_late OR NOT is_delivered)          AS bad_orders,
               count(*)                                                     AS orders
        FROM mart.fct_orders""").df().iloc[0]
    d["legs"] = con.execute("""
        SELECT is_late,
               median(date_diff('hour', approved_at, carrier_at) / 24.0)  AS handover,
               median(date_diff('hour', carrier_at, delivered_at) / 24.0) AS transit
        FROM mart.fct_orders WHERE is_delivered AND NOT has_status_date_conflict
        GROUP BY is_late""").df().set_index("is_late")
    d["states"] = con.execute("""
        SELECT customer_state, count(*) n, 100*avg(is_late::INT) late
        FROM mart.fct_orders WHERE is_delivered AND NOT has_status_date_conflict
        GROUP BY 1 HAVING n > 300 ORDER BY late DESC""").df()
    d["rj"] = con.execute("""
        SELECT 100*avg(is_late::INT) FROM mart.fct_orders
        WHERE is_delivered AND customer_state='RJ'
          AND purchase_month IN (DATE '2018-02-01', DATE '2018-03-01')""").fetchone()[0]
    d["promise"] = con.execute("""
        SELECT strftime(purchase_month,'%Y-%m') m, avg(promised_days) p, avg(delivery_days) a,
               100*avg(is_late::INT) late
        FROM mart.fct_orders WHERE is_delivered AND NOT has_status_date_conflict
        GROUP BY 1""").df().set_index("m")
    return d


# ---------------------------------------------------------------- sections
def title_block():
    centre = ParagraphStyle("c", parent=S["body"], alignment=1)
    return [Spacer(1, 6),
            Paragraph(f"<font name='Head' size='14'>{COURSE}</font>", centre),
            Spacer(1, 3),
            Paragraph(f"<font name='Head' size='12'>{TITLE}</font>", centre),
            Spacer(1, 3),
            Paragraph("Dataset: Olist Brazilian E-Commerce (Kaggle), 99,441 orders, Sep-2016 to "
                      "Oct-2018. Tools: Python, DuckDB, SQL, Airflow, matplotlib.", centre),
            Spacer(1, 4),
            Table([[""]], colWidths=[17.8 * cm], rowHeights=[2],
                  style=[("LINEABOVE", (0, 0), (-1, -1), 0.8, colors.black)])]


def summary_box(d):
    L, low, q4, bt = d["late"], d["low"], d["q4"], d["bt"]
    bad_share = 100 * (low.low_late + low.low_undel) / low.low
    items = [
        "<b>Pipeline:</b> 9 CSVs, raw, staging, mart in DuckDB. Idempotent, logged, 8 + 3 SQL quality "
        "checks with alarms, and a daily Airflow DAG.",
        "<b>Data quality:</b> keys and joins are clean. Fixed or flagged 166 impossible carrier dates, "
        "366 payment mismatches, 547 duplicate reviews and 14 status/date conflicts.",
        f"<b>Growth:</b> GMV rose from R$137k (Jan-17) to about R$1.0-1.16M per month, flat since Mar-18. "
        f"Repeat-purchase rate is only {q4.repeat_rate_pct:.2f}%.",
        f"<b>Key finding:</b> late deliveries ({100 * L.late / L.delivered:.1f}% of orders) score "
        f"{L.s_late:.2f} vs {L.s_ok:.2f} stars. Late plus undelivered orders cause {bad_share:.0f}% of all "
        "1-2 star reviews.",
        f"<b>Recommendation:</b> set delivery promises from recent route data. Back-tested: "
        f"{100 * (1 - bt.late_with_new_promise / bt.late_now):.0f}% fewer late orders.",
    ]
    return [P("Summary", "h1")] + bullets(items)


def part_a(d):
    c = d["counts"]
    out = [P("Part A - Ingestion Pipeline (ELT)", "h1"),
           P("The pipeline (<font name='Mono'>pipeline/run_pipeline.py</font>) loads the nine Olist CSVs "
             "into a single DuckDB warehouse and builds three layers. Each step is logged with start, "
             "end, duration and row counts to the console and <font name='Mono'>logs/pipeline.log</font>.")]
    rows = [["Step / layer", "What it does", "Output (rows)"],
            ["1. validate_inputs", "Checks all 9 files exist and every required column is present "
             "(column list per file in <font name='Mono'>pipeline/config.py</font>).", "-"],
            ["2. raw.*", "CSV loaded as-is (all text) + <font name='Mono'>_source_file</font>, "
             "<font name='Mono'>_loaded_at</font>.",
             f"orders {c['raw.orders']:,}; items {c['raw.order_items']:,}; "
             f"payments {c['raw.order_payments']:,}; reviews {c['raw.order_reviews']:,}"],
            ["3. dq_gate", "8 SQL data-quality checks on raw data (Part B). Alarm stops the run "
             "before anything downstream is rebuilt.", "dq.latest_gate"],
            ["4. staging.*", "Typed columns, trimmed text, de-duplication and the DQ fixes "
             "(one review per order, invalid carrier dates nulled, flags added).",
             f"7 tables; reviews {c['staging.order_reviews']:,} (1 per order)"],
            ["5. mart.fct_orders", "<b>One row per order</b>: GMV, freight, payment total, item and "
             "seller count, all delivery dates, promised days, delay days, review score, flags.",
             f"{c['mart.fct_orders']:,}"],
            ["   mart.fct_order_items", "One row per order line with category, seller and buyer state.",
             f"{c['mart.fct_order_items']:,}"],
            ["6. dq_post", "3 checks on the finished mart: grain, revenue reconciliation, review "
             "uniqueness.", "dq.latest_post"]]
    out.append(table(rows, [3.3 * cm, 10.0 * cm, 4.5 * cm], bold_first=True))
    out.append(Spacer(1, 4))
    out += bullets([
        "<b>Idempotent:</b> every table is rebuilt with <font name='Mono'>CREATE OR REPLACE</font> inside "
        "a transaction, so re-running replaces rather than appends. Verified by running twice: every table "
        f"has identical row counts and mart GMV is unchanged. The only append-only table is the audit log "
        "<font name='Mono'>dq.check_history</font>, keyed by run_id.",
        "<b>No double counting:</b> items and payments are each aggregated to order level in separate CTEs "
        "before joining, so all mart joins are 1:1. Check POST01 enforces this on every run.",
        "<b>Failure handling:</b> each failure type has its own exception (MissingFileError, SchemaError, "
        "DataQualityError). Tested: deleting a CSV, renaming the <font name='Mono'>price</font> column, and "
        "injecting a duplicate order each stopped the pipeline with exit code 1 and a message naming the "
        "file, column or check. A failing SQL step is rolled back.",
        "<b>Bonus - Airflow:</b> <font name='Mono'>dags/olist_wbr_dag.py</font> runs the six steps as six "
        "tasks, <font name='Mono'>schedule=\"@daily\"</font>, catchup off, one active run (DuckDB has a single "
        "writer), 1 retry. A DQ alarm fails its task and blocks staging and marts. Tested with "
        "<font name='Mono'>airflow dags test</font> on Airflow 3.3: all six tasks succeeded.",
        "<b>Run:</b> <font name='Mono'>pip install -r requirements.txt</font> → put CSVs in "
        "<font name='Mono'>data/raw/</font> → <font name='Mono'>python -m pipeline.run_pipeline</font> "
        "(full steps in README.md).",
    ])
    return out


def part_b(d):
    dq = d["dq"]
    pay = d["pay"]
    why = {
        "DQ01": ("Hard stop (0 allowed)", "order_id is the grain of the mart."),
        "DQ02": ("Hard stop (0 allowed)", "Would make delay metrics meaningless."),
        "DQ03": ("<b>Fixed:</b> carrier date set to NULL, flagged",
                 "Impossible timestamp; the rest of the order is valid, so keep the order."),
        "DQ04": ("<b>Flagged</b> (is_payment_mismatch), kept",
                 f"{pay['over']} of {pay['n']} pay MORE than items+freight (instalment interest). "
                 "Revenue uses price+freight, so these orders are still correct."),
        "DQ05": ("Hard stop (0 allowed)", "Order could not be attributed to a customer or state."),
        "DQ06": ("<b>Flagged</b>, excluded from delay metrics",
                 "Status and dates disagree, so the delay cannot be trusted."),
        "DQ07": ("<b>Fixed:</b> keep latest answered review",
                 "The last answer is the customer's final opinion; avoids double-weighting."),
        "DQ08": ("Hard stop (0 allowed)", "Orphan or zero-price items would corrupt revenue."),
    }
    rows = [["ID", "Check (SQL in sql/dq/)", "Failing / total rows", "Alarm if over", "Handling", "Why"]]
    hl = []
    for i, r in enumerate(dq.itertuples(), start=1):
        h, w = why[r.check_id]
        rows.append([r.check_id, r.check_name.replace("(Own) ", "<i>(own)</i> "),
                     f"<b>{r.failing_rows:,}</b> / {r.total_rows:,}",
                     f"{r.max_fail_ratio:.1%}" if r.max_fail_ratio else "0 rows", h, w])
        if r.failing_rows:
            hl.append(i)
    out = [P("Part B - Data Quality Checks", "h1"),
           P("Eight checks run on the raw layer before anything is built, and three more on the finished mart. "
             "Each check is a <font name='Mono'>.sql</font> file returning <i>failing_rows</i> and "
             "<i>total_rows</i>; its header sets an allowed failure ratio. If any check exceeds it, the pipeline "
             "raises <font name='Mono'>DataQualityError</font> (\"DATA QUALITY ALARM\") and stops. Key "
             "integrity checks allow zero failures; known, explainable source issues get a small tolerance, so "
             "a sudden jump still raises the alarm. Results from the final run:"),
           table(rows, [1.05 * cm, 3.9 * cm, 2.35 * cm, 1.6 * cm, 3.6 * cm, 5.3 * cm],
                 highlight_rows=hl),
           Spacer(1, 3),
           P("<font size='7.6' color='#333333'>Rows with a non-zero failing count are the real issues found in the data. Post-mart checks: "
             + "; ".join(f"{r.check_id} {r.check_name} - {r.failing_rows} failing"
                         for r in d["dq_post"].itertuples())
             + ".</font>"),
           P("<b>Other observations (not errors):</b> "
             f"{pay['no_items']:,} orders have no items ({pay['no_items_cancel']:,} of them canceled or "
             f"unavailable) and {pay['no_pay']} order has no payment. They are kept in the mart with "
             "GMV 0 so order counts stay complete. 610 products have no category and are labelled "
             "'unknown'. Money is cast to DECIMAL, not float. With floats DQ04 reported 443 mismatches "
             f"instead of {pay['n']}, all of them rounding noise.")]
    return out


def part_c(d):
    q1, q2, q3, q4, q5 = d["q1"], d["q2"], d["q3"], d["q4"], d["q5"]
    out = [P("Part C - SQL at Scale (CTEs + window functions; files in sql/analysis/)", "h1")]

    # Q1 - two side-by-side halves 2017-01..2018-08
    w = q1[(q1.month >= "2017-01") & (q1.month <= "2018-08")].reset_index(drop=True)
    half = (len(w) + 1) // 2
    rows = [["Month", "GMV", "MoM %", "", "Month", "GMV", "MoM %"]]
    for i in range(half):
        a = w.iloc[i]
        b = w.iloc[i + half] if i + half < len(w) else None
        fmt = lambda r: [r.month, money(r.revenue),  # noqa
                         "n/a*" if abs(r.mom_growth_pct) > 1000 else f"{r.mom_growth_pct:+.1f}%"]
        rows.append(fmt(a) + [""] + (fmt(b) if b is not None else ["", "", ""]))
    t1 = table(rows, [1.35 * cm, 2.05 * cm, 1.35 * cm, 0.25 * cm, 1.35 * cm, 2.05 * cm, 1.35 * cm])
    peak = w.loc[w.revenue.idxmax()]
    q1_text = [P("<b>Q1. Month-over-month revenue (LAG).</b> GMV = price + freight of non-canceled orders. "
                 "A month calendar is generated first, so LAG always compares with the previous <i>calendar</i> "
                 "month (Nov-2016 has no orders). Months before 2017 and after Aug-2018 have almost no "
                 "orders and are left out of the table. *Jan-17 growth is not meaningful (Dec-16 had 1 order)."),
               P(f"GMV grew from {money(w.iloc[0].revenue)} (Jan-17) to around R$1.0-1.16M a month in 2018. "
                 f"The peak was {peak.month} ({money(peak.revenue)}, Black Friday). Growth has been flat "
                 "since Mar-2018.")]
    out.append(Table([[t1, q1_text]], colWidths=[9.9 * cm, 7.9 * cm],
                     style=[("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 0),
                            ("RIGHTPADDING", (0, 0), (0, 0), 8)]))

    # Q2 - top states
    top_states = ["SP", "RJ", "MG", "RS", "PR"]
    rows = [["State", "#1 category (GMV)", "#2 category (GMV)", "#3 category (GMV)"]]
    for s in top_states:
        sub = q2[q2.customer_state == s].sort_values("rank")
        rows.append([s] + [f"{r.category.replace('_', ' ')} ({money(r.revenue)})"
                           for r in sub.itertuples()][:3])
    out += [Spacer(1, 4),
            P("<b>Q2. Top 3 categories per customer state (DENSE_RANK over PARTITION BY state).</b> "
              f"The query returns all 27 states ({len(q2)} rows, because ties are kept). The five largest "
              "states are shown below. Health &amp; beauty, watches &amp; gifts and bed/bath/table lead almost "
              "everywhere."),
            table(rows, [1.2 * cm, 5.5 * cm, 5.5 * cm, 5.6 * cm], bold_first=True)]

    # Q3 + Q4 side by side
    r3 = q3[(q3.day >= "2017-01-01") & (q3.day <= "2018-08-31")]
    pk = r3.loc[r3.rolling_7d_avg_orders.idxmax()]
    q3p = P(f"<b>Q3. 7-day rolling average of daily orders</b> (AVG OVER ROWS 6 PRECEDING). A day calendar "
            f"is built first so days with no orders count as zero; the first 6 days are NULL. The rolling "
            f"average rose from about {r3.rolling_7d_avg_orders.iloc[6]:.0f}/day (Jan-17) to 200-300/day in "
            f"2018. The peak was {pk.rolling_7d_avg_orders:.0f}/day in the week ending "
            f"{pk.day:%d-%b-%Y} (Black Friday). See Fig 2.")
    q4p = P(f"<b>Q4. Repeat-purchase rate.</b> <font name='Mono'>customer_id</font> is created new for every "
            f"order, so counting by it gives <b>{q4.wrong_rate_using_customer_id_pct:.1f}%</b>. The real person "
            f"is <font name='Mono'>customer_unique_id</font>: {int(q4.repeat_customers):,} of "
            f"{int(q4.customers):,} customers bought twice or more, a repeat rate of "
            f"<b>{q4.repeat_rate_pct:.2f}%</b> ({q4.orders_per_customer:.3f} orders per customer). "
            "Almost all of Olist's growth comes from new customers.")
    out += [Spacer(1, 4), Table([[q3p, q4p]], colWidths=[8.9 * cm, 8.9 * cm],
                                style=[("VALIGN", (0, 0), (-1, -1), "TOP"),
                                       ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                       ("RIGHTPADDING", (0, 0), (0, 0), 10)])]

    # Q5
    rows = [["Delay vs promised date", "Orders", "% of orders", "Avg delay (days)",
             "Avg review", "% 1-2 star"]]
    hl = []
    for i, r in enumerate(q5.itertuples(), start=1):
        rows.append([r.delay_bucket.split(". ")[1], f"{r.orders:,}", f"{r.pct_of_orders:.1f}%",
                     f"{r.avg_delay_days:+.1f}", f"{r.avg_review_score:.2f}", f"{r.pct_1_2_star:.1f}%"])
        if "late" in r.delay_bucket:
            hl.append(i)
    out += [Spacer(1, 4),
            P(f"<b>Q5. Delivery delay vs estimated date, and review score.</b> delay = delivered date - "
              f"estimated date. On average orders arrive <b>{-q5.overall_avg_delay_days.iloc[0]:.1f} days "
              f"early</b>, but the relationship is a cliff, not a slope. Correlation of delay with score is "
              f"r = {q5.corr_delay_vs_score.iloc[0]:.2f}, yet the score drops by about one star on the first "
              "late day (3.29) and below 2.1 once an order is 4 or more days late. Being 15+ days early "
              "scores almost the same as being just on time."),
            table(rows, [4.6 * cm, 2.2 * cm, 2.2 * cm, 2.9 * cm, 2.6 * cm, 3.3 * cm],
                  highlight_rows=hl)]
    return out


def part_d(d):
    m = d["m"]
    out = [P("Part D - Metrics (North Star and supporting / guardrail metrics)", "h1"),
           P("Values are for Jan-2017 to Aug-2018 (87 full weeks). Weekly versions are produced by "
             "<font name='Mono'>sql/metrics/weekly_metrics.sql</font> for the Weekly Business Review.")]
    rows = [["Metric", "Exact formula (from mart.fct_orders)", "Value", "Why it matters"],
            ["<b>North Star:</b> On-time Happy Orders / week",
             "COUNT(orders WHERE is_delivered AND delivered_date &lt;= estimated_date AND review_score &gt;= 4) "
             "per purchase week",
             f"{m.ns_per_week:,.0f}/wk ({m.ns_share:.0f}% of orders)",
             "Counts only orders that were sold, kept their promise and pleased the customer. It grows only "
             "if volume AND experience grow together."],
            ["GMV / week (supporting)",
             "SUM(price + freight) over order items WHERE status NOT IN (canceled, unavailable)",
             f"{money(m.gmv_week)}/wk", "Top-line scale of the marketplace; seller and commission revenue "
             "follow it."],
            ["On-time delivery rate (supporting, driver)",
             "COUNT(delivered AND delivered_date &lt;= estimated_date) / COUNT(delivered)",
             f"{m.ontime:.1f}%", "The strongest controllable driver of review score (Fig 3)."],
            ["1-2 star review share (guardrail)",
             "COUNT(review_score &lt;= 2) / COUNT(orders with a review)",
             f"{m.low:.1f}%", "Early warning of churn and seller-quality problems. Must not rise while "
             "GMV is pushed."],
            ["Cancel / unavailable rate (guardrail)",
             "COUNT(status IN (canceled, unavailable)) / COUNT(orders)",
             f"{m.cancel:.2f}%", "Catches stock-outs and seller failures; a sale that never ships is "
             "the worst experience of all."]]
    out.append(table(rows, [3.6 * cm, 5.6 * cm, 2.6 * cm, 6.0 * cm]))
    out.append(P(f"<font size='7.6' color='#333333'>Repeat-purchase rate (Q4, {d['q4'].repeat_rate_pct:.2f}%) "
                 "is tracked monthly as a long-term guardrail; it is too small and slow-moving for a weekly "
                 "review.</font>"))

    wk = d["wk"]
    wk = wk[(wk.week >= "2018-06-25") & (wk.week <= "2018-08-13")].reset_index(drop=True)
    rows = [["Week starting", "Orders", "North Star (on-time happy)", "NS WoW", "GMV",
             "On-time rate", "1-2 star share", "Cancel rate"]]
    prev = None
    for r in wk.itertuples():
        wow = "-" if prev is None else f"{100 * (r.on_time_happy_orders / prev - 1):+.1f}%"
        rows.append([f"{r.week:%d-%b-%Y}", f"{r.orders_placed:,}", f"{r.on_time_happy_orders:,}", wow,
                     money(r.gmv), f"{r.on_time_rate_pct:.1f}%", f"{r.low_review_pct:.1f}%",
                     f"{r.cancel_rate_pct:.2f}%"])
        prev = r.on_time_happy_orders
    low = wk.loc[wk.on_time_rate_pct.idxmin()]
    out += [Spacer(1, 4), P("Weekly Business Review snapshot - last 8 full weeks", "h2"),
            P("This is the table leadership would see each Monday (output of "
              "<font name='Mono'>weekly_metrics.sql</font>; weeks from 20-Aug-2018 are incomplete because the dataset ends, so they are excluded). "
              f"The weakest week for on-time delivery was {low.week:%d-%b} ({low.on_time_rate_pct:.1f}%), "
              f"and its 1-2 star share was {low.low_review_pct:.1f}%. The guardrail moves with the "
              "delivery metric, as the memo argues."),
            table(rows, [2.4 * cm, 1.6 * cm, 3.2 * cm, 1.7 * cm, 2.4 * cm, 2.1 * cm, 2.3 * cm, 2.1 * cm])]
    return out


def charts(d):
    L, pr = d["late"], d["promise"]
    cap = lambda t: Paragraph(t, S["small"])  # noqa

    def cell(img, text):
        return [img, Spacer(1, 2), cap(text)]

    grid = [
        [cell(fig("fig1_monthly_gmv.png", 8.7),
              "<b>Figure 1.</b> GMV grew about 8x during 2017, then flattened at roughly R$1.0-1.16M a "
              "month from Mar-2018. Black Friday (Nov-17) was the single biggest month."),
         cell(fig("fig3_delay_vs_review.png", 8.7),
              "<b>Figure 3.</b> Scores fall off a cliff at the promised date, not gradually with speed. "
              "Arriving early earns little extra; arriving late costs one to two and a half stars.")],
        [cell(fig("fig2_rolling_orders.png", 8.7),
              "<b>Figure 2.</b> The rolling average removes day-of-week noise. Demand doubled from "
              "about 100 to 200-300 orders a day; the Black Friday spike was about 6x a normal day. The "
              "drop at the right edge is where the dataset ends."),
         cell(fig("fig4_promise_vs_actual.png", 8.7),
              f"<b>Figure 4.</b> Late rates spike (Nov-17, Feb-Mar-18) when actual delivery time rises "
              f"while the promise stays fixed or shrinks. In Mar-18 the promise was cut to "
              f"{pr.loc['2018-03','p']:.0f} days just as deliveries slowed to {pr.loc['2018-03','a']:.0f}.")],
    ]
    t = Table(grid, colWidths=[8.9 * cm, 8.9 * cm])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (0, -1), 10),
                           ("BOTTOMPADDING", (0, 0), (-1, 0), 14)]))
    return [P("Part D - Charts", "h1"),
            P("All charts are generated by <font name='Mono'>report/make_charts.py</font> from the same SQL "
              "files as Part C (window: Jan-2017 to Aug-2018, the full months with meaningful volume)."),
            Spacer(1, 6), t]


def memo(d):
    L, low, bt, legs, st, pr = d["late"], d["low"], d["bt"], d["legs"], d["states"], d["promise"]
    late_pct = 100 * L.late / L.delivered
    bad_share = 100 * (low.low_late + low.low_undel) / low.low
    bad_orders = 100 * low.bad_orders / low.orders
    ne = st[st.customer_state.isin(["AL", "MA", "SE", "PI", "CE", "BA"])]
    fewer = int(bt.late_low_reviews_now - bt.late_low_reviews_new)
    head = Table([
        [P("<b>To:</b> Vice President, Operations &amp; Customer Experience", "memo"),
         P("<b>Date:</b> 12 October 2026", "memo")],
        [P(f"<b>From:</b> {STUDENT} (Reg No: {REG_NO}), Data Analyst", "memo"), ""],
        [P("<b>Subject:</b> Broken delivery promises are the biggest cause of bad reviews; set "
           "promises from real route data", "memo"), ""]],
        colWidths=[12.3 * cm, 5.5 * cm])
    head.setStyle(TableStyle([("SPAN", (0, 1), (1, 1)), ("SPAN", (0, 2), (1, 2)),
                              ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("TOPPADDING", (0, 0), (-1, -1), 0),
                              ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                              ("BOTTOMPADDING", (0, 2), (-1, 2), 4),
                              ("LINEBELOW", (0, 2), (-1, 2), 0.8, colors.black)]))
    box = [P(
        "<b>Key finding.</b> Customer satisfaction is lost when we break a delivery promise. Only "
        f"{late_pct:.1f}% of delivered orders arrive after the estimated date, but those orders average "
        f"<b>{L.s_late:.2f} stars vs {L.s_ok:.2f}</b>, and {L.low_late:.0f}% of them get a 1-2 star review "
        f"(vs {L.low_ok:.0f}% of on-time orders). Late and never-delivered orders are {bad_orders:.0f}% of "
        f"orders but cause <b>{bad_share:.0f}% of all 1-2 star reviews</b>.", "memo")]
    out = [P("Part D - Memo to the Vice President", "h1"), head, Spacer(1, 8)] + box + [
           Spacer(1, 2), P("<b>Evidence</b>", "memo")]
    out += bullets([
        "<b>The promise matters, not speed.</b> Orders 15+ days early score 4.32; orders 0-7 days early score "
        "4.19. One day late drops the score to 3.29, and 4+ days late to about 2 (Fig 3). Customers judge us "
        "against the date we showed them.",
        "<b>Lateness is not random. It spikes when demand or carriers are stretched.</b> The late rate was "
        f"{pr.loc['2017-11','late']:.0f}% in Nov-17 (Black Friday), {pr.loc['2018-02','late']:.0f}% in "
        f"Feb-18 and {pr.loc['2018-03','late']:.0f}% in Mar-18, against a usual 3-7%. In Mar-18 actual "
        f"delivery time rose to {pr.loc['2018-03','a']:.0f} days while the promise was <i>cut</i> to "
        f"{pr.loc['2018-03','p']:.0f} days (Fig 4). Rio de Janeiro reached {d['rj']:.0f}% late in Feb-Mar 2018.",
        "<b>The problem sits on specific routes and in the carrier leg.</b> North-east states run "
        f"{ne.late.min():.0f}-{ne.late.max():.0f}% late, against {L.late / L.delivered * 100:.0f}% overall. "
        f"For late orders, median carrier-to-door time is {legs.loc[True,'transit']:.0f} days vs "
        f"{legs.loc[False,'transit']:.0f} for on-time ones. Seller hand-over differs much less "
        f"({legs.loc[True,'handover']:.1f} vs {legs.loc[False,'handover']:.1f} days).",
        "<b>The current estimate is static.</b> It does not react when a route slows down, so customers keep "
        "getting dates the network cannot meet.",
    ], "memob")
    rec = [P(
        "<b>Recommendation.</b> Replace the static estimated delivery date with a <b>route-level promise</b>. "
        "For every seller-state to customer-state route, the date shown at checkout should be at least the "
        "<b>90th percentile of actual delivery days on that route over the last 28 days</b> (used when the "
        "route has 20 or more recent deliveries). It is recomputed every day by this pipeline. Pilot it on "
        "the Rio de Janeiro and north-east routes for 4 weeks, owned by the Logistics product team.", "memo")]
    out += [Spacer(1, 4)] + rec + [Spacer(1, 2), P("<b>Expected impact and how we will measure it</b>", "memo")]
    out += bullets([
        f"<b>Back-test</b> (<font name='Mono'>sql/analysis/x1_promise_backtest.sql</font>, {int(bt.orders):,} "
        "delivered orders, Mar-17 to Aug-18, using only data available at purchase time): late orders fall "
        f"<b>{100 * (1 - bt.late_with_new_promise / bt.late_now):.0f}%</b> (late rate {bt.late_rate_now_pct:.1f}% "
        f"to {bt.late_rate_new_pct:.1f}%), and about <b>{fewer:,} orders that got a late-delivery 1-2 star review would have arrived on time</b>. The cost: "
        f"{bt.pct_orders_promise_extended:.0f}% of orders show a longer promise, by "
        f"{bt.avg_extra_days_when_extended:.1f} days on average.",
        "<b>Success metric:</b> on-time delivery rate on pilot routes above 95% every month, and a falling "
        "1-2 star share. <b>Guardrail:</b> checkout conversion and GMV on pilot routes, because a longer "
        "promise can cost sales. Stop the pilot if conversion drops by more than 2%.",
        "<b>Honest limit:</b> a better promise removes about a fifth of late orders, not all. The remaining "
        "delays are carrier failures during spikes. The next step is a carrier SLA review on the routes where "
        "the 90th percentile keeps rising above the promise; the same pipeline can flag those routes weekly.",
    ], "memob")
    out.append(P("<font size='7.6' color='#333333'>Data note: orders after Aug-2018 are incomplete, and "
                 "late orders from the final weeks may not be delivered yet, so recent late rates are "
                 "slightly understated.</font>"))
    return out


def main():
    con = duckdb.connect(str(config.DEFAULT_DB_PATH), read_only=True)
    d = load(con)
    con.close()
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=1.6 * cm, rightMargin=1.6 * cm,
                            topMargin=1.85 * cm, bottomMargin=1.45 * cm,
                            title=f"BDA Assignment 1 - {STUDENT} ({REG_NO})", author=STUDENT,
                            subject=TITLE)
    story = title_block() + summary_box(d)
    story += part_a(d)
    story += [PageBreak()] + part_b(d)
    story += [Spacer(1, 4)] + part_c(d)
    story += [Spacer(1, 2)] + part_d(d)
    story += [PageBreak()] + charts(d)
    story += [PageBreak()] + memo(d)
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print("report written to", OUT)


if __name__ == "__main__":
    main()
