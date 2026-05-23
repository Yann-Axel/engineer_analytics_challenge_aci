{{ config(materialized='ephemeral') }}

-- Number of flown passengers per flight.
-- Grain: 1 row per flight_id (only flights with at least 1 flown booking).
with flown as (
    select
        flight_id,
        count(*)                       as pax_flown,
        count(distinct customer_id)    as unique_pax
    from {{ ref('stg_bookings') }}
    where booking_status = 'Flown'
    group by 1
)

select * from flown
