-- Test that stg_weather doesn't drop records with partial temperature data
-- This test verifies the fix for the NULL-handling bug in the WHERE clause

-- This test should return 0 rows if working correctly
-- If it returns rows, it means we're incorrectly filtering valid records

with source_counts as (
    select count(*) as raw_count
    from {{ source('raw_weather', 'daily_weather') }}
    where date is not null
),

staged_counts as (
    select count(*) as staged_count
    from {{ ref('stg_weather') }}
),

-- Check if we're losing records that should be preserved
potential_data_loss as (
    select
        s.raw_count,
        st.staged_count,
        (s.raw_count - st.staged_count) as records_lost
    from source_counts s
    cross join staged_counts st
)

-- This test fails if we lose more than 1% of records
-- (allowing for legitimate data quality filtering)
select *
from potential_data_loss
where records_lost > (raw_count * 0.01)

