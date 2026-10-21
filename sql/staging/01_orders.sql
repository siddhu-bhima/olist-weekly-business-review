-- staging.orders: typed, one row per order_id, DQ fixes applied.
CREATE OR REPLACE TABLE staging.orders AS
WITH typed AS (
    SELECT
        order_id,
        customer_id,
        lower(trim(order_status))                                 AS order_status,
        CAST(order_purchase_timestamp       AS TIMESTAMP)         AS purchased_at,
        TRY_CAST(order_approved_at          AS TIMESTAMP)         AS approved_at,
        TRY_CAST(order_delivered_carrier_date  AS TIMESTAMP)      AS raw_carrier_at,
        TRY_CAST(order_delivered_customer_date AS TIMESTAMP)      AS delivered_at,
        TRY_CAST(order_estimated_delivery_date AS TIMESTAMP)      AS estimated_at,
        -- keep a single row per order_id if the source ever repeats one
        row_number() OVER (PARTITION BY order_id
                           ORDER BY order_purchase_timestamp DESC) AS rn
    FROM raw.orders
    WHERE order_id IS NOT NULL
)
SELECT
    order_id,
    customer_id,
    order_status,
    purchased_at,
    approved_at,
    -- DQ03 fix: a hand-over before purchase is impossible -> unknown
    CASE WHEN raw_carrier_at < purchased_at THEN NULL ELSE raw_carrier_at END
                                                         AS carrier_at,
    delivered_at,
    estimated_at,
    (raw_carrier_at < purchased_at)                      AS is_carrier_date_invalid,
    -- DQ06 flag
    ((order_status = 'delivered'  AND delivered_at IS NULL) OR
     (order_status <> 'delivered' AND delivered_at IS NOT NULL))
                                                         AS has_status_date_conflict
FROM typed
WHERE rn = 1;
