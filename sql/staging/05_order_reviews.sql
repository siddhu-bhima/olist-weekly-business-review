-- staging.order_reviews: DQ07 fix - exactly one review per order
-- (the most recently answered one, i.e. the customer's final opinion).
CREATE OR REPLACE TABLE staging.order_reviews AS
WITH typed AS (
    SELECT
        review_id,
        order_id,
        CAST(review_score AS INTEGER)               AS review_score,
        TRY_CAST(review_creation_date    AS TIMESTAMP) AS review_created_at,
        TRY_CAST(review_answer_timestamp AS TIMESTAMP) AS review_answered_at,
        (review_comment_message IS NOT NULL
         AND trim(review_comment_message) <> '')    AS has_comment
    FROM raw.order_reviews
    WHERE TRY_CAST(review_score AS INTEGER) BETWEEN 1 AND 5
)
SELECT * EXCLUDE (rn)
FROM (
    SELECT *, row_number() OVER (PARTITION BY order_id
              ORDER BY review_answered_at DESC NULLS LAST,
                       review_created_at  DESC, review_id) AS rn
    FROM typed
)
WHERE rn = 1;
