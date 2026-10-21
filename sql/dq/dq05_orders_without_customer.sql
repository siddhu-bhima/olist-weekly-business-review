-- check_id: DQ05
-- name: Orders with no matching customer record
-- max_fail_ratio: 0
-- handling: Hard stop. An orphan order cannot be attributed to a state or customer.
SELECT
    count(*) FILTER (WHERE c.customer_id IS NULL) AS failing_rows,
    count(*)                                      AS total_rows
FROM raw.orders o
LEFT JOIN raw.customers c ON c.customer_id = o.customer_id;
