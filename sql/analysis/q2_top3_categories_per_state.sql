-- Q2. Top 3 product categories per customer state by revenue.
-- Revenue at item level = price + freight. fct_order_items is one row per
-- order line, so summing it does not double count. DENSE_RANK keeps ties.
WITH cat_state AS (
    SELECT
        customer_state,
        category,
        sum(item_total)          AS revenue,
        count(DISTINCT order_id) AS orders
    FROM mart.fct_order_items
    WHERE is_valid_sale
    GROUP BY customer_state, category
),
ranked AS (
    SELECT *,
           DENSE_RANK() OVER (PARTITION BY customer_state
                              ORDER BY revenue DESC) AS rnk
    FROM cat_state
)
SELECT customer_state, rnk AS rank, category, round(revenue, 2) AS revenue, orders
FROM ranked
WHERE rnk <= 3
ORDER BY customer_state, rnk;
