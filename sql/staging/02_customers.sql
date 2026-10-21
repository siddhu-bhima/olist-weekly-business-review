-- staging.customers: customer_id is per-ORDER; customer_unique_id is the person.
CREATE OR REPLACE TABLE staging.customers AS
SELECT DISTINCT
    customer_id,
    customer_unique_id,
    customer_zip_code_prefix,
    lower(trim(customer_city))  AS customer_city,
    upper(trim(customer_state)) AS customer_state
FROM raw.customers
WHERE customer_id IS NOT NULL;
