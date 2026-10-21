-- Weekly Business Review metrics (Part D), one row per purchase week.
--   North Star : on_time_happy_orders
--   Supporting : gmv, on_time_rate_pct
--   Guardrails : low_review_pct, cancel_rate_pct
-- Repeat-purchase rate is a cohort metric and is computed in
-- sql/analysis/q4_repeat_purchase_rate.sql.
WITH base AS (
    SELECT date_trunc('week', purchased_at)::DATE AS week, *
    FROM mart.fct_orders
)
SELECT
    week,
    count(*)                                                    AS orders_placed,
    -- North Star: delivered on/before the promised date AND rated 4-5 stars
    count(*) FILTER (WHERE is_delivered AND NOT is_late
                       AND review_score >= 4)                   AS on_time_happy_orders,
    round(sum(order_value) FILTER (WHERE is_valid_sale), 2)     AS gmv,
    round(100.0 * count(*) FILTER (WHERE is_delivered AND NOT is_late)
          / NULLIF(count(*) FILTER (WHERE is_delivered), 0), 1) AS on_time_rate_pct,
    round(100.0 * count(*) FILTER (WHERE review_score <= 2)
          / NULLIF(count(review_score), 0), 1)                  AS low_review_pct,
    round(100.0 * count(*) FILTER (WHERE NOT is_valid_sale)
          / count(*), 2)                                        AS cancel_rate_pct
FROM base
GROUP BY week
ORDER BY week;
