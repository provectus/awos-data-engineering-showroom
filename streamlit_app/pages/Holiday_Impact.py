"""Streamlit dashboard for holiday impact analysis.

This page shows how public holidays affect NYC Citi Bike demand.
"""

import calendar
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import duckdb


# Page configuration
st.set_page_config(
    page_title="Holiday Impact Analysis",
    page_icon="🎉",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def get_db_connection():
    """Create and cache DuckDB connection."""
    return duckdb.connect("duckdb/warehouse.duckdb", read_only=True)


@st.cache_data(ttl=600)
def load_holiday_data():
    """Load holiday analysis data from the marts.

    Returns:
        pd.DataFrame: Holiday analysis data with ride_date, is_holiday, holiday_name,
                     holiday_category, trips_total, trips_weather_adjusted,
                     baseline_daily_trips, demand_vs_baseline_pct, tmax, precip, day_type.
    """
    con = get_db_connection()
    query = """
        SELECT *
        FROM main_marts.mart_holiday_analysis
        ORDER BY ride_date
    """
    try:
        df = con.execute(query).df()
        return df
    except Exception as e:
        st.error(f"Error loading holiday data: {e}")
        return pd.DataFrame()


def check_data_sufficiency(df: pd.DataFrame) -> tuple[bool, int]:
    """Check if there is sufficient historical data for meaningful analysis.

    Args:
        df: Holiday analysis dataframe.

    Returns:
        Tuple of (is_sufficient, holiday_count) where is_sufficient is True if
        there are at least 2 holidays with trip data.
    """
    if df.empty:
        return False, 0

    holiday_count = df[df["is_holiday"]]["holiday_name"].nunique()
    is_sufficient = holiday_count >= 2

    return is_sufficient, holiday_count


@st.cache_data(ttl=600)
def load_holiday_comparison_data():
    """Load aggregated holiday vs. non-holiday demand comparison data.

    Returns:
        pd.DataFrame: Aggregated data with columns: holiday_category, avg_demand,
                     holiday_count, date_range_start, date_range_end.
    """
    con = get_db_connection()
    query = """
        SELECT
            holiday_category,
            AVG(trips_weather_adjusted) AS avg_demand,
            COUNT(DISTINCT ride_date) AS holiday_count,
            MIN(ride_date)::VARCHAR AS date_range_start,
            MAX(ride_date)::VARCHAR AS date_range_end
        FROM main_marts.mart_holiday_analysis
        WHERE is_holiday = TRUE
        GROUP BY holiday_category

        UNION ALL

        SELECT
            CAST('Non-Holiday Baseline' AS VARCHAR) AS holiday_category,
            AVG(trips_weather_adjusted) AS avg_demand,
            COUNT(DISTINCT ride_date) AS holiday_count,
            MIN(ride_date)::VARCHAR AS date_range_start,
            MAX(ride_date)::VARCHAR AS date_range_end
        FROM main_marts.mart_holiday_analysis
        WHERE is_holiday = FALSE
    """
    try:
        df = con.execute(query).df()
        return df
    except Exception as e:
        st.error(f"Error loading holiday comparison data: {e}")
        return pd.DataFrame()


def create_holiday_comparison_chart(df: pd.DataFrame) -> px.bar:
    """Create a bar chart comparing holiday vs. non-holiday demand.

    Args:
        df: DataFrame with holiday_category, avg_demand, holiday_count,
            date_range_start, date_range_end columns.

    Returns:
        Plotly bar chart figure.
    """
    if df.empty:
        return None

    # Calculate percentage change vs. baseline
    baseline_demand = df[df["holiday_category"] == "Non-Holiday Baseline"]["avg_demand"].iloc[0]

    df["pct_change"] = ((df["avg_demand"] - baseline_demand) / baseline_demand) * 100
    df["pct_change_label"] = df["pct_change"].apply(
        lambda x: f"{x:+.1f}%" if x != 0 else "Baseline"
    )

    # Format tooltip text
    df["tooltip_text"] = df.apply(
        lambda row: (
            f"<b>{row['holiday_category']}</b><br>"
            f"Avg Daily Trips: {row['avg_demand']:,.0f}<br>"
            f"Number of Days: {row['holiday_count']}<br>"
            f"Date Range: {row['date_range_start']} to {row['date_range_end']}"
        ),
        axis=1,
    )

    # Define color mapping
    color_map = {
        "Federal Holiday": "#1f77b4",  # Blue
        "NY State Observance": "#ff7f0e",  # Orange
        "Non-Holiday Baseline": "#7f7f7f",  # Gray
    }

    # Create bar chart
    fig = px.bar(
        df,
        x="holiday_category",
        y="avg_demand",
        color="holiday_category",
        color_discrete_map=color_map,
        text="pct_change_label",
        custom_data=["tooltip_text"],
        labels={
            "holiday_category": "Category",
            "avg_demand": "Average Daily Trips (Weather-Adjusted)",
        },
        title="",
    )

    # Update layout
    fig.update_traces(
        textposition="outside",
        hovertemplate="%{customdata[0]}<extra></extra>",
        textfont_size=12,
    )

    fig.update_layout(
        showlegend=False,
        xaxis_title="",
        yaxis_title="Average Daily Trips (Weather-Adjusted)",
        height=500,
        hovermode="closest",
        font={"size": 12},
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis={"gridcolor": "lightgray"},
    )

    return fig


@st.cache_data(ttl=600)
def load_calendar_heatmap_data(year: int = 2024):
    """Load calendar data with holidays and trip counts for heatmap.

    Args:
        year: Year to load data for (default: 2024).

    Returns:
        pd.DataFrame: Calendar data with ride_date, is_holiday, holiday_name,
                     trips_total, and data_status columns.
    """
    con = get_db_connection()
    query = f"""
        SELECT
            ride_date,
            is_holiday,
            holiday_name,
            trips_total,
            CASE WHEN trips_total IS NULL THEN 'No Data' ELSE 'Data Available' END AS data_status
        FROM main_marts.mart_holiday_analysis
        WHERE YEAR(ride_date) = {year}
        ORDER BY ride_date
    """
    try:
        df = con.execute(query).df()
        return df
    except Exception as e:
        st.error(f"Error loading calendar heatmap data: {e}")
        return pd.DataFrame()


def create_calendar_heatmap(df: pd.DataFrame, year: int = 2024) -> go.Figure:
    """Create a calendar heatmap showing holidays and demand levels.

    Args:
        df: DataFrame with ride_date, is_holiday, holiday_name, trips_total,
            and data_status columns.
        year: Year to display (default: 2024).

    Returns:
        Plotly figure with calendar heatmap.
    """
    if df.empty:
        return None

    # Ensure ride_date is datetime and remove timezone to avoid merge conflicts
    df["ride_date"] = pd.to_datetime(df["ride_date"]).dt.tz_localize(None)

    # Create a full year date range
    start_date = pd.Timestamp(year, 1, 1)
    end_date = pd.Timestamp(year, 12, 31)
    all_dates = pd.date_range(start=start_date, end=end_date, freq="D")

    # Create a complete calendar dataframe
    calendar_df = pd.DataFrame({"ride_date": all_dates})
    calendar_df = calendar_df.merge(df, on="ride_date", how="left")

    # Fill missing values
    calendar_df["is_holiday"] = calendar_df["is_holiday"].fillna(False)
    calendar_df["holiday_name"] = calendar_df["holiday_name"].fillna("")
    calendar_df["data_status"] = calendar_df["data_status"].fillna("No Data")

    # Add calendar components
    calendar_df["year"] = calendar_df["ride_date"].dt.year
    calendar_df["month"] = calendar_df["ride_date"].dt.month
    calendar_df["day"] = calendar_df["ride_date"].dt.day
    calendar_df["weekday"] = calendar_df["ride_date"].dt.dayofweek  # Monday=0, Sunday=6
    calendar_df["week_of_month"] = (calendar_df["day"] - 1) // 7

    # Create the figure
    fig = go.Figure()

    # Define color scale for demand (white to dark blue)
    # Use trips_total for coloring
    min_trips = calendar_df[calendar_df["data_status"] == "Data Available"]["trips_total"].min()
    max_trips = calendar_df[calendar_df["data_status"] == "Data Available"]["trips_total"].max()

    # Process each month
    for month_num in range(1, 13):
        month_data = calendar_df[calendar_df["month"] == month_num].copy()

        if month_data.empty:
            continue

        # Get month name
        month_name = calendar.month_name[month_num]

        # Calculate positions
        # X position: column based on month (4 months per row)
        col = (month_num - 1) % 4
        # Y position: row based on month (3 rows)
        row = (month_num - 1) // 4

        # Calculate cell positions within the month grid
        # Each month grid: 7 columns (weekdays) x 6 rows (weeks)
        x_offset = col * 8  # 7 for weekdays + 1 for spacing
        y_offset = row * 7  # 6 for weeks + 1 for spacing

        for _, day_row in month_data.iterrows():
            weekday = day_row["weekday"]
            week = day_row["week_of_month"]

            # Calculate cell position
            x_pos = x_offset + weekday
            y_pos = y_offset + week

            # Determine cell color
            if day_row["data_status"] == "No Data":
                # Gray for no data
                color = "lightgray"
                trips_display = "No Data"
            else:
                # Color intensity based on trips_total
                if max_trips > min_trips:
                    intensity = (day_row["trips_total"] - min_trips) / (max_trips - min_trips)
                else:
                    intensity = 0.5
                # Use blue color scale
                rgb_value = int(255 * (1 - intensity * 0.7))  # Darker blue = higher demand
                color = f"rgb({rgb_value}, {rgb_value}, 255)"
                trips_display = f"{day_row['trips_total']:,.0f} trips"

            # Determine border style for holidays
            line_width = 3 if day_row["is_holiday"] else 0.5
            line_color = "red" if day_row["is_holiday"] else "white"

            # Create hover text
            hover_text = (
                f"<b>{day_row['ride_date'].strftime('%Y-%m-%d')}</b><br>"
                f"{trips_display}<br>"
            )
            if day_row["is_holiday"] and day_row["holiday_name"]:
                hover_text += f"<b>🎉 {day_row['holiday_name']}</b>"

            # Add cell as rectangle
            fig.add_trace(
                go.Scatter(
                    x=[x_pos],
                    y=[y_pos],
                    mode="markers",
                    marker={
                        "size": 30,
                        "color": color,
                        "symbol": "square",
                        "line": {"width": line_width, "color": line_color},
                    },
                    hovertemplate=hover_text + "<extra></extra>",
                    showlegend=False,
                )
            )

            # Add day number as text
            fig.add_trace(
                go.Scatter(
                    x=[x_pos],
                    y=[y_pos],
                    mode="text",
                    text=str(day_row["day"]),
                    textfont={"size": 10, "color": "black" if color == "lightgray" else "white"},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

            # Add holiday name if it's a holiday
            if day_row["is_holiday"] and day_row["holiday_name"]:
                fig.add_annotation(
                    x=x_pos,
                    y=y_pos - 0.35,
                    text=day_row["holiday_name"][:10],  # Truncate long names
                    showarrow=False,
                    font={"size": 7, "color": "darkred"},
                    bgcolor="rgba(255, 255, 255, 0.7)",
                    borderpad=1,
                )

        # Add month label
        fig.add_annotation(
            x=x_offset + 3,
            y=y_offset + 6.5,
            text=f"<b>{month_name}</b>",
            showarrow=False,
            font={"size": 12, "color": "black"},
            xanchor="center",
        )

        # Add weekday labels (just for first row of months)
        if row == 0:
            weekday_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
            for i, label in enumerate(weekday_labels):
                fig.add_annotation(
                    x=x_offset + i,
                    y=y_offset + 6,
                    text=label,
                    showarrow=False,
                    font={"size": 9, "color": "gray"},
                )

    # Update layout
    fig.update_layout(
        title="",
        xaxis={
            "visible": False,
            "range": [-1, 32],
        },
        yaxis={
            "visible": False,
            "range": [-1, 22],
            "scaleanchor": "x",
            "scaleratio": 1,
        },
        height=900,
        hovermode="closest",
        plot_bgcolor="white",
        margin={"l": 20, "r": 20, "t": 40, "b": 20},
    )

    return fig


def main():
    """Main Streamlit app for holiday impact analysis."""
    # Load data
    df = load_holiday_data()

    if df.empty:
        st.warning(
            "No holiday data available. Please run:\n\n"
            "1. Holiday data ingestion: `uv run python dlt_pipeline/holiday.py`\n"
            "2. dbt transformations: `cd dbt && uv run dbt build`"
        )
        return

    # Check data sufficiency and show banner if needed
    is_sufficient, holiday_count = check_data_sufficiency(df)

    if not is_sufficient:
        st.info(
            "⚠️ Limited historical data available. "
            "Insights will strengthen as more data accumulates over time."
        )

    # Page title
    st.title("Holiday Impact Analysis")
    st.markdown("### Understanding how public holidays influence bike ridership")

    # Visualization 1: Holiday vs. Non-Holiday Demand Comparison
    st.markdown("---")
    st.markdown("### Holiday vs. Non-Holiday Demand")
    st.markdown(
        "Comparison of average daily bike trips on holidays versus non-holidays, "
        "adjusted for weather conditions to isolate the holiday effect."
    )

    comparison_df = load_holiday_comparison_data()

    if comparison_df.empty:
        st.warning("No holiday comparison data available.")
    else:
        chart = create_holiday_comparison_chart(comparison_df)
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.warning("Unable to generate comparison chart.")

    # Visualization 2: Holiday Calendar Heatmap
    st.markdown("---")
    st.markdown("### Holiday Calendar Heatmap")
    st.markdown(
        "Calendar view of 2024 showing holidays and demand levels. "
        "Cell color intensity represents trip volume (darker blue = higher demand), "
        "holidays are marked with red borders and labels, and gray cells indicate no data."
    )

    calendar_data = load_calendar_heatmap_data(year=2024)

    if calendar_data.empty:
        st.warning("No calendar data available for 2024.")
    else:
        # Create legend
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**Legend:**")
        with col2:
            st.markdown("🟦 Light to Dark Blue: Low to High Demand")
        with col3:
            st.markdown("⬜ Gray: No Data | 🔴 Red Border: Holiday")

        heatmap_fig = create_calendar_heatmap(calendar_data, year=2024)
        if heatmap_fig:
            st.plotly_chart(heatmap_fig, use_container_width=True)
        else:
            st.warning("Unable to generate calendar heatmap.")

    # Show basic data info in an expander
    with st.expander("📋 Data Preview"):
        st.markdown(f"**Total records:** {len(df)}")
        st.markdown(f"**Date range:** {df['ride_date'].min()} to {df['ride_date'].max()}")
        st.markdown(f"**Holidays in dataset:** {holiday_count}")

        # Show sample of the data
        st.dataframe(df.head(10), use_container_width=True)

    # Footer
    st.markdown("---")
    st.markdown(
        "*Holiday Data: Nager.Date API | Bike Data: NYC Citi Bike | Weather Data: Open-Meteo API*"
    )


if __name__ == "__main__":
    main()
