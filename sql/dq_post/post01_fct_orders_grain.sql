-- check_id: POST01
-- name: mart.fct_orders has exactly one row per staged order
-- max_fail_ratio: 0
-- handling: Hard stop. A fan-out join here would double count revenue.
SELECT
    (SELECT count(*) - count(DISTINCT order_id) FROM mart.fct_orders)
  + abs((SELECT count(*) FROM mart.fct_orders) - (SELECT count(*) FROM staging.orders))
                                              AS failing_rows,
    (SELECT count(*) FROM staging.orders)     AS total_rows;
