-- Q3. 7-day rolling average of daily order count.
-- A calendar spine is generated first so days with zero orders count as 0;
-- otherwise "7 rows" could cover more than 7 calendar days.
-- All orders placed are counted (order intake), whatever their status.
WITH bounds AS (
    SELECT min(purchase_date) AS d0, max(purchase_date) AS d1 FROM mart.fct_orders
),
calendar AS (
    SELECT CAST(d AS DATE) AS day
    FROM bounds, generate_series(d0, d1, INTERVAL 1 DAY) AS t(d)
),
daily AS (
    SELECT purchase_date AS day, count(*) AS orders
    FROM mart.fct_orders
    GROUP BY purchase_date
)
SELECT
    c.day,
    coalesce(d.orders, 0) AS orders,
    CASE WHEN row_number() OVER (ORDER BY c.day) >= 7 THEN
        round(avg(coalesce(d.orders, 0)) OVER (
                  ORDER BY c.day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2)
    END                   AS rolling_7d_avg_orders   -- NULL until 7 days exist
FROM calendar c
LEFT JOIN daily d USING (day)
ORDER BY c.day;
