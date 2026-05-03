"""
src/05_dashboard.py
───────────────────
Interactive Streamlit dashboard for the Olist E-Commerce analysis.
Pulls live data from DuckDB on every filter change.

Usage:
    streamlit run src/05_dashboard.py
"""

import streamlit as st
import duckdb
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

DB_PATH = "ecommerce.duckdb"

#  Page config 
st.set_page_config(
    page_title="Olist E-Commerce Intelligence",
    layout="wide",
    initial_sidebar_state="expanded",
)

#  Theme colours 
COLOR_PRIMARY  = "#00d4ff"
COLOR_ACCENT   = "#7c3aed"
COLOR_SUCCESS  = "#10b981"
COLOR_WARNING  = "#f59e0b"
PLOTLY_THEME   = "plotly_dark"

#  DB connection (cached) 
@st.cache_resource
def get_con():
    if not os.path.exists(DB_PATH):
        st.error(f"Database not found: {DB_PATH}\n\nRun `python src/01_setup_db.py` first.")
        st.stop()
    return duckdb.connect(DB_PATH, read_only=True)


@st.cache_data(ttl=300)
def run_query(sql: str) -> pd.DataFrame:
    con = get_con()
    return con.execute(sql).fetchdf()


#  Sidebar filters
def render_sidebar():
    st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/thumb/0/09/Flag_of_Brazil.svg/320px-Flag_of_Brazil.svg.png", width=150)
    st.sidebar.title("Olist Dashboard")
    st.sidebar.markdown("---")

    # Date range
    dates = run_query("""
        SELECT
            MIN(CAST(order_purchase_timestamp AS DATE)) AS min_d,
            MAX(CAST(order_purchase_timestamp AS DATE)) AS max_d
        FROM orders
    """)
    min_d = pd.to_datetime(dates["min_d"][0])
    max_d = pd.to_datetime(dates["max_d"][0])

    start, end = st.sidebar.date_input(
        "Date Range",
        value=(min_d, max_d),
        min_value=min_d,
        max_value=max_d,
    )

    # State filter
    states = run_query("SELECT DISTINCT customer_state FROM customers ORDER BY 1")
    selected_states = st.sidebar.multiselect(
        "Filter by State",
        options=["All"] + states["customer_state"].tolist(),
        default=["All"]
    )
    if "All" in selected_states or not selected_states:
        state_filter = ""
    else:
        state_list = "', '".join(selected_states)
        state_filter = f"AND c.customer_state IN ('{state_list}')"

    st.sidebar.markdown("---")
    
    return str(start), str(end), state_filter


#  KPI Cards 
def render_kpis(start, end, state_filter):
    kpis = run_query(f"""
        SELECT
            COUNT(DISTINCT o.order_id)                         AS orders,
            COUNT(DISTINCT o.customer_id)                      AS customers,
            ROUND(SUM(oi.price + oi.freight_value), 2)         AS revenue,
            ROUND(AVG(oi.price + oi.freight_value), 2)         AS aov,
            ROUND(AVG(r.review_score), 2)                      AS avg_rating
        FROM orders o
        JOIN order_items oi   ON o.order_id    = oi.order_id
        JOIN customers c      ON o.customer_id = c.customer_id
        LEFT JOIN order_reviews r ON o.order_id = r.order_id
        WHERE o.order_status = 'delivered'
          AND CAST(o.order_purchase_timestamp AS DATE) BETWEEN '{start}' AND '{end}'
          {state_filter}
    """)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Orders",    f"{int(kpis['orders'][0]):,}")
    c2.metric("Customers",       f"{int(kpis['customers'][0]):,}")
    c3.metric("Revenue",         f"R${kpis['revenue'][0]:,.0f}")
    c4.metric("Avg Order Value", f"R${kpis['aov'][0]:,.2f}")
    c5.metric("Avg Rating",      f"{kpis['avg_rating'][0]:.2f}")


#  Monthly Revenue Chart 
def render_revenue_chart(start, end, state_filter):
    df = run_query(f"""
        SELECT
            DATE_TRUNC('month', CAST(o.order_purchase_timestamp AS TIMESTAMP)) AS month,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue,
            COUNT(DISTINCT o.order_id)                  AS orders
        FROM orders o
        JOIN order_items oi ON o.order_id    = oi.order_id
        JOIN customers c    ON o.customer_id = c.customer_id
        WHERE o.order_status = 'delivered'
          AND CAST(o.order_purchase_timestamp AS DATE) BETWEEN '{start}' AND '{end}'
          {state_filter}
        GROUP BY 1 ORDER BY 1
    """)
    df["month"] = pd.to_datetime(df["month"])

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Scatter(
        x=df["month"], y=df["revenue"],
        fill="tozeroy", name="Revenue",
        line=dict(color=COLOR_PRIMARY, width=2),
        fillcolor=f"rgba(0,212,255,0.15)"
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=df["month"], y=df["orders"],
        name="Orders", marker_color=COLOR_ACCENT, opacity=0.5
    ), secondary_y=True)

    fig.update_layout(
        title="Monthly Revenue & Orders",
        template=PLOTLY_THEME,
        hovermode="x unified",
        legend=dict(orientation="h", y=1.1)
    )
    fig.update_yaxes(title_text="Revenue (BRL)", tickprefix="R$", secondary_y=False)
    fig.update_yaxes(title_text="Orders", secondary_y=True)
    st.plotly_chart(fig, use_container_width=True)


#  Top Categories 
def render_categories(start, end, state_filter):
    df = run_query(f"""
        SELECT
            COALESCE(ct.product_category_name_english,
                     p.product_category_name, 'Unknown') AS category,
            ROUND(SUM(oi.price), 2)  AS revenue,
            COUNT(DISTINCT oi.order_id) AS orders
        FROM order_items oi
        JOIN products p  ON oi.product_id = p.product_id
        JOIN orders o    ON oi.order_id   = o.order_id
        JOIN customers c ON o.customer_id = c.customer_id
        LEFT JOIN category_translation ct ON p.product_category_name = ct.product_category_name
        WHERE o.order_status = 'delivered'
          AND CAST(o.order_purchase_timestamp AS DATE) BETWEEN '{start}' AND '{end}'
          {state_filter}
        GROUP BY 1 ORDER BY revenue DESC LIMIT 15
    """)

    fig = px.bar(
        df, x="revenue", y="category", orientation="h",
        color="revenue", color_continuous_scale="Plasma",
        title="Top 15 Categories by Revenue",
        template=PLOTLY_THEME
    )
    fig.update_layout(yaxis=dict(categoryorder="total ascending"),
                      coloraxis_showscale=False)
    fig.update_xaxes(tickprefix="R$")
    st.plotly_chart(fig, use_container_width=True)


#  Map: Revenue by State 
def render_state_map(start, end, state_filter):
    df = run_query(f"""
        SELECT
            c.customer_state AS state,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue,
            COUNT(DISTINCT o.order_id) AS orders
        FROM orders o
        JOIN order_items oi ON o.order_id    = oi.order_id
        JOIN customers c    ON o.customer_id = c.customer_id
        WHERE o.order_status = 'delivered'
          AND CAST(o.order_purchase_timestamp AS DATE) BETWEEN '{start}' AND '{end}'
          {state_filter}
        GROUP BY 1 ORDER BY revenue DESC
    """)

    fig = px.choropleth(
        df,
        locations="state",
        locationmode="geojson-id",
        color="revenue",
        hover_data=["orders"],
        color_continuous_scale="Viridis",
        title="Revenue by State",
        template=PLOTLY_THEME,
        scope="south america",
    )
    # Fallback: bar chart if choropleth data doesn't resolve
    fig2 = px.bar(df.head(10), x="state", y="revenue",
                  color="revenue", color_continuous_scale="Viridis",
                  title="Revenue by State (Top 10)",
                  template=PLOTLY_THEME)
    fig2.update_yaxes(tickprefix="R$")
    st.plotly_chart(fig2, use_container_width=True)


#  RFM Segments 
def render_rfm(start, end):
    try:
        df = run_query("""
            SELECT segment,
                   COUNT(*) AS customers,
                   ROUND(AVG(monetary), 2) AS avg_value,
                   ROUND(SUM(monetary), 2) AS total_revenue
            FROM rfm_segments
            GROUP BY segment
            ORDER BY total_revenue DESC
        """)

        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(df, names="segment", values="customers",
                         title="Customers by RFM Segment",
                         template=PLOTLY_THEME, hole=0.4)
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            fig = px.bar(df, x="segment", y="total_revenue",
                         color="segment",
                         title="Revenue by RFM Segment",
                         template=PLOTLY_THEME)
            fig.update_yaxes(tickprefix="R$")
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

    except Exception:
        st.info("Run `python src/03_rfm.py` to generate RFM segments.")


#  Forecast
def render_forecast():
    try:
        df_actual = run_query("""
            SELECT
                CAST(DATE_TRUNC('day', CAST(order_purchase_timestamp AS TIMESTAMP)) AS DATE) AS ds,
                ROUND(SUM(oi.price + oi.freight_value), 2) AS revenue
            FROM orders o
            JOIN order_items oi ON o.order_id = oi.order_id
            WHERE o.order_status = 'delivered'
            GROUP BY 1 ORDER BY 1
        """)
        df_fc = run_query("SELECT * FROM revenue_forecast ORDER BY ds")
        df_fc["ds"] = pd.to_datetime(df_fc["ds"])
        df_actual["ds"] = pd.to_datetime(df_actual["ds"])

        max_actual = df_actual["ds"].max()
        future = df_fc[df_fc["ds"] > max_actual]

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_actual["ds"], y=df_actual["revenue"],
                                 name="Actual", line=dict(color=COLOR_PRIMARY)))
        fig.add_trace(go.Scatter(x=future["ds"], y=future["yhat"],
                                 name="Forecast", line=dict(color=COLOR_WARNING, width=2.5)))
        fig.add_trace(go.Scatter(
            x=pd.concat([future["ds"], future["ds"][::-1]]),
            y=pd.concat([future["yhat_upper"], future["yhat_lower"][::-1]]),
            fill="toself", fillcolor="rgba(245,158,11,0.15)",
            line=dict(color="rgba(0,0,0,0)"), name="Confidence Band"
        ))
        fig.update_layout(title="Revenue Forecast (Next 90 Days)",
                          template=PLOTLY_THEME, hovermode="x unified")
        fig.update_yaxes(tickprefix="R$")
        st.plotly_chart(fig, use_container_width=True)

    except Exception:
        st.info("Run `python src/04_forecasting.py` to generate forecast.")


#  Main layout 
def main():
    st.title("Olist E-Commerce Sales Intelligence")
    st.markdown("---")

    start, end, state_filter = render_sidebar()

    # KPI row
    render_kpis(start, end, state_filter)
    st.markdown("---")

    # Revenue trend
    render_revenue_chart(start, end, state_filter)

    # Categories + State
    col1, col2 = st.columns(2)
    with col1:
        render_categories(start, end, state_filter)
    with col2:
        render_state_map(start, end, state_filter)

    st.markdown("---")
    st.subheader("Customer Segmentation (RFM)")
    render_rfm(start, end)

    st.markdown("---")
    st.subheader("Revenue Forecasting")
    render_forecast()

    st.markdown("---")
    st.caption("Built with Python · DuckDB · Streamlit · Plotly · Scikit-learn | Data: Olist via Kaggle")


if __name__ == "__main__":
    main()