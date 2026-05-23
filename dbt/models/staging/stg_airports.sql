{{ config(materialized='view') }}

-- Staging — 1:1 cast of source airports table.
with source as (
    select * from {{ source('air_cote_divoire', 'airports') }}
),

renamed as (
    select
        cast(airport_code as varchar) as airport_code,
        cast(airport_name as varchar) as airport_name,
        cast(city         as varchar) as city,
        cast(country      as varchar) as country,
        cast(timezone     as varchar) as timezone,
        cast(latitude     as double)  as latitude,
        cast(longitude    as double)  as longitude,
        current_timestamp             as _loaded_at
    from source
)

select * from renamed
