-- mart.fct_order_items: one row per order line, enriched with category and
-- the buyer's state. Used for category/state revenue (Part C Q2).
CREATE OR REPLACE TABLE mart.fct_order_items AS
SELECT
    i.order_id,
    i.order_item_id,
    i.product_id,
    i.seller_id,
    p.category,
    s.seller_state,
    o.customer_state,
    o.purchase_month,
    o.is_valid_sale,
    i.price,
    i.freight_value,
    i.item_total
FROM staging.order_items i
JOIN mart.fct_orders     o ON o.order_id   = i.order_id
LEFT JOIN staging.products p ON p.product_id = i.product_id
LEFT JOIN staging.sellers  s ON s.seller_id  = i.seller_id;
