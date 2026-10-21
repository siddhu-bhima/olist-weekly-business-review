-- staging.order_items: one row per (order_id, order_item_id).
CREATE OR REPLACE TABLE staging.order_items AS
SELECT DISTINCT
    order_id,
    CAST(order_item_id AS INTEGER)           AS order_item_id,
    product_id,
    seller_id,
    TRY_CAST(shipping_limit_date AS TIMESTAMP) AS shipping_limit_at,
    CAST(price         AS DECIMAL(12,2))     AS price,
    CAST(freight_value AS DECIMAL(12,2))     AS freight_value,
    CAST(price AS DECIMAL(12,2)) + CAST(freight_value AS DECIMAL(12,2)) AS item_total
FROM raw.order_items;
