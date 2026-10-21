-- Q5. Average delivery delay vs the estimated date, and its link to review score.
-- delay_days = delivered date - estimated date (negative = early).
-- Delivered orders only, excluding DQ06 status/date conflicts.
WITH delivered AS (
    SELECT delivery_delay_days AS delay, review_score
    FROM mart.fct_orders
    WHERE is_delivered AND NOT has_status_date_conflict
      AND review_score IS NOT NULL
),
bucketed AS (
    SELECT *,
        CASE WHEN delay <= -15 THEN '1. 15+ days early'
             WHEN delay <=  -8 THEN '2. 8-14 days early'
             WHEN delay <=   0 THEN '3. 0-7 days early'
             WHEN delay <=   3 THEN '4. 1-3 days late'
             WHEN delay <=   7 THEN '5. 4-7 days late'
             WHEN delay <=  14 THEN '6. 8-14 days late'
             ELSE                   '7. 15+ days late' END AS delay_bucket
    FROM delivered
),
overall AS (
    SELECT round(avg(delay), 2)                  AS overall_avg_delay_days,
           round(corr(delay, review_score), 3)   AS pearson_corr_delay_vs_score
    FROM delivered
)
SELECT
    b.delay_bucket,
    count(*)                                                  AS orders,
    round(100.0 * count(*) / sum(count(*)) OVER (), 1)        AS pct_of_orders,
    round(avg(b.delay), 1)                                    AS avg_delay_days,
    round(avg(b.review_score), 2)                             AS avg_review_score,
    round(100.0 * avg(CASE WHEN b.review_score <= 2 THEN 1 ELSE 0 END), 1)
                                                              AS pct_1_2_star,
    any_value(o.overall_avg_delay_days)                       AS overall_avg_delay_days,
    any_value(o.pearson_corr_delay_vs_score)                  AS corr_delay_vs_score
FROM bucketed b CROSS JOIN overall o
GROUP BY b.delay_bucket
ORDER BY b.delay_bucket;
