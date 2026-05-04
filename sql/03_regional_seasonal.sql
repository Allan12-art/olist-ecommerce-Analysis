-- ============================================================
-- 03_regional.sql
-- Revenue, orders, and customer distribution by Brazilian state
-- ============================================================

# 1. Revenue by State 
SELECT
    c.customer_state                                     AS state,
    COUNT(DISTINCT o.order_id)                           AS total_orders,
    COUNT(DISTINCT o.customer_id)                        AS unique_customers,
    ROUND(SUM(oi.price + oi.freight_value), 2)           AS total_revenue,
    ROUND(AVG(oi.price + oi.freight_value), 2)           AS avg_order_value,
    ROUND(SUM(oi.freight_value) / NULLIF(SUM(oi.price + oi.freight_value), 0) * 100, 2) AS freight_pct
FROM orders o
JOIN order_items oi  ON o.order_id   = oi.order_id
JOIN customers c     ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY total_revenue DESC;


# 2. Top 10 Cities by Revenue 
    c.customer_city                        AS city,
    c.customer_state                       AS state,
    COUNT(DISTINCT o.order_id)             AS orders,
    ROUND(SUM(oi.price), 2)               AS revenue
FROM orders o
JOIN order_items oi ON o.order_id    = oi.order_id
JOIN customers c    ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_city, c.customer_state
ORDER BY revenue DESC
LIMIT 10;


# 3. Freight Cost Burden by Region 
-- High freight = barrier to purchase in remote regions
SELECT
    c.customer_state                                      AS state,
    ROUND(AVG(oi.freight_value), 2)                       AS avg_freight,
    ROUND(AVG(oi.price), 2)                               AS avg_product_price,
    ROUND(AVG(oi.freight_value) / NULLIF(AVG(oi.price), 0) * 100, 2) AS freight_to_price_ratio_pct
FROM orders o
JOIN order_items oi ON o.order_id    = oi.order_id
JOIN customers c    ON o.customer_id = c.customer_id
WHERE o.order_status = 'delivered'
GROUP BY c.customer_state
ORDER BY freight_to_price_ratio_pct DESC;


-- ============================================================
-- 04_seasonal.sql
-- Monthly and seasonal revenue trends
-- ============================================================

# 1. Monthly Revenue Trend 
SELECT
    DATE_TRUNC('month', CAST(o.order_purchase_timestamp AS TIMESTAMP)) AS month,
    COUNT(DISTINCT o.order_id)            AS orders,
    COUNT(DISTINCT o.customer_id)         AS customers,
    ROUND(SUM(oi.price), 2)              AS revenue,
    ROUND(AVG(oi.price), 2)              AS aov
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY 1
ORDER BY 1;


# 2. Revenue by Day of Week 
    DAYNAME(CAST(order_purchase_timestamp AS TIMESTAMP))  AS day_of_week,
    DAYOFWEEK(CAST(order_purchase_timestamp AS TIMESTAMP)) AS day_num,
    COUNT(*)                                               AS orders,
    ROUND(AVG(oi.price), 2)                               AS avg_order_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY 1, 2
ORDER BY 2;


# 3. Revenue by Hour of Day 
SELECT
    EXTRACT(HOUR FROM CAST(order_purchase_timestamp AS TIMESTAMP)) AS hour,
    COUNT(*) AS orders
FROM orders
GROUP BY 1
ORDER BY 1;


# 4. Peak Month per Category 
SELECT
    COALESCE(ct.product_category_name_english, p.product_category_name) AS category,
    MONTHNAME(CAST(o.order_purchase_timestamp AS TIMESTAMP))             AS peak_month,
    ROUND(SUM(oi.price), 2)                                              AS revenue
FROM orders o
JOIN order_items oi ON o.order_id   = oi.order_id
JOIN products p     ON oi.product_id = p.product_id
LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY 1, 2
QUALIFY ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) = 1
ORDER BY revenue DESC
LIMIT 15;
