{{ config(materialized='ephemeral') }}

-- Revenue aggregation per flight: ticket + ancillary on Flown bookings.
with revenue as (
    select
        flight_id,
        sum(ticket_price_usd)        as ticket_revenue_usd,
        sum(ancillary_revenue_usd)   as ancillary_revenue_usd,
        sum(ticket_price_usd + ancillary_revenue_usd) as total_revenue_usd
    from {{ ref('stg_bookings') }}
    where booking_status = 'Flown'
    group by 1
)

select * from revenue
