{{ config(materialized='view') }}

with source as (
    select * from {{ source('air_cote_divoire', 'aircraft') }}
),

renamed as (
    select
        cast(tail_number       as varchar) as tail_number,
        cast(aircraft_type     as varchar) as aircraft_type,
        cast(manufacturer      as varchar) as manufacturer,
        cast(build_year        as integer) as build_year,
        cast(seats_business    as integer) as seats_business,
        cast(seats_premium_eco as integer) as seats_premium_eco,
        cast(seats_economy     as integer) as seats_economy,
        cast(fleet_status      as varchar) as fleet_status,
        cast(total_seats       as integer) as total_seats,
        cast(typed_capacity    as integer) as typed_capacity,
        current_timestamp                  as _loaded_at
    from source
)

select * from renamed
