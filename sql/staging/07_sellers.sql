CREATE OR REPLACE TABLE staging.sellers AS
SELECT DISTINCT
    seller_id,
    seller_zip_code_prefix,
    lower(trim(seller_city))  AS seller_city,
    upper(trim(seller_state)) AS seller_state
FROM raw.sellers;
