-- check_id: DQ02
-- name: Delivered-to-customer date earlier than purchase date
-- max_fail_ratio: 0
-- handling: Hard stop. A delivery before purchase would make delay metrics meaningless.
SELECT
    count(*) FILTER (
        WHERE TRY_CAST(order_delivered_customer_date AS TIMESTAMP)
            < TRY_CAST(order_purchase_timestamp AS TIMESTAMP)) AS failing_rows,
    count(*)                                                    AS total_rows
FROM raw.orders;
