{{ config(materialized='table') }}

-- Grain: 1 row per booking.
-- customer_sk uses the SCD2 snapshot to capture the tier valid at booking time.
with bookings as (
    select * from {{ ref('stg_bookings') }}
),
d_customer as (
    -- Versioned customer: pick the snapshot row valid at booking_date
    select
        customer_id,
        loyalty_tier,
        customer_segment,
        dbt_scd_id,
        dbt_valid_from,
        dbt_valid_to
    from {{ ref('dim_customer_snapshot') }}
),
d_customer_current as (
    -- Fallback for bookings predating the first snapshot run.
    -- With synthetic historical data the snapshot's dbt_valid_from is the
    -- seed timestamp (2026-05-24), which is after every booking_date.
    -- In production with continuous snapshotting, this fallback only fires
    -- during the initial seed window.
    select customer_id, loyalty_tier, customer_segment
    from {{ ref('dim_customer_current') }}
),
d_route_via_flight as (
    select f.flight_id, f.route_id, dr.route_sk, f.tail_number, f.aircraft_type
    from {{ ref('stg_flights') }} f
    join {{ ref('dim_route') }} dr on f.route_id = dr.route_id
),
d_flight as (
    select flight_sk, flight_id, flight_date, flight_date_sk
    from {{ ref('fct_flights') }}
),
d_fare as (
    select fare_sk, fare_class, fare_family, is_premium_cabin from {{ ref('dim_fare') }}
),
d_date as (
    select date_sk, date_day from {{ ref('dim_date') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['b.booking_id']) }} as booking_sk,
    b.booking_id,
    -- Point-in-time SCD2 join: pick the customer version valid at booking_date
    {{ dbt_utils.generate_surrogate_key(['dc.dbt_scd_id']) }} as customer_version_sk,
    b.customer_id,
    coalesce(dc.loyalty_tier,     dcc.loyalty_tier)     as loyalty_tier_at_booking,
    coalesce(dc.customer_segment, dcc.customer_segment) as customer_segment_at_booking,
    df.flight_sk,
    b.flight_id,
    dr.route_sk,
    dr.route_id,
    dr.tail_number,
    dr.aircraft_type,
    dfare.fare_sk,
    b.fare_class,
    b.fare_family,
    dfare.is_premium_cabin,
    dd_book.date_sk    as booking_date_sk,
    b.booking_date,
    df.flight_date_sk,
    df.flight_date,
    b.booking_channel,
    b.booking_status,
    b.ticket_price_usd,
    b.ancillary_revenue_usd,
    b.ticket_price_usd + b.ancillary_revenue_usd as total_booking_revenue_usd,
    b.bags_count,
    b.seat_selection_flag,
    case when b.booking_status = 'Flown' then true else false end as is_flown
from bookings b
left join d_customer         dc       on b.customer_id = dc.customer_id
                                       and b.booking_date >= cast(dc.dbt_valid_from as date)
                                       and (dc.dbt_valid_to is null
                                            or b.booking_date < cast(dc.dbt_valid_to as date))
left join d_customer_current dcc      on b.customer_id = dcc.customer_id
left join d_route_via_flight dr       on b.flight_id    = dr.flight_id
left join d_flight           df       on b.flight_id    = df.flight_id
left join d_fare             dfare    on b.fare_class   = dfare.fare_class
                                       and b.fare_family = dfare.fare_family
left join d_date             dd_book  on b.booking_date = dd_book.date_day
