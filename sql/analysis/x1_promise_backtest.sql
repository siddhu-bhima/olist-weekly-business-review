-- Extra (supports the VP memo): back-test of a route-level delivery promise.
-- Route = first seller's state -> customer state.
-- New promise = max(current promise, P90 of actual delivery days on the same
-- route, using ONLY orders delivered in the 28 days before this purchase,
-- and only when the route has >= 20 such orders). No look-ahead.
WITH od AS (
    SELECT f.order_id, f.customer_state, f.purchased_at, f.delivered_at,
           f.delivery_days, f.promised_days, f.is_late, f.review_score,
           f.purchase_month, s.seller_state
    FROM mart.fct_orders f
    JOIN (SELECT order_id, arg_min(seller_state, order_item_id) AS seller_state
          FROM mart.fct_order_items GROUP BY order_id) s USING (order_id)
    WHERE f.is_delivered AND NOT f.has_status_date_conflict
),
route_p90 AS (
    SELECT a.order_id,
           quantile_cont(b.delivery_days, 0.9) AS p90,
           count(b.order_id)                   AS n_hist
    FROM od a
    JOIN od b
      ON  b.seller_state   = a.seller_state
      AND b.customer_state = a.customer_state
      AND b.delivered_at  <  a.purchased_at
      AND b.delivered_at >=  a.purchased_at - INTERVAL 28 DAY
    GROUP BY a.order_id
),
sim AS (
    SELECT od.*,
           greatest(od.promised_days,
                    coalesce(CASE WHEN r.n_hist >= 20 THEN ceil(r.p90) END, 0)) AS new_promise
    FROM od LEFT JOIN route_p90 r USING (order_id)
    WHERE od.purchase_month BETWEEN DATE '2017-03-01' AND DATE '2018-08-01'
)
SELECT
    count(*)                                                     AS orders,
    count(*) FILTER (WHERE is_late)                              AS late_now,
    count(*) FILTER (WHERE delivery_days > new_promise)          AS late_with_new_promise,
    round(100.0 * count(*) FILTER (WHERE is_late) / count(*), 1) AS late_rate_now_pct,
    round(100.0 * count(*) FILTER (WHERE delivery_days > new_promise) / count(*), 1)
                                                                 AS late_rate_new_pct,
    round(100.0 * avg(CASE WHEN new_promise > promised_days THEN 1 ELSE 0 END), 1)
                                                                 AS pct_orders_promise_extended,
    round(avg(new_promise - promised_days)
          FILTER (WHERE new_promise > promised_days), 1)         AS avg_extra_days_when_extended,
    count(*) FILTER (WHERE is_late AND review_score <= 2)        AS late_low_reviews_now,
    count(*) FILTER (WHERE delivery_days > new_promise AND review_score <= 2)
                                                                 AS late_low_reviews_new
FROM sim;
