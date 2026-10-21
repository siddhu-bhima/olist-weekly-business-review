-- check_id: DQ04
-- name: Payment total differs from item price + freight (> R$0.01)
-- max_fail_ratio: 0.01
-- handling: Flagged (is_payment_mismatch) and kept. Revenue uses item price + freight.
-- Items and payments are aggregated to order level SEPARATELY before the
-- join; joining the raw tables directly would multiply rows and double count.
WITH items AS (
    SELECT order_id,
           sum(CAST(price AS DECIMAL(12,2)) + CAST(freight_value AS DECIMAL(12,2))) AS item_total
    FROM raw.order_items
    GROUP BY order_id
),
payments AS (
    SELECT order_id, sum(CAST(payment_value AS DECIMAL(12,2))) AS paid_total
    FROM raw.order_payments
    GROUP BY order_id
)
SELECT
    count(*) FILTER (WHERE abs(i.item_total - p.paid_total) > 0.01) AS failing_rows,
    count(*)                                                        AS total_rows
FROM items i
JOIN payments p USING (order_id);
