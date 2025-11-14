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
)

select
    date,
    holiday_name,
    local_name,
    country_code,
    is_fixed,
    is_global,
    counties,
    holiday_types,

    -- Derive is_major flag: holidays with 'Public' type are considered major
    -- Public holidays get priority in the merge logic
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

from source_holidays
