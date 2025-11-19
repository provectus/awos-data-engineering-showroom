{{
    config(
        materialized='view'
    )
}}

with source_games as (
    select
        game_id,
        game_date,
        game_datetime,
        official_date,
        season,
        game_type,
        game_status,
        home_team_id,
        home_team_name,
        away_team_id,
        away_team_name,
        venue_id,
        venue_name,
        _dlt_load_timestamp,
        source_api
    from {{ source('raw_games', 'mlb_games') }}
)

select
    game_id,
    game_date::date as game_date,
    game_datetime::timestamp as game_datetime,
    extract(hour from game_datetime::timestamp) as game_hour,
    game_datetime::timestamp::time as game_time,
    official_date,
    season,
    game_type,
    game_status,

    -- Team information
    home_team_id,
    home_team_name,
    away_team_id,
    away_team_name,

    -- Venue information
    venue_id,
    venue_name,

    -- Derived fields
    game_datetime::timestamp + interval '3 hours' as estimated_end_datetime,

    case when home_team_id = 147 then true else false end as is_yankees_home,
    case when home_team_id = 121 then true else false end as is_mets_home,

    case
        when venue_name like '%Yankee%' then 'Yankee Stadium'
        when venue_name like '%Citi Field%' then 'Citi Field'
        else venue_name
    end as stadium_name,

    -- Metadata
    _dlt_load_timestamp,
    source_api

from source_games
