{{
    config(
        materialized='table'
    )
}}

with start_stations as (
    select distinct
        start_station_id as station_id,
        start_station_name as station_name
    from {{ ref('stg_bike_trips') }}
    where start_station_id is not null
),

end_stations as (
    select distinct
        end_station_id as station_id,
        end_station_name as station_name
    from {{ ref('stg_bike_trips') }}
    where end_station_id is not null
),

all_stations as (
    select * from start_stations
    union
    select * from end_stations
),

-- Deduplicate in case of station_id with multiple names
final as (
    select
        station_id,
        first(station_name) as station_name,
        count(*) as name_variations
    from all_stations
    where station_id is not null
    group by station_id
)

select * from final

