{{
    config(
        materialized='table'
    )
}}

-- Static stadium dimension with geocoded coordinates
-- Coordinates verified with geopy for accurate proximity calculations
select * from (
    values
        (
            1,
            'Yankee Stadium',
            '1 E 161st St, Bronx, NY 10451',
            40.8296,
            -73.9265,
            'Bronx',
            'NY',
            current_timestamp
        ),
        (
            2,
            'Citi Field',
            '41 Seaver Way, Queens, NY 11368',
            40.7573,
            -73.8459,
            'Queens',
            'NY',
            current_timestamp
        )
) as stadiums(
    stadium_id,
    stadium_name,
    address,
    latitude,
    longitude,
    city,
    state,
    geocoded_at
)
