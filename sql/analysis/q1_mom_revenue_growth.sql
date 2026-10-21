-- Q1. Month-over-month revenue and growth %.
-- Revenue (GMV) = item price + freight of valid sales (not canceled /
-- unavailable), dated by purchase month. Taken from mart.fct_orders, which
-- is one row per order, so there is no join fan-out.
-- A month calendar is generated so a month with no sales (Nov-2016) shows
-- as 0 and LAG always compares with the true previous calendar month.
WITH bounds AS (
    SELECT min(purchase_month) AS m0, max(purchase_month) AS m1
    FROM mart.fct_orders WHERE is_valid_sale
),
months AS (
    SELECT CAST(m AS DATE) AS purchase_month
    FROM bounds, generate_series(m0, m1, INTERVAL 1 MONTH) AS t(m)
),
monthly AS (
    SELECT purchase_month, count(*) AS orders, sum(order_value) AS revenue
    FROM mart.fct_orders
    WHERE is_valid_sale
    GROUP BY purchase_month
),
filled AS (
    SELECT m.purchase_month,
           coalesce(x.orders, 0)  AS orders,
           coalesce(x.revenue, 0) AS revenue
    FROM months m LEFT JOIN monthly x USING (purchase_month)
)
SELECT
    strftime(purchase_month, '%Y-%m')                     AS month,
    orders,
    round(revenue, 2)                                     AS revenue,
    round(LAG(revenue) OVER (ORDER BY purchase_month), 2) AS prev_month_revenue,
    round(100.0 * (revenue - LAG(revenue) OVER (ORDER BY purchase_month))
          / NULLIF(LAG(revenue) OVER (ORDER BY purchase_month), 0), 1)
                                                          AS mom_growth_pct
FROM filled
ORDER BY purchase_month;
