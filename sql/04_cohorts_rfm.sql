-- ============================================================
-- 05_cohorts.sql
-- Customer cohort retention analysis
-- ============================================================

# 1. Assign each customer to their first-order cohort month 
WITH customer_cohorts AS (
    SELECT
        o.customer_id,
        DATE_TRUNC('month', MIN(CAST(o.order_purchase_timestamp AS TIMESTAMP))) AS cohort_month
    FROM orders o
    WHERE o.order_status = 'delivered'
    GROUP BY o.customer_id
),

# 2. Get all orders per customer with cohort label 
orders_with_cohort AS (
    SELECT
        o.customer_id,
        cc.cohort_month,
        DATE_TRUNC('month', CAST(o.order_purchase_timestamp AS TIMESTAMP)) AS order_month,
        DATEDIFF('month', cc.cohort_month,
            DATE_TRUNC('month', CAST(o.order_purchase_timestamp AS TIMESTAMP))) AS month_number
    FROM orders o
    JOIN customer_cohorts cc ON o.customer_id = cc.customer_id
    WHERE o.order_status = 'delivered'
),

# 3. Cohort size (month 0) 
cohort_sizes AS (
    SELECT
        cohort_month,
        COUNT(DISTINCT customer_id) AS cohort_size
    FROM orders_with_cohort
    WHERE month_number = 0
    GROUP BY cohort_month
)

# 4. Retention rate per cohort per month 
SELECT
    owc.cohort_month,
    owc.month_number,
    COUNT(DISTINCT owc.customer_id)                              AS active_customers,
    cs.cohort_size,
    ROUND(COUNT(DISTINCT owc.customer_id) * 100.0 / cs.cohort_size, 2) AS retention_rate_pct
FROM orders_with_cohort owc
JOIN cohort_sizes cs ON owc.cohort_month = cs.cohort_month
GROUP BY owc.cohort_month, owc.month_number, cs.cohort_size
ORDER BY owc.cohort_month, owc.month_number;


-- ============================================================
-- 06_rfm.sql
-- RFM Scoring entirely in SQL
-- ============================================================

# 1. Compute raw RFM values per customer 
WITH rfm_base AS (
    SELECT
        o.customer_id,
        MAX(CAST(o.order_purchase_timestamp AS TIMESTAMP))           AS last_order_date,
        DATEDIFF('day',
            MAX(CAST(o.order_purchase_timestamp AS TIMESTAMP)),
            (SELECT MAX(CAST(order_purchase_timestamp AS TIMESTAMP)) FROM orders)
        )                                                             AS recency_days,
        COUNT(DISTINCT o.order_id)                                    AS frequency,
        ROUND(SUM(oi.price + oi.freight_value), 2)                   AS monetary
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.order_status = 'delivered'
    GROUP BY o.customer_id
),

# 2. Score each dimension 1–5 using NTILE 
rfm_scores AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        -- Lower recency = better = score 5
        6 - NTILE(5) OVER (ORDER BY recency_days ASC)  AS r_score,
        NTILE(5) OVER (ORDER BY frequency ASC)          AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)           AS m_score
    FROM rfm_base
),

# 3. Combine into RFM segment labels 
rfm_labeled AS (
    SELECT
        customer_id,
        recency_days,
        frequency,
        monetary,
        r_score,
        f_score,
        m_score,
        (r_score + f_score + m_score)   AS rfm_total,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3 AND m_score >= 3 THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2                  THEN 'New Customers'
            WHEN r_score >= 3 AND f_score >= 1 AND m_score >= 3 THEN 'Potential Loyalists'
            WHEN r_score <= 2 AND f_score >= 3 AND m_score >= 3 THEN 'At Risk'
            WHEN r_score <= 2 AND f_score >= 4                  THEN 'Cant Lose Them'
            WHEN r_score <= 2 AND f_score <= 2                  THEN 'Lost'
            ELSE 'Needs Attention'
        END AS segment
    FROM rfm_scores
)

# 4. Segment summary 
SELECT
    segment,
    COUNT(*)                         AS customer_count,
    ROUND(AVG(recency_days), 1)      AS avg_recency_days,
    ROUND(AVG(frequency), 2)         AS avg_frequency,
    ROUND(AVG(monetary), 2)          AS avg_monetary,
    ROUND(SUM(monetary), 2)          AS total_revenue
FROM rfm_labeled
GROUP BY segment
ORDER BY total_revenue DESC;
