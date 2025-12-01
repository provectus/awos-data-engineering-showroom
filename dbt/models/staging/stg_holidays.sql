{{
    config(
        materialized='view'
    )
}}

with source_holidays as (
    select
        date,
        holiday_name,
        local_name,
        country_code,
        is_fixed,
        is_global,
        counties,
        holiday_types,
        source_year,
        _dlt_load_timestamp
    from {{ source('raw_holidays', 'us_holidays') }}
),

-- Get all distinct years from source holidays
available_years as (
    select distinct source_year
    from source_holidays
),

-- NYC-specific static holidays generated dynamically for all available years
-- These are local NYC events not included in the federal API
nyc_static_holidays as (
    select
        -- NYC Marathon: First Sunday in November
        -- Source: NYRR official schedule
        -- Calculate: November 1st + days until first Sunday
        (source_year || '-11-01')::date +
            interval ((7 - extract(dow from (source_year || '-11-01')::date)::integer) % 7) day as date,
        'NYC Marathon' as holiday_name,
        'NYC Marathon' as local_name,
        'US' as country_code,
        false as is_fixed,
        false as is_global,
        'US-NY' as counties,
        'Local' as holiday_types,
        source_year,
        current_timestamp as _dlt_load_timestamp
    from available_years

    union all

    select
        -- Puerto Rican Day Parade: Second Sunday in June
        -- Source: National Puerto Rican Day Parade official schedule
        -- Calculate: June 1st + days until first Sunday + 7 days for second Sunday
        (source_year || '-06-01')::date +
            interval ((7 - extract(dow from (source_year || '-06-01')::date)::integer) % 7 + 7) day as date,
        'Puerto Rican Day Parade' as holiday_name,
        'Puerto Rican Day Parade' as local_name,
        'US' as country_code,
        false as is_fixed,
        false as is_global,
        'US-NY' as counties,
        'Local' as holiday_types,
        source_year,
        current_timestamp as _dlt_load_timestamp
    from available_years
),

-- Union API-sourced and NYC-specific holidays
all_holidays as (
    select
        date,
        holiday_name,
        local_name,
        country_code,
        is_fixed,
        is_global,
        counties,
        holiday_types,
        source_year,
        _dlt_load_timestamp
    from source_holidays

    union all

    select
        date,
        holiday_name,
        local_name,
        country_code,
        is_fixed,
        is_global,
        counties,
        holiday_types,
        source_year,
        _dlt_load_timestamp
    from nyc_static_holidays
),

-- Deduplicate by date, prioritizing Public/Federal holidays over NYC local holidays
deduplicated as (
    select
        *,
        row_number() over (
            partition by date
            order by
                -- Prioritize Public and Federal types first
                case
                    when holiday_types like '%Public%' then 1
                    when holiday_types like '%Federal%' then 2
                    else 3
                end,
                holiday_name  -- Tie-breaker: alphabetical
        ) as row_num
    from all_holidays
)

select
    date::date as date,  -- Ensure date column is DATE type, not timestamp
    holiday_name,
    local_name,
    country_code,
    is_fixed,
    is_global,
    counties,
    holiday_types,

    -- Derive is_major flag: holidays with 'Public' or 'Federal' type are considered major
    case
        when holiday_types like '%Public%' then true
        when holiday_types like '%Federal%' then true
        else false
    end as is_major,

    -- Derive is_working_day flag: major holidays are non-working days
    case
        when holiday_types like '%Public%' then false
        when holiday_types like '%Federal%' then false
        else true
    end as is_working_day,

    source_year,
    _dlt_load_timestamp

from deduplicated
where row_num = 1  -- Keep only the highest priority holiday per date
