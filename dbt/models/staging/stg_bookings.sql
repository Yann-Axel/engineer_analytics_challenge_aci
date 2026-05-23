{{ config(materialized='view') }}

with source as (
    select * from {{ source('air_cote_divoire', 'bookings') }}
),

renamed as (
    select
        cast(booking_id            as varchar)        as booking_id,
        cast(booking_date          as date)           as booking_date,
        cast(customer_id           as varchar)        as customer_id,
        cast(flight_id             as varchar)        as flight_id,
        cast(booking_channel       as varchar)        as booking_channel,
        cast(fare_class            as varchar)        as fare_class,
        cast(fare_family           as varchar)        as fare_family,
        cast(ticket_price_usd      as decimal(10,2))  as ticket_price_usd,
        cast(ancillary_revenue_usd as decimal(10,2))  as ancillary_revenue_usd,
        cast(bags_count            as integer)        as bags_count,
        cast(seat_selection_flag   as integer)        as seat_selection_flag,
        cast(booking_status        as varchar)        as booking_status,
        current_timestamp                              as _loaded_at
    from source
)

select * from renamed
