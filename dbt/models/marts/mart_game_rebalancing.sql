{{
    config(
        materialized='table'
    )
}}

-- Game Rebalancing Recommendations
-- Aggregates game day demand patterns to provide actionable rebalancing recommendations
-- Operations managers can use this to pre-position bikes before games

with aggregated_demand as (
    select
        stadium_name,
        station_id,
        hour_offset,

        -- Average metrics across all games for this stadium/station/hour combination
        avg(trips_started_game_day) as avg_trips_started,
        avg(trips_ended_game_day) as avg_trips_ended,
        avg(net_flow_game_day) as avg_net_flow,

        -- Count of games for this pattern
        count(distinct game_id) as num_games

    from {{ ref('mart_game_day_demand') }}
    group by stadium_name, station_id, hour_offset
)

select
    ad.stadium_name,
    ad.station_id,
    s.station_name,
    ad.hour_offset,
    ad.avg_trips_started,
    ad.avg_trips_ended,
    ad.avg_net_flow,
    ad.num_games,

    -- Rebalancing logic
    -- Negative net_flow = bikes depleting (trips started > trips ended) → ADD bikes
    -- Positive net_flow = bikes accumulating (trips ended > trips started) → REMOVE bikes
    case
        when ad.avg_net_flow < -10 then round(abs(ad.avg_net_flow))  -- Add bikes (positive number)
        when ad.avg_net_flow > 10 then -1 * round(ad.avg_net_flow)   -- Remove bikes (negative number)
        else 0
    end as bikes_to_add_or_remove,

    -- Text recommendation
    case
        when ad.avg_net_flow < -10 then 'Add ' || round(abs(ad.avg_net_flow)) || ' bikes'
        when ad.avg_net_flow > 10 then 'Remove ' || round(ad.avg_net_flow) || ' bikes'
        else 'No action needed'
    end as rebalancing_recommendation,

    -- Percentage capacity adjustment (assuming ~20 bikes per station capacity)
    case
        when ad.avg_net_flow < -10 then round((abs(ad.avg_net_flow) / 20.0) * 100, 1)
        when ad.avg_net_flow > 10 then -1 * round((ad.avg_net_flow / 20.0) * 100, 1)
        else 0
    end as pct_capacity_adjustment

from aggregated_demand ad
left join {{ ref('dim_stations') }} s
    on ad.station_id = s.station_id
where ad.num_games >= 2  -- Only include patterns seen in at least 2 games
order by ad.stadium_name, abs(ad.avg_net_flow) desc, ad.station_id, ad.hour_offset
