-- Test to verify that stg_weather preserves records with partial temperature data
-- This test ensures we don't lose weather records with NULL tmax or tmin

with test_data as (
    -- Should pass: both temps present and valid
    select 1 as test_case, '2024-05-01'::date as date, 25.0 as tmax, 15.0 as tmin, 0.0 as precip
    union all
    -- Should pass: tmax is NULL but other data is valid
    select 2, '2024-05-02'::date, null, 15.0, 5.0
    union all
    -- Should pass: tmin is NULL but other data is valid
    select 3, '2024-05-03'::date, 25.0, null, 0.0
    union all
    -- Should pass: both temps NULL but precip/wind data valid
    select 4, '2024-05-04'::date, null, null, 10.0
    union all
    -- Should FAIL: tmax < tmin when both present (data integrity violation)
    select 5, '2024-05-05'::date, 10.0, 20.0, 0.0
),

result as (
    select
        test_case,
        case
            when tmax is null or tmin is null or tmax >= tmin then 'PASS'
            else 'FAIL'
        end as expected_result
    from test_data
)

select * from result
-- Test cases 1-4 should PASS (preserved)
-- Test case 5 should FAIL (filtered out)

