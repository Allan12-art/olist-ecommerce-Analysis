-- ============================================================
-- 02_kpis.sql
-- Core business KPIs: Revenue, AOV, Order Volume, Top Categories
-- ============================================================

# 1. Overall Revenue KPIs 
SELECT
    COUNT(DISTINCT o.order_id)                          AS total_orders,
    COUNT(DISTINCT o.customer_id)                       AS total_customers,
    ROUND(SUM(oi.price + oi.freight_value), 2)          AS total_revenue,
    ROUND(AVG(oi.price + oi.freight_value), 2)          AS avg_order_value,
    ROUND(SUM(oi.price), 2)                             AS product_revenue,
    ROUND(SUM(oi.freight_value), 2)                     AS freight_revenue
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered';


# 2. Revenue by Product Category (Top 15)
SELECT
    COALESCE(ct.product_category_name_english, p.product_category_name, 'Unknown') AS category,
    COUNT(DISTINCT oi.order_id)                          AS orders,
    ROUND(SUM(oi.price), 2)                              AS revenue,
    ROUND(AVG(oi.price), 2)                              AS avg_price,
    ROUND(SUM(oi.price) * 100.0 / SUM(SUM(oi.price)) OVER (), 2) AS revenue_pct
FROM order_items oi
JOIN products p       ON oi.product_id = p.product_id
JOIN orders o         ON oi.order_id   = o.order_id
LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
WHERE o.order_status = 'delivered'
GROUP BY 1
ORDER BY revenue DESC
LIMIT 15;


# 3. Average Order Value by Payment Type
SELECT
    payment_type,
    COUNT(DISTINCT order_id)           AS num_orders,
    ROUND(AVG(payment_value), 2)       AS avg_payment,
    ROUND(SUM(payment_value), 2)       AS total_payment
FROM order_payments
GROUP BY payment_type
ORDER BY total_payment DESC;


# 4. Order Status Breakdown 
SELECT
    order_status,
    COUNT(*) AS order_count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS pct
FROM orders
GROUP BY order_status
ORDER BY order_count DESC;


# 5. Revenue with Window Functions — Running Total 
SELECT
    DATE_TRUNC('month', CAST(o.order_purchase_timestamp AS TIMESTAMP)) AS month,
    ROUND(SUM(oi.price), 2)                                             AS monthly_revenue,
    ROUND(SUM(SUM(oi.price)) OVER (ORDER BY DATE_TRUNC('month', CAST(o.order_purchase_timestamp AS TIMESTAMP))), 2) AS running_total,
    ROUND(AVG(SUM(oi.price)) OVER (ORDER BY DATE_TRUNC('month', CAST(o.order_purchase_timestamp AS TIMESTAMP)) ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS rolling_3m_avg
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
WHERE o.order_status = 'delivered'
GROUP BY 1
ORDER BY 1;
