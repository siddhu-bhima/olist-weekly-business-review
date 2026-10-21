-- check_id: DQ01
-- name: Null or duplicate order_id in orders
-- max_fail_ratio: 0
-- handling: Hard stop. order_id is the grain of the whole mart; no tolerance.
-- Returns: failing_rows, total_rows
WITH counted AS (
    SELECT order_id, count(*) OVER (PARTITION BY order_id) AS n
    FROM raw.orders
)
SELECT
    count(*) FILTER (WHERE order_id IS NULL OR trim(order_id) = '' OR n > 1) AS failing_rows,
    count(*)                                                               AS total_rows
FROM counted;
