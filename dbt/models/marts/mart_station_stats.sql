{{
    config(
        materialized='table'
    )
}}

with station_trips as (
    select
        t.ride_id,
        t.start_station_id,
        t.end_station_id,
        t.ride_date,
        t.member_casual,
        t.ride_mins
    from {{ ref('stg_bike_trips') }} t
),

start_station_stats as (
    select
        s.station_id,
        s.station_name,
        count(distinct t.ride_id) as start_trip_count,
        avg(t.ride_mins) as avg_start_duration,
        count(distinct case when t.member_casual = 'member' then t.ride_id end) as member_start_trips,
        count(distinct case when t.member_casual = 'casual' then t.ride_id end) as casual_start_trips
    from {{ ref('dim_stations') }} s
    left join station_trips t
        on s.station_id = t.start_station_id
    group by s.station_id, s.station_name
),

end_station_stats as (
    select
        s.station_id,
        count(distinct t.ride_id) as end_trip_count
    from {{ ref('dim_stations') }} s
    left join station_trips t
        on s.station_id = t.end_station_id
    group by s.station_id
),

final as (
    select
        ss.station_id,
        ss.station_name,
        ss.start_trip_count,
        es.end_trip_count,
        ss.start_trip_count + es.end_trip_count as total_trip_count,
        ss.avg_start_duration,
        ss.member_start_trips,
        ss.casual_start_trips,
        round(ss.member_start_trips * 100.0 / nullif(ss.start_trip_count, 0), 2) as member_pct
    from start_station_stats ss
    left join end_station_stats es
        on ss.station_id = es.station_id
)

select * from final
order by start_trip_count desc

