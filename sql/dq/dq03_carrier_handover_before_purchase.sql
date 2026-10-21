-- check_id: DQ03
-- name: Carrier hand-over date earlier than purchase date
-- max_fail_ratio: 0.01
-- handling: Fixed. carrier date set to NULL in staging and flagged (is_carrier_date_invalid).
SELECT
    count(*) FILTER (
        WHERE TRY_CAST(order_delivered_carrier_date AS TIMESTAMP)
            < TRY_CAST(order_purchase_timestamp AS TIMESTAMP)) AS failing_rows,
    count(*)                                                    AS total_rows
FROM raw.orders;
