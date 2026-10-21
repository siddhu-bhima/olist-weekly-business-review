-- check_id: POST03
-- name: Staged reviews are unique per order and scores in 1-5
-- max_fail_ratio: 0
-- handling: Hard stop. Confirms the DQ07 de-duplication worked.
SELECT
    (SELECT count(*) - count(DISTINCT order_id) FROM staging.order_reviews)
  + (SELECT count(*) FROM staging.order_reviews WHERE review_score NOT BETWEEN 1 AND 5)
                                                   AS failing_rows,
    (SELECT count(*) FROM staging.order_reviews)   AS total_rows;
