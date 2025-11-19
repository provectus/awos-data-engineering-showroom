{{
    config(
        materialized='table'
    )
}}

-- Calculate distance from each stadium to all bike stations using Haversine formula
-- Used to identify stations within walking distance of game venues

with stadiums as (
    select
        stadium_id,
        stadium_name,
        latitude as stadium_lat,
        longitude as stadium_lon
    from {{ ref('dim_stadiums') }}
),

stations as (
    select
        station_id,
        station_name,
        latitude as station_lat,
        longitude as station_lon
    from {{ ref('dim_stations') }}
    where latitude is not null
      and longitude is not null
),

-- Cross join stadiums with all stations and calculate distances
distances as (
    select
        stadiums.stadium_id,
        stadiums.stadium_name,
        stations.station_id,
        stations.station_name,

        -- Haversine formula for great circle distance
        -- Returns distance in kilometers
        6371 * 2 * asin(sqrt(
            pow(sin((radians(stadiums.stadium_lat) - radians(stations.station_lat)) / 2), 2) +
            cos(radians(stations.station_lat)) * cos(radians(stadiums.stadium_lat)) *
            pow(sin((radians(stadiums.stadium_lon) - radians(stations.station_lon)) / 2), 2)
        )) as distance_km

    from stadiums
    cross join stations
)

select
    stadium_id,
    stadium_name,
    station_id,
    station_name,
    distance_km,

    -- Flag for stations within 1km radius (walking distance)
    case when distance_km <= 1.0 then true else false end as within_1km

from distances
order by stadium_id, distance_km
