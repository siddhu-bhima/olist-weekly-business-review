-- Q4. Repeat-purchase rate.
-- customer_id is created fresh for EVERY order, so it can never repeat.
-- The real person is customer_unique_id. Valid sales only.
WITH per_customer AS (
    SELECT customer_unique_id, count(DISTINCT order_id) AS n_orders
    FROM mart.fct_orders
    WHERE is_valid_sale
    GROUP BY customer_unique_id
),
naive AS (   -- shown only to prove why customer_id is the wrong key
    SELECT count(*) FILTER (WHERE n > 1) AS repeaters, count(*) AS customers
    FROM (SELECT customer_id, count(*) AS n
          FROM mart.fct_orders WHERE is_valid_sale GROUP BY customer_id)
)
SELECT
    count(*)                                         AS customers,
    count(*) FILTER (WHERE n_orders >= 2)            AS repeat_customers,
    round(100.0 * count(*) FILTER (WHERE n_orders >= 2) / count(*), 2)
                                                     AS repeat_rate_pct,
    round(avg(n_orders), 3)                          AS orders_per_customer,
    (SELECT round(100.0 * repeaters / customers, 2) FROM naive)
                                                     AS wrong_rate_using_customer_id_pct
FROM per_customer;
