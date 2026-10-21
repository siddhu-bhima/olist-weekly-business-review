-- staging.order_payments: one row per (order_id, payment_sequential).
CREATE OR REPLACE TABLE staging.order_payments AS
SELECT DISTINCT
    order_id,
    CAST(payment_sequential   AS INTEGER)      AS payment_sequential,
    lower(trim(payment_type))                  AS payment_type,
    CAST(payment_installments AS INTEGER)      AS payment_installments,
    CAST(payment_value        AS DECIMAL(12,2)) AS payment_value
FROM raw.order_payments;
