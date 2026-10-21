-- check_id: DQ06
-- name: (Own) Status contradicts delivery date
-- max_fail_ratio: 0.001
-- handling: Flagged (has_status_date_conflict) and excluded from delivery-delay metrics.
-- 'delivered' orders must have a delivery date, and orders with any other
-- status must not have one.
SELECT
    count(*) FILTER (
        WHERE (order_status = 'delivered'  AND order_delivered_customer_date IS NULL)
           OR (order_status <> 'delivered' AND order_delivered_customer_date IS NOT NULL)
    )        AS failing_rows,
    count(*) AS total_rows
FROM raw.orders;
