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

-- Extract geographic coordinates from raw data
stations_with_coords as (
    select
        start_station_id as station_id,
        first(start_lat) as latitude,
        first(start_lng) as longitude
    from {{ ref('stg_bike_trips') }}
    where
        start_station_id is not null
        and start_lat is not null
        and start_lng is not null
        and start_lat between 40.5 and 41.0
        and start_lng between -74.3 and -73.7
    group by start_station_id
),

-- Deduplicate station names and add geographic dimensions
final as (
    select
        a.station_id,
        first(a.station_name) as station_name,
        count(*) as name_variations,
        c.latitude,
        c.longitude,
        case
            when c.latitude between 40.700 and 40.720 and c.longitude between -74.020 and -73.980
                then 'Manhattan - Financial'
            when c.latitude between 40.740 and 40.780 and c.longitude between -74.010 and -73.970
                then 'Manhattan - Midtown'
            when c.latitude between 40.780 and 40.800 and c.longitude between -74.000 and -73.950
                then 'Manhattan - Upper West'
            when c.latitude between 40.780 and 40.800 and c.longitude between -73.980 and -73.940
                then 'Manhattan - Upper East'
            when c.latitude between 40.700 and 40.730 and c.longitude between -73.970 and -73.930
                then 'Manhattan - Downtown'
            when c.latitude between 40.580 and 40.740 and c.longitude between -74.050 and -73.833
                then 'Brooklyn'
            when c.latitude between 40.690 and 40.800 and c.longitude between -73.962 and -73.700
                then 'Queens'
            when c.latitude between 40.790 and 40.880 and c.longitude between -73.930 and -73.830
                then 'Bronx'
            when c.latitude between 40.680 and 40.760 and c.longitude between -74.080 and -74.020
                then 'Jersey City'
            else 'Other'
        end as area
    from all_stations a
    left join stations_with_coords c on a.station_id = c.station_id
    where a.station_id is not null
    group by a.station_id, c.latitude, c.longitude
)

select * from final

