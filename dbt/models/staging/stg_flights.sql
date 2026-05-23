{{ config(materialized='view') }}

with source as (
    select * from {{ source('air_cote_divoire', 'flights') }}
),

renamed as (
    select
        cast(flight_id            as varchar)   as flight_id,
        cast(flight_number        as varchar)   as flight_number,
        cast(route_id             as varchar)   as route_id,
        cast(tail_number          as varchar)   as tail_number,
        cast(flight_date          as date)      as flight_date,
        cast(scheduled_departure  as timestamp) as scheduled_departure_at,
        cast(actual_departure     as timestamp) as actual_departure_at,
        cast(scheduled_arrival    as timestamp) as scheduled_arrival_at,
        cast(actual_arrival       as timestamp) as actual_arrival_at,
        cast(aircraft_type        as varchar)   as aircraft_type,
        cast(seat_capacity        as integer)   as seat_capacity,
        cast(flight_status        as varchar)   as flight_status,
        cast(delay_min            as integer)   as delay_min,
        current_timestamp                       as _loaded_at
    from source
)

select * from renamed
