"""Streamlit dashboard for weather impact analysis.

This page shows how weather conditions affect bike demand.
"""

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import duckdb


# Page configuration
st.set_page_config(
    page_title="Weather Impact Analysis",
    page_icon="🌦️",
    layout="wide",
)


@st.cache_resource
def get_db_connection():
    """Create and cache DuckDB connection."""
    return duckdb.connect("./duckdb/warehouse.duckdb", read_only=True)


@st.cache_data(ttl=600)
def load_weather_effect_data():
    """Load weather effect data from the marts."""
    con = get_db_connection()
    query = """
        SELECT *
        FROM marts.mart_weather_effect
        ORDER BY date
    """
    try:
        df = con.execute(query).df()
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()


def calculate_correlation(df: pd.DataFrame, col1: str, col2: str) -> float:
    """Calculate correlation between two columns."""
    if df.empty or col1 not in df.columns or col2 not in df.columns:
        return 0.0
    clean_df = df[[col1, col2]].dropna()
    if clean_df.empty or len(clean_df) < 2:
        return 0.0
    return clean_df[col1].corr(clean_df[col2])


def main():
    """Main Streamlit app for weather analysis."""
    st.title("🌦️ Weather Impact on Bike Demand")
    st.markdown("### Understanding how weather conditions influence ridership")

    # Load data
    df = load_weather_effect_data()

    if df.empty:
        st.warning(
            "No weather data available. Please run:\n\n"
            "1. Weather data ingestion: `uv run python dlt_pipeline/weather.py`\n"
            "2. dbt transformations: `cd dbt && dbt build`"
        )
        return

    # Filters in sidebar
    st.sidebar.header("🔍 Filters")
    rain_filter = st.sidebar.radio(
        "Weather Condition",
        ["All Days", "Rainy Days Only", "Dry Days Only"],
        index=0,
    )

    # Apply filter
    filtered_df = df.copy()
    if rain_filter == "Rainy Days Only":
        filtered_df = filtered_df[filtered_df["is_rain"] == 1]
    elif rain_filter == "Dry Days Only":
        filtered_df = filtered_df[filtered_df["is_rain"] == 0]

    # Key Correlations
    st.markdown("---")
    st.subheader("📊 Weather Correlations")

    col1, col2, col3 = st.columns(3)

    temp_corr = calculate_correlation(filtered_df, "trips_total", "temp_avg")
    precip_corr = calculate_correlation(filtered_df, "trips_total", "precip")
    wind_corr = calculate_correlation(filtered_df, "trips_total", "wind_max")

    with col1:
        st.metric(
            "Temperature Correlation",
            f"{temp_corr:.3f}",
            delta="Positive" if temp_corr > 0 else "Negative",
        )

    with col2:
        st.metric(
            "Precipitation Correlation",
            f"{precip_corr:.3f}",
            delta="Negative" if precip_corr < 0 else "Positive",
        )

    with col3:
        st.metric(
            "Wind Correlation",
            f"{wind_corr:.3f}",
            delta="Negative" if wind_corr < 0 else "Positive",
        )

    # Dual-axis chart: Trips vs Temperature
    st.markdown("---")
    st.subheader("🌡️ Trips and Temperature Over Time")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Add trips line
    fig.add_trace(
        go.Scatter(
            x=filtered_df["date"],
            y=filtered_df["trips_total"],
            name="Trips",
            line={"color": "#1f77b4", "width": 2},
        ),
        secondary_y=False,
    )

    # Add temperature line
    fig.add_trace(
        go.Scatter(
            x=filtered_df["date"],
            y=filtered_df["temp_avg"],
            name="Avg Temperature",
            line={"color": "#ff7f0e", "width": 2, "dash": "dot"},
        ),
        secondary_y=True,
    )

    fig.update_xaxes(title_text="Date")
    fig.update_yaxes(title_text="Number of Trips", secondary_y=False)
    fig.update_yaxes(title_text="Temperature (°C)", secondary_y=True)
    fig.update_layout(hovermode="x unified", height=400)

    st.plotly_chart(fig, use_container_width=True)

    # Scatter plots
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🌡️ Trips vs Temperature")
        fig_temp = px.scatter(
            filtered_df,
            x="temp_avg",
            y="trips_total",
            trendline="ols",
            labels={"temp_avg": "Avg Temperature (°C)", "trips_total": "Total Trips"},
            color="is_rain",
            color_discrete_map={0: "#2ca02c", 1: "#d62728"},
        )
        fig_temp.update_layout(height=400)
        st.plotly_chart(fig_temp, use_container_width=True)

    with col2:
        st.subheader("🌧️ Trips vs Precipitation")
        fig_precip = px.scatter(
            filtered_df,
            x="precip",
            y="trips_total",
            trendline="ols",
            labels={"precip": "Precipitation (mm)", "trips_total": "Total Trips"},
            color="day_type",
            color_discrete_map={"Weekday": "#1f77b4", "Weekend": "#ff7f0e"},
        )
        fig_precip.update_layout(height=400)
        st.plotly_chart(fig_precip, use_container_width=True)

    # Impact by categories
    st.markdown("---")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🌡️ Demand by Temperature Category")
        temp_impact = filtered_df.groupby("temp_category")["trips_total"].mean().reset_index()
        temp_impact = temp_impact.sort_values("trips_total", ascending=False)

        fig_temp_cat = px.bar(
            temp_impact,
            x="temp_category",
            y="trips_total",
            labels={"temp_category": "Temperature", "trips_total": "Avg Trips"},
            color="trips_total",
            color_continuous_scale="RdYlBu_r",
        )
        fig_temp_cat.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig_temp_cat, use_container_width=True)

    with col2:
        st.subheader("🌧️ Demand by Rain Category")
        rain_impact = filtered_df.groupby("rain_category")["trips_total"].mean().reset_index()
        rain_impact = rain_impact.sort_values("trips_total", ascending=False)

        fig_rain_cat = px.bar(
            rain_impact,
            x="rain_category",
            y="trips_total",
            labels={"rain_category": "Rain Level", "trips_total": "Avg Trips"},
            color="trips_total",
            color_continuous_scale="Blues_r",
        )
        fig_rain_cat.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig_rain_cat, use_container_width=True)

    # What-if analysis
    st.markdown("---")
    st.subheader("🔮 What-If Temperature Analysis")
    st.markdown("See how changing the temperature might affect bike demand")

    # Calculate simple linear regression
    clean_data = filtered_df[["temp_avg", "trips_total"]].dropna()

    if len(clean_data) >= 2:
        # Fit linear model
        coeffs = np.polyfit(clean_data["temp_avg"], clean_data["trips_total"], 1)
        slope, intercept = coeffs[0], coeffs[1]

        current_avg_temp = clean_data["temp_avg"].mean()
        current_avg_trips = clean_data["trips_total"].mean()

        col1, col2 = st.columns([2, 1])

        with col1:
            temp_delta = st.slider(
                "Temperature Change (°C)",
                min_value=-10.0,
                max_value=10.0,
                value=0.0,
                step=0.5,
            )

        with col2:
            new_temp = current_avg_temp + temp_delta
            predicted_trips = slope * new_temp + intercept
            trip_change = predicted_trips - current_avg_trips

            st.metric(
                "Predicted Avg Daily Trips",
                f"{predicted_trips:,.0f}",
                delta=f"{trip_change:+,.0f} trips",
            )

        st.info(
            f"📝 Based on linear regression: Each 1°C increase correlates "
            f"with {slope:+.0f} trips/day"
        )
    else:
        st.warning("Not enough data for what-if analysis")

    # Data Preview
    st.markdown("---")
    with st.expander("📊 View Raw Data"):
        st.dataframe(filtered_df, use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown(
        "*Weather Data: Open-Meteo API | Bike Data: NYC Citi Bike | "
        "Correlations calculated on filtered data*"
    )


if __name__ == "__main__":
    main()
