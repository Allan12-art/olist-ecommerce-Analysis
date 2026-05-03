"""
src/04_forecasting.py
─────────────────────
Revenue time-series forecasting using Facebook Prophet.
Forecasts 90 days into the future and saves chart.

Usage:
    python src/04_forecasting.py
"""

import duckdb
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import os
import warnings
warnings.filterwarnings("ignore")

DB_PATH = "ecommerce.duckdb"
OUT_DIR = "outputs"
os.makedirs(OUT_DIR, exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": "#0f1117", "axes.facecolor": "#0f1117",
    "axes.edgecolor": "#444",      "axes.labelcolor": "#ccc",
    "text.color": "#eee",          "xtick.color": "#aaa",
    "ytick.color": "#aaa",         "grid.color": "#333",
    "grid.linestyle": "--",        "grid.alpha": 0.5,
    "font.family": "monospace",
})


def get_daily_revenue(con) -> pd.DataFrame:
    """Pull daily revenue aggregation from DuckDB."""
    df = con.execute("""
        SELECT
            CAST(DATE_TRUNC('day', CAST(order_purchase_timestamp AS TIMESTAMP)) AS DATE) AS ds,
            ROUND(SUM(oi.price + oi.freight_value), 2) AS y
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_status = 'delivered'
        GROUP BY 1
        ORDER BY 1
    """).fetchdf()
    df["ds"] = pd.to_datetime(df["ds"])
    return df


def run_prophet_forecast(df: pd.DataFrame, periods: int = 90):
    """Fit Prophet model and forecast `periods` days ahead."""
    try:
        from prophet import Prophet
    except ImportError:
        print("  Prophet not installed. Run: pip install prophet")
        print("  Falling back to simple moving-average forecast...")
        return run_moving_average_forecast(df, periods)

    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        changepoint_prior_scale=0.05,
        seasonality_prior_scale=10.0,
    )
    model.fit(df)

    future = model.make_future_dataframe(periods=periods)
    forecast = model.predict(future)

    return model, forecast


def run_moving_average_forecast(df: pd.DataFrame, periods: int = 90):
    """Fallback: simple 30-day rolling average forecast."""
    last_date = df["ds"].max()
    future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=periods)
    rolling_avg = df["y"].rolling(30).mean().iloc[-1]

    forecast_df = pd.DataFrame({
        "ds": future_dates,
        "yhat": rolling_avg,
        "yhat_lower": rolling_avg * 0.8,
        "yhat_upper": rolling_avg * 1.2,
    })
    full = pd.concat([df.rename(columns={"y": "yhat"}), forecast_df], ignore_index=True)
    return None, full


def plot_forecast(df: pd.DataFrame, forecast, model=None):
    """Plot actual revenue + forecast with confidence interval."""
    fig, ax = plt.subplots(figsize=(16, 6))

    # Historical
    ax.plot(df["ds"], df["y"],
            color="#00d4ff", lw=1.5, alpha=0.9, label="Actual Revenue", zorder=3)

    # Forecast
    future_mask = forecast["ds"] > df["ds"].max()
    hist_mask   = ~future_mask

    ax.plot(forecast.loc[hist_mask, "ds"],
            forecast.loc[hist_mask, "yhat"],
            color="#7c3aed", lw=1, alpha=0.5, linestyle="--", label="Model fit")

    ax.plot(forecast.loc[future_mask, "ds"],
            forecast.loc[future_mask, "yhat"],
            color="#f59e0b", lw=2.5, label="Forecast (90 days)", zorder=4)

    ax.fill_between(
        forecast.loc[future_mask, "ds"],
        forecast.loc[future_mask, "yhat_lower"],
        forecast.loc[future_mask, "yhat_upper"],
        alpha=0.25, color="#f59e0b", label="95% Confidence Interval"
    )

    # Mark forecast start
    ax.axvline(df["ds"].max(), color="#ef4444", lw=1.5, linestyle=":", alpha=0.8)
    ax.text(df["ds"].max(), ax.get_ylim()[1] * 0.95,
            "  Forecast start", color="#ef4444", fontsize=9)

    ax.set_title("Revenue Forecast — Next 90 Days (Prophet)", fontsize=14, pad=15)
    ax.set_xlabel("Date")
    ax.set_ylabel("Daily Revenue (BRL)")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"R${x:,.0f}"))
    ax.legend(loc="upper left")
    ax.grid(True)

    plt.tight_layout()
    path = f"{OUT_DIR}/10_revenue_forecast.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


def plot_seasonality(model, forecast):
    """Plot weekly and yearly seasonality components from Prophet."""
    if model is None:
        print("  Seasonality plot skipped (Prophet not used)")
        return

    fig, axes = plt.subplots(2, 1, figsize=(12, 8))

    # Weekly
    weekly = forecast[["ds", "weekly"]].drop_duplicates("ds").head(14)
    weekly["weekday"] = weekly["ds"].dt.day_name()
    axes[0].bar(weekly["weekday"][:7], weekly["weekly"][:7],
                color="#7c3aed", alpha=0.8)
    axes[0].set_title("Weekly Seasonality Effect on Revenue")
    axes[0].set_ylabel("Effect (BRL)")
    axes[0].grid(axis="y")

    # Yearly
    yearly = forecast[["ds", "yearly"]].sort_values("ds")
    axes[1].plot(yearly["ds"], yearly["yearly"], color="#10b981", lw=2)
    axes[1].fill_between(yearly["ds"], yearly["yearly"],
                         alpha=0.2, color="#10b981")
    axes[1].set_title("Yearly Seasonality Effect on Revenue")
    axes[1].set_ylabel("Effect (BRL)")
    axes[1].grid(True)

    plt.suptitle("Seasonality Components (Prophet)", fontsize=14)
    plt.tight_layout()
    path = f"{OUT_DIR}/11_seasonality_components.png"
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {path}")


def print_forecast_summary(df: pd.DataFrame, forecast):
    future_mask = forecast["ds"] > df["ds"].max()
    future_fc   = forecast[future_mask]

    print("\n  Forecast Summary (Next 90 Days):")
    print(f"  Forecasted total revenue : R${future_fc['yhat'].sum():>12,.2f}")
    print(f"  Avg daily revenue        : R${future_fc['yhat'].mean():>12,.2f}")
    print(f"  Peak day forecast        : R${future_fc['yhat'].max():>12,.2f}")
    print(f"  Peak date                : {future_fc.loc[future_fc['yhat'].idxmax(), 'ds'].date()}")


def main():
    print("=" * 50)
    print("  Revenue Forecasting (Prophet / MA fallback)")
    print("=" * 50)

    con = duckdb.connect(DB_PATH)

    print("\n Fetching daily revenue data...")
    df = get_daily_revenue(con)
    print(f" {len(df)} days of data ({df['ds'].min().date()} → {df['ds'].max().date()})")

    print("\n Fitting forecast model...")
    model, forecast = run_prophet_forecast(df, periods=90)

    print("\n Generating charts...")
    plot_forecast(df, forecast, model)
    plot_seasonality(model, forecast)

    print_forecast_summary(df, forecast)

    # Save forecast to DuckDB
    forecast_save = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].copy()
    con.execute("CREATE OR REPLACE TABLE revenue_forecast AS SELECT * FROM forecast_save")
    print("\n  Forecast saved to DuckDB table: revenue_forecast")

    con.close()
    print(f"\n Forecasting complete. Charts in {OUT_DIR}/")
    print("   Next step: streamlit run src/05_dashboard.py")


if __name__ == "__main__":
    main()