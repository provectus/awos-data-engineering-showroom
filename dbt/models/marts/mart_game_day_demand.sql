{{
    config(
        materialized='table'
    )
}}

-- Game Day Demand Analysis by Station and Hour
-- Analyzes bike demand patterns at nearby stations during game times
-- Compares game day demand vs baseline (same day of week, non-game days)

with games as (
    select
        game_id,
        game_date,
        game_datetime,
        estimated_end_datetime,
        stadium_name,
        home_team_name,
        away_team_name
    from {{ ref('stg_games') }}
    where game_date between '2024-05-01' and '2024-06-30'
      and stadium_name in ('Yankee Stadium', 'Citi Field')  -- Exclude London Stadium
),

nearby_stations as (
    select
        stadium_name,
        station_id,
        station_name,
        distance_km
    from {{ ref('fct_station_proximity') }}
    where within_1km = true
),

-- Calculate demand on game days for nearby stations (6-hour window: -3h to +3h)
game_day_demand as (
    select
        g.game_id,
        g.game_date,
        g.game_datetime,
        g.stadium_name,
        g.home_team_name,
        g.away_team_name,
        ns.station_id,
        ns.station_name,
        extract(hour from t.started_at) as start_hour,
        extract(hour from g.game_datetime) as game_hour,
        (extract(hour from t.started_at) - extract(hour from g.game_datetime))::int as hour_offset,

        -- Count trips started at this station
        count(case when t.start_station_id = ns.station_id then 1 end) as trips_started,

        -- Count trips ended at this station
        count(case when t.end_station_id = ns.station_id then 1 end) as trips_ended

    from games g
    inner join nearby_stations ns
        on g.stadium_name = ns.stadium_name
    inner join {{ ref('stg_bike_trips') }} t
        on t.ride_date = g.game_date
        and extract(hour from t.started_at) between
            extract(hour from g.game_datetime) - 3
            and extract(hour from g.estimated_end_datetime) + 3
    where (t.start_station_id = ns.station_id or t.end_station_id = ns.station_id)
    group by
        g.game_id,
        g.game_date,
        g.game_datetime,
        g.stadium_name,
        g.home_team_name,
        g.away_team_name,
        ns.station_id,
        ns.station_name,
        extract(hour from t.started_at),
        extract(hour from g.game_datetime)
),

-- Calculate baseline demand (same day of week, non-game days, excluding holidays)
baseline_demand as (
    select
        g.game_id,
        ns.station_id,
        extract(hour from t.started_at) as start_hour,
        (extract(hour from t.started_at) - extract(hour from g.game_datetime))::int as hour_offset,

        -- Average trips started (per baseline day)
        count(case when t.start_station_id = ns.station_id then 1 end)::float /
            count(distinct t.ride_date) as avg_trips_started,

        -- Average trips ended (per baseline day)
        count(case when t.end_station_id = ns.station_id then 1 end)::float /
            count(distinct t.ride_date) as avg_trips_ended

    from games g
    inner join nearby_stations ns
        on g.stadium_name = ns.stadium_name
    inner join {{ ref('stg_bike_trips') }} t
        on dayofweek(t.ride_date) = dayofweek(g.game_date)
        and t.ride_date != g.game_date
        and t.ride_date between '2024-05-01' and '2024-06-30'
        and extract(hour from t.started_at) between
            extract(hour from g.game_datetime) - 3
            and extract(hour from g.estimated_end_datetime) + 3
        and (t.start_station_id = ns.station_id or t.end_station_id = ns.station_id)
        -- Exclude other game days
        and t.ride_date not in (
            select game_date from {{ ref('stg_games') }}
            where stadium_name in ('Yankee Stadium', 'Citi Field')
        )
        -- Exclude holidays
        and t.ride_date not in (
            select date from {{ ref('stg_holidays') }}
        )
    group by
        g.game_id,
        ns.station_id,
        extract(hour from t.started_at),
        extract(hour from g.game_datetime)
)

-- Final comparison with percentage changes
select
    gd.game_id,
    gd.game_date,
    gd.game_datetime,
    gd.stadium_name,
    gd.home_team_name,
    gd.away_team_name,
    gd.station_id,
    gd.station_name,
    gd.hour_offset,
    gd.start_hour,
    gd.game_hour,

    -- Game day metrics
    gd.trips_started as trips_started_game_day,
    gd.trips_ended as trips_ended_game_day,
    (gd.trips_ended - gd.trips_started) as net_flow_game_day,

    -- Baseline metrics
    coalesce(bd.avg_trips_started, 0) as trips_started_baseline,
    coalesce(bd.avg_trips_ended, 0) as trips_ended_baseline,
    (coalesce(bd.avg_trips_ended, 0) - coalesce(bd.avg_trips_started, 0)) as net_flow_baseline,

    -- Percentage changes
    case
        when bd.avg_trips_started > 0 then
            ((gd.trips_started - bd.avg_trips_started) / bd.avg_trips_started) * 100
        else null
    end as trips_started_pct_change,

    case
        when bd.avg_trips_ended > 0 then
            ((gd.trips_ended - bd.avg_trips_ended) / bd.avg_trips_ended) * 100
        else null
    end as trips_ended_pct_change

from game_day_demand gd
left join baseline_demand bd
    on gd.game_id = bd.game_id
    and gd.station_id = bd.station_id
    and gd.hour_offset = bd.hour_offset
order by gd.game_date, gd.stadium_name, gd.station_id, gd.hour_offset
