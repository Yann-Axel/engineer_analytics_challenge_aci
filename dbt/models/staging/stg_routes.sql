{{ config(materialized='view') }}

with source as (
    select * from {{ source('air_cote_divoire', 'routes') }}
),

renamed as (
    select
        cast(route_id                 as varchar) as route_id,
        cast(origin_airport_code      as varchar) as origin_airport_code,
        cast(destination_airport_code as varchar) as destination_airport_code,
        cast(route_type               as varchar) as route_type,
        cast(distance_km              as integer) as distance_km,
        cast(block_time_min           as integer) as block_time_min,
        cast(route_status             as varchar) as route_status,
        cast(is_strategic             as boolean) as is_strategic,
        current_timestamp                          as _loaded_at
    from source
)

select * from renamed
