{{
    config(
        materialized='table'
    )
}}

with demand as (
    select
        ride_date as date,
        trips_total,
        avg_duration_mins,
        member_trips,
        casual_trips,
        day_of_week,
        day_type
    from {{ ref('mart_demand_daily') }}
),

weather as (
    select
        date,
        tmax,
        tmin,
        precip,
        wind_max,
        (tmax + tmin) / 2.0 as temp_avg
    from {{ ref('stg_weather') }}
),

joined as (
    select
        d.date,
        d.trips_total,
        d.avg_duration_mins,
        d.member_trips,
        d.casual_trips,
        d.day_of_week,
        d.day_type,
        w.tmax,
        w.tmin,
        w.temp_avg,
        w.precip,
        w.wind_max,
        case when w.precip > 0 then 1 else 0 end as is_rain,
        case
            when w.precip > 10 then 'Heavy Rain'
            when w.precip > 0 then 'Light Rain'
            else 'No Rain'
        end as rain_category,
        case
            when w.temp_avg < 5 then 'Very Cold'
            when w.temp_avg < 15 then 'Cold'
            when w.temp_avg < 25 then 'Moderate'
            else 'Warm'
        end as temp_category
    from demand d
    left join weather w on d.date = w.date
)

select * from joined
order by date

