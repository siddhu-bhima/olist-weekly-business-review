-- check_id: DQ07
-- name: (Own) Order has more than one review
-- max_fail_ratio: 0.01
-- handling: Fixed. Staging keeps only the latest answered review per order.
SELECT
    (SELECT count(*) FROM (SELECT order_id FROM raw.order_reviews
                           GROUP BY order_id HAVING count(*) > 1)) AS failing_rows,
    (SELECT count(DISTINCT order_id) FROM raw.order_reviews)        AS total_rows;
