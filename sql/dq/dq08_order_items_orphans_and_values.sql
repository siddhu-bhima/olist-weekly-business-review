-- check_id: DQ08
-- name: (Own) Order items with no parent order or invalid price
-- max_fail_ratio: 0
-- handling: Hard stop. Orphan or zero-price items would corrupt revenue.
SELECT
    count(*) FILTER (
        WHERE o.order_id IS NULL
           OR TRY_CAST(i.price AS DOUBLE) IS NULL OR CAST(i.price AS DOUBLE) <= 0
           OR TRY_CAST(i.freight_value AS DOUBLE) < 0) AS failing_rows,
    count(*)                                            AS total_rows
FROM raw.order_items i
LEFT JOIN raw.orders o ON o.order_id = i.order_id;
