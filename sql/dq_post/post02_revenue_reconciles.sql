-- check_id: POST02
-- name: Mart revenue reconciles with staged order items
-- max_fail_ratio: 0
-- handling: Hard stop. Orders whose mart order_value differs from the sum of their items.
WITH item_sum AS (
    SELECT order_id, sum(item_total) AS v FROM staging.order_items GROUP BY order_id
)
SELECT
    count(*) FILTER (WHERE abs(f.order_value - coalesce(s.v, 0)) > 0.001) AS failing_rows,
    count(*)                                                              AS total_rows
FROM mart.fct_orders f
LEFT JOIN item_sum s USING (order_id);
