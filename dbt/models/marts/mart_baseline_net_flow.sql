{{
    config(
        materialized='table'
    )
}}

-- Baseline Net Flow Calculations
-- Historical average net flow by cluster, day-of-week, and hour
-- Used as foundation for factor-based demand forecasting

with trip_counts as (
    select
        -- Join to get cluster assignment
        c.cluster_id,

        -- Time dimensions
        extract(dayofweek from t.started_at) as day_of_week,  -- 0=Sunday, 6=Saturday
        extract(hour from t.started_at) as hour,

        -- Trip counts for started trips (bikes leaving the cluster)
        count(*) as trips_started

    from {{ ref('stg_bike_trips') }} t
    inner join {{ ref('dim_station_clusters') }} c
        on t.start_station_id = c.station_id

    group by c.cluster_id, day_of_week, hour
),

trip_ends as (
    select
        -- Join to get cluster assignment
        c.cluster_id,

        -- Time dimensions (use ended_at for trip ends)
        extract(dayofweek from t.ended_at) as day_of_week,
        extract(hour from t.ended_at) as hour,

        -- Trip counts for ended trips (bikes arriving to the cluster)
        count(*) as trips_ended

    from {{ ref('stg_bike_trips') }} t
    inner join {{ ref('dim_station_clusters') }} c
        on t.end_station_id = c.station_id

    group by c.cluster_id, day_of_week, hour
),

combined as (
    select
        coalesce(s.cluster_id, e.cluster_id) as cluster_id,
        coalesce(s.day_of_week, e.day_of_week) as day_of_week,
        coalesce(s.hour, e.hour) as hour,
        coalesce(s.trips_started, 0) as trips_started,
        coalesce(e.trips_ended, 0) as trips_ended

    from trip_counts s
    full outer join trip_ends e
        on s.cluster_id = e.cluster_id
        and s.day_of_week = e.day_of_week
        and s.hour = e.hour
)

select
    cluster_id,
    day_of_week,
    hour,

    -- Average trip counts (currently just raw totals, will become averages when we have multiple weeks)
    trips_started,
    trips_ended,

    -- Net flow calculation
    -- Negative = bikes depleting (trips_started > trips_ended) → need to ADD bikes
    -- Positive = bikes accumulating (trips_ended > trips_started) → need to REMOVE bikes
    (trips_ended - trips_started) as net_flow,

    -- Helper columns for dashboard
    case
        when day_of_week = 0 then 'Sunday'
        when day_of_week = 1 then 'Monday'
        when day_of_week = 2 then 'Tuesday'
        when day_of_week = 3 then 'Wednesday'
        when day_of_week = 4 then 'Thursday'
        when day_of_week = 5 then 'Friday'
        when day_of_week = 6 then 'Saturday'
    end as day_name,

    -- Format hour for display (e.g., "14:00")
    lpad(cast(hour as varchar), 2, '0') || ':00' as hour_label

from combined
order by cluster_id, day_of_week, hour
