{{
    config(
        materialized='table'
    )
}}

-- Adjustment Factors for Demand Forecasting
-- Calculates historical impact percentages for weather and holiday conditions
-- Used to adjust baseline forecasts multiplicatively

with daily_trips as (
    -- Get daily trip counts with weather and holiday data
    select
        date_trunc('day', t.started_at) as trip_date,
        count(*) as total_trips,

        -- Weather metrics (join to weather data)
        avg(w.tmax) as avg_temp,
        sum(w.precip) as total_precip,
        avg(w.wind_max) as avg_wind_speed

    from {{ ref('stg_bike_trips') }} t
    left join {{ ref('stg_weather') }} w
        on date_trunc('day', t.started_at) = w.date

    group by trip_date
),

daily_with_holidays as (
    -- Add holiday flags
    select
        dt.*,
        case when h.holiday_name is not null then 1 else 0 end as is_holiday,
        h.holiday_types
    from daily_trips dt
    left join {{ ref('stg_holidays') }} h
        on dt.trip_date = h.date
),

baseline_metrics as (
    -- Calculate baseline (overall average trips per day)
    select
        avg(total_trips) as baseline_trips_per_day
    from daily_with_holidays
),

factor_calculations as (
    select
        -- Temperature factors
        'hot_weather' as factor_name,
        'Temperature > 28°C' as description,
        coalesce(
            round(
                (avg(case when avg_temp > 28 then total_trips end) /
                 (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
                1
            ),
            0.0  -- Default to 0% impact if no matching days
        ) as impact_pct
    from daily_with_holidays
    where avg_temp is not null

    union all

    select
        'neutral_weather' as factor_name,
        'Temperature 15-19°C' as description,
        coalesce(
            round(
                (avg(case when avg_temp >= 15 and avg_temp < 20 then total_trips end) /
                 (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
                1
            ),
            0.0
        ) as impact_pct
    from daily_with_holidays
    where avg_temp is not null

    union all

    select
        'warm_weather' as factor_name,
        'Temperature 20-28°C' as description,
        coalesce(
            round(
                (avg(case when avg_temp >= 20 and avg_temp <= 28 then total_trips end) /
                 (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
                1
            ),
            0.0
        ) as impact_pct
    from daily_with_holidays
    where avg_temp is not null

    union all

    select
        'cold_weather' as factor_name,
        'Temperature < 15°C' as description,
        coalesce(
            round(
                (avg(case when avg_temp < 15 then total_trips end) /
                 (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
                1
            ),
            0.0
        ) as impact_pct
    from daily_with_holidays
    where avg_temp is not null

    union all

    select
        'light_rain' as factor_name,
        'Light rain (≤5 mm)' as description,
        coalesce(
            round(
                (avg(case when total_precip > 0 and total_precip <= 5 then total_trips end) /
                 (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
                1
            ),
            0.0
        ) as impact_pct
    from daily_with_holidays
    where total_precip is not null

    union all

    select
        'heavy_rain' as factor_name,
        'Heavy rain (>5 mm)' as description,
        coalesce(
            round(
                (avg(case when total_precip > 5 then total_trips end) /
                 (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
                1
            ),
            0.0
        ) as impact_pct
    from daily_with_holidays
    where total_precip is not null

    union all

    select
        'weak_wind' as factor_name,
        'Weak wind (≤15 km/h)' as description,
        coalesce(
            round(
                (avg(case when avg_wind_speed <= 15 then total_trips end) /
                 (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
                1
            ),
            0.0
        ) as impact_pct
    from daily_with_holidays
    where avg_wind_speed is not null

    union all

    select
        'strong_wind' as factor_name,
        'Strong wind (>15 km/h)' as description,
        coalesce(
            round(
                (avg(case when avg_wind_speed > 15 then total_trips end) /
                 (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
                1
            ),
            0.0
        ) as impact_pct
    from daily_with_holidays
    where avg_wind_speed is not null

    union all

    select
        'major_holiday' as factor_name,
        'Major holidays (Federal)' as description,
        coalesce(
            round(
                (avg(case when holiday_types like '%Federal%' or holiday_types like '%Public%' then total_trips end) /
                 (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
                1
            ),
            0.0
        ) as impact_pct
    from daily_with_holidays

    union all

    select
        'minor_holiday' as factor_name,
        'Minor holidays (Local)' as description,
        coalesce(
            round(
                (avg(case when holiday_types = 'Local' then total_trips end) /
                 (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
                1
            ),
            0.0
        ) as impact_pct
    from daily_with_holidays

    union all

    -- Day of week factors
    select
        'monday' as factor_name,
        'Monday' as description,
        round(
            (avg(case when extract(dayofweek from trip_date) = 1 then total_trips end) /
             (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
            1
        ) as impact_pct
    from daily_with_holidays

    union all

    select
        'tuesday' as factor_name,
        'Tuesday' as description,
        round(
            (avg(case when extract(dayofweek from trip_date) = 2 then total_trips end) /
             (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
            1
        ) as impact_pct
    from daily_with_holidays

    union all

    select
        'wednesday' as factor_name,
        'Wednesday' as description,
        round(
            (avg(case when extract(dayofweek from trip_date) = 3 then total_trips end) /
             (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
            1
        ) as impact_pct
    from daily_with_holidays

    union all

    select
        'thursday' as factor_name,
        'Thursday' as description,
        round(
            (avg(case when extract(dayofweek from trip_date) = 4 then total_trips end) /
             (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
            1
        ) as impact_pct
    from daily_with_holidays

    union all

    select
        'friday' as factor_name,
        'Friday' as description,
        round(
            (avg(case when extract(dayofweek from trip_date) = 5 then total_trips end) /
             (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
            1
        ) as impact_pct
    from daily_with_holidays

    union all

    select
        'saturday' as factor_name,
        'Saturday' as description,
        round(
            (avg(case when extract(dayofweek from trip_date) = 6 then total_trips end) /
             (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
            1
        ) as impact_pct
    from daily_with_holidays

    union all

    select
        'sunday' as factor_name,
        'Sunday' as description,
        round(
            (avg(case when extract(dayofweek from trip_date) = 0 then total_trips end) /
             (select baseline_trips_per_day from baseline_metrics) - 1) * 100,
            1
        ) as impact_pct
    from daily_with_holidays
)

select
    factor_name,
    description,
    impact_pct,

    -- Convert to multiplicative factor for dashboard use
    -- Example: -20% impact → factor = 0.80 (multiply baseline by 0.80)
    -- Example: +15% impact → factor = 1.15 (multiply baseline by 1.15)
    round(1 + (impact_pct / 100.0), 3) as adjustment_multiplier,

    -- Helper text for dashboard
    case
        when impact_pct > 0 then '+' || cast(impact_pct as varchar) || '% increase'
        when impact_pct < 0 then cast(impact_pct as varchar) || '% decrease'
        else 'No impact'
    end as impact_label

from factor_calculations
order by factor_name
