{{
    config(
        materialized='view'
    )
}}

with source as (
    select * from raw_weather.daily_weather
),

cleaned as (
    select
        cast(date as date) as date,
        tmax,
        tmin,
        precip,
        wind_max,
        _dlt_load_timestamp,
        source_location
    from source
    where
        date is not null
        -- Only enforce tmax >= tmin when both values are present
        -- This preserves records with partial temperature data but valid precip/wind
        and (tmax is null or tmin is null or tmax >= tmin)
)

select * from cleaned

