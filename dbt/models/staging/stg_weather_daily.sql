{{ config(materialized='view') }}

with source as (
    select * from {{ source('air_cote_divoire', 'weather_daily') }}
),

renamed as (
    select
        cast(airport_code     as varchar)       as airport_code,
        cast(weather_date     as date)          as weather_date,
        cast(precipitation_mm as decimal(6,1))  as precipitation_mm,
        cast(wind_kph         as decimal(6,1))  as wind_kph,
        cast(severity_flag    as varchar)       as severity_flag,
        current_timestamp                       as _loaded_at
    from source
)

select * from renamed
