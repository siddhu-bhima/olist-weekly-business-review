-- mart.fct_orders: ONE ROW PER ORDER - totals, delivery dates, review score.
-- Items, payments and reviews are each reduced to order level in their own
-- CTE first, so the final joins are 1:1 and nothing is double counted.
CREATE OR REPLACE TABLE mart.fct_orders AS
WITH items AS (
    SELECT order_id,
           count(*)              AS item_count,
           count(DISTINCT seller_id) AS seller_count,
           sum(price)            AS items_value,
           sum(freight_value)    AS freight_value,
           sum(item_total)       AS order_value
    FROM staging.order_items
    GROUP BY order_id
),
payments AS (
    SELECT order_id,
           sum(payment_value)    AS payment_total,
           count(*)              AS payment_count,
           arg_max(payment_type, payment_value) AS main_payment_type
    FROM staging.order_payments
    GROUP BY order_id
)
SELECT
    o.order_id,
    o.customer_id,
    c.customer_unique_id,
    c.customer_state,
    o.order_status,
    o.purchased_at,
    CAST(o.purchased_at AS DATE)                           AS purchase_date,
    date_trunc('month', o.purchased_at)::DATE              AS purchase_month,
    o.approved_at,
    o.carrier_at,
    o.delivered_at,
    o.estimated_at,
    coalesce(i.item_count, 0)                              AS item_count,
    coalesce(i.seller_count, 0)                            AS seller_count,
    coalesce(i.items_value, 0)                             AS items_value,
    coalesce(i.freight_value, 0)                           AS freight_value,
    coalesce(i.order_value, 0)                             AS order_value,      -- GMV of the order
    p.payment_total,
    p.main_payment_type,
    r.review_score,
    r.has_comment                                          AS review_has_comment,
    -- delivery timing (days); NULL when not validly delivered
    CASE WHEN o.order_status = 'delivered' AND o.delivered_at IS NOT NULL
         THEN date_diff('day', CAST(o.estimated_at AS DATE),
                               CAST(o.delivered_at AS DATE)) END AS delivery_delay_days,
    CASE WHEN o.order_status = 'delivered' AND o.delivered_at IS NOT NULL
         THEN date_diff('day', CAST(o.purchased_at AS DATE),
                               CAST(o.delivered_at AS DATE)) END AS delivery_days,
    date_diff('day', CAST(o.purchased_at AS DATE),
                     CAST(o.estimated_at AS DATE))         AS promised_days,
    -- flags
    (o.order_status = 'delivered' AND o.delivered_at IS NOT NULL) AS is_delivered,
    (o.order_status = 'delivered' AND o.delivered_at IS NOT NULL
        AND CAST(o.delivered_at AS DATE) > CAST(o.estimated_at AS DATE)) AS is_late,
    (o.order_status NOT IN ('canceled', 'unavailable'))    AS is_valid_sale,
    (p.payment_total IS NOT NULL AND i.order_value IS NOT NULL
        AND abs(p.payment_total - i.order_value) > 0.01)   AS is_payment_mismatch,
    o.is_carrier_date_invalid,
    o.has_status_date_conflict
FROM staging.orders o
JOIN staging.customers c  ON c.customer_id = o.customer_id
LEFT JOIN items i         ON i.order_id    = o.order_id
LEFT JOIN payments p      ON p.order_id    = o.order_id
LEFT JOIN staging.order_reviews r ON r.order_id = o.order_id;
