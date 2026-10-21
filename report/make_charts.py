"""
Build the report charts from the warehouse. Every chart is fed by one of
the .sql files in sql/analysis or sql/metrics, so the figures and the
query results in the report always agree.

    python -m report.make_charts
"""
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

from pipeline import config  # noqa: E402

OUT = config.PROJECT_ROOT / "report" / "figures"
WINDOW = ("2017-01-01", "2018-08-31")   # full months with meaningful volume

# plain matplotlib defaults (tab:blue / tab:orange), light dashed grid
BLUE, ORANGE = "tab:blue", "tab:orange"
INK, INK2 = "black", "black"

plt.style.use("default")
plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 9, "xtick.labelsize": 7,
    "ytick.labelsize": 7, "legend.fontsize": 7, "savefig.dpi": 200,
    "axes.grid": True, "grid.linestyle": "--", "grid.alpha": 0.4,
})


def q(con, rel_path: str):
    return con.execute((config.SQL_DIR / rel_path).read_text()).df()


def clean_x(ax):
    ax.grid(axis="x", visible=False)


def chart_monthly_gmv(con):
    df = q(con, "analysis/q1_mom_revenue_growth.sql")
    df = df[(df.month >= WINDOW[0][:7]) & (df.month <= WINDOW[1][:7])]
    fig, ax = plt.subplots(figsize=(4.7, 3.75))
    ax.bar(df.month, df.revenue / 1e6, color=BLUE, width=0.72)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"R${v:.1f}M"))
    ax.set_xticks(range(len(df)))
    ax.set_xticklabels([m[2:].replace("-", "/") if i % 3 == 0 else ""
                        for i, m in enumerate(df.month)])
    clean_x(ax)
    # direct labels only on the notable months
    for i, r in enumerate(df.itertuples()):
        if r.month == "2017-11":
            ax.annotate(f"Black Friday {r.mom_growth_pct:+.0f}% MoM", (i, r.revenue / 1e6),
                        xytext=(0, 3), textcoords="offset points",
                        ha="center", fontsize=7.5, color=INK)
    ax.set_ylim(0, 1.38)
    ax.set_title("Monthly GMV (price + freight)")
    ax.set_ylabel("GMV")
    fig.tight_layout()
    fig.savefig(OUT / "fig1_monthly_gmv.png")
    plt.close(fig)


def chart_rolling_orders(con):
    df = q(con, "analysis/q3_rolling_7day_orders.sql")
    df = df[(df.day >= WINDOW[0]) & (df.day <= WINDOW[1])]
    fig, ax = plt.subplots(figsize=(4.7, 3.75))
    ax.plot(df.day, df.orders, color=BLUE, alpha=0.35, linewidth=0.8, label="Daily orders")
    ax.plot(df.day, df.rolling_7d_avg_orders, color=BLUE, linewidth=2,
            label="7-day rolling average")
    peak = df.loc[df.orders.idxmax()]
    ax.annotate(f"Black Friday\n{int(peak.orders):,} orders",
                (peak.day, peak.orders), xytext=(-80, -10),
                textcoords="offset points", fontsize=7.5, color=INK,
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.7))
    ax.legend(loc="upper left", bbox_to_anchor=(0, 0.84))
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%y/%m"))
    clean_x(ax)
    ax.set_title("Daily orders, 7-day rolling average")
    ax.set_ylabel("Orders per day")
    fig.tight_layout()
    fig.savefig(OUT / "fig2_rolling_orders.png")
    plt.close(fig)


def chart_delay_vs_review(con):
    df = q(con, "analysis/q5_delivery_delay_vs_review.sql")
    labels = [b.split(". ")[1].replace(" days ", " days\n") for b in df.delay_bucket]
    colors = [ORANGE if "late" in b else BLUE for b in df.delay_bucket]
    fig, ax = plt.subplots(figsize=(4.7, 3.75))
    bars = ax.bar(labels, df.avg_review_score, color=colors, width=0.68)
    for b, s, p in zip(bars, df.avg_review_score, df.pct_1_2_star):
        ax.text(b.get_x() + b.get_width() / 2, s + 0.06,
                f"{s:.2f}\n{p:.0f}% 1-2★", ha="center", va="bottom",
                fontsize=6.4, color=INK, linespacing=1.05)
    ax.set_ylim(0, 5.9)
    ax.set_yticks([0, 1, 2, 3, 4, 5])
    ax.set_ylabel("Avg review score")
    ax.tick_params(axis="x", labelsize=6.4)
    clean_x(ax)
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color=BLUE, label="On time / early"),
                       Patch(color=ORANGE, label="Late")],
              loc="upper right", ncol=2, bbox_to_anchor=(1, 1.04))
    ax.set_title("Review score by delay vs promised date")
    fig.tight_layout()
    fig.savefig(OUT / "fig3_delay_vs_review.png")
    plt.close(fig)


def chart_promise_vs_actual(con):
    df = con.execute("""
        SELECT strftime(purchase_month, '%Y-%m') AS month,
               avg(promised_days)                AS promised,
               avg(delivery_days)                AS actual,
               100.0 * avg(CASE WHEN is_late THEN 1 ELSE 0 END) AS late_pct
        FROM mart.fct_orders
        WHERE is_delivered AND NOT has_status_date_conflict
          AND purchase_month BETWEEN ? AND ?
        GROUP BY 1 ORDER BY 1
    """, list(WINDOW)).df()
    x = range(len(df))
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(4.7, 3.75), sharex=True,
                                 gridspec_kw={"height_ratios": [1.25, 1]})
    a1.plot(x, df.promised, color=BLUE, lw=1.5, marker="o", ms=3)
    a1.plot(x, df.actual, color=ORANGE, lw=1.5, marker="o", ms=3)
    a1.text(len(df) - 0.6, df.promised.iloc[-1], "Promised", color=INK,
            fontsize=7.5, va="center")
    a1.text(len(df) - 0.6, df.actual.iloc[-1], "Actual", color=INK,
            fontsize=7.5, va="center")
    a1.set_ylabel("Avg days\nfrom purchase")
    a1.set_ylim(0, max(df.promised.max(), df.actual.max()) * 1.08)
    a1.set_title("Promised vs actual days, and % late")
    a2.bar(x, df.late_pct, color=ORANGE, width=0.72)
    for i, r in enumerate(df.itertuples()):
        if r.late_pct > 10:
            a2.text(i, r.late_pct + 0.6, f"{r.late_pct:.0f}%", ha="center",
                    fontsize=6.6, color=INK)
    a2.set_ylabel("% late")
    a2.set_ylim(0, 24)
    a2.set_xticks(list(x))
    a2.set_xticklabels([m[2:].replace("-", "/") if i % 3 == 0 else ""
                        for i, m in enumerate(df.month)])
    for a in (a1, a2):
        clean_x(a)
    a1.set_xlim(-0.6, len(df) + 1.0)
    fig.tight_layout(h_pad=0.6)
    fig.savefig(OUT / "fig4_promise_vs_actual.png")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(config.DEFAULT_DB_PATH), read_only=True)
    chart_monthly_gmv(con)
    chart_rolling_orders(con)
    chart_delay_vs_review(con)
    chart_promise_vs_actual(con)
    con.close()
    print("charts written to", OUT)


if __name__ == "__main__":
    main()
