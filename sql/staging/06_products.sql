-- staging.products: English category names; missing category -> 'unknown'.
CREATE OR REPLACE TABLE staging.products AS
SELECT
    p.product_id,
    coalesce(t.product_category_name_english,
             p.product_category_name, 'unknown') AS category,
    TRY_CAST(p.product_weight_g AS DOUBLE)       AS weight_g
FROM raw.products p
LEFT JOIN raw.category_translation t
       ON t.product_category_name = p.product_category_name;
