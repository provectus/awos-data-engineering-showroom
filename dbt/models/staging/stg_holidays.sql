{{
    config(
        materialized='view'
    )
}}

with source as (
    select * from {{ source('raw_holidays', 'us_holidays') }}
),

cleaned as (
    select
        cast(date as date) as date,
        trim(holiday_name) as holiday_name,
        trim(local_name) as local_name,
        cast(is_nationwide as boolean) as is_nationwide,
        cast(is_fixed as boolean) as is_fixed,
        trim(holiday_types) as holiday_types,
        case
            when counties is null then null
            else trim(counties)
        end as counties,
        _dlt_load_timestamp
    from source
)

select * from cleaned
