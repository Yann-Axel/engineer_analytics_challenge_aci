{{ config(materialized='table') }}

-- Grain: 1 row per ancillary offer presented to a booking.
with offers as (
    select * from {{ ref('stg_ancillary_offers') }}
),
bookings as (
    select booking_id, customer_id, flight_id, fare_class, fare_family
    from {{ ref('stg_bookings') }}
),
d_customer as (
    select customer_sk, customer_id, customer_segment, loyalty_tier
    from {{ ref('dim_customer_current') }}
),
d_fare as (
    select fare_sk, fare_class, fare_family from {{ ref('dim_fare') }}
),
d_date as (
    select date_sk, date_day from {{ ref('dim_date') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['o.ancillary_offer_id']) }} as ancillary_offer_sk,
    o.ancillary_offer_id,
    o.booking_id,
    dc.customer_sk,
    b.customer_id,
    dc.customer_segment,
    dc.loyalty_tier,
    b.flight_id,
    dfare.fare_sk,
    b.fare_class,
    b.fare_family,
    dd.date_sk as offer_date_sk,
    cast(o.offer_at as date) as offer_date,
    o.offer_at,
    o.offer_type,
    o.offer_price_usd,
    o.presented_flag,
    o.accepted_flag,
    case when o.accepted_flag then o.offer_price_usd else 0 end as accepted_revenue_usd
from offers o
join bookings        b     on o.booking_id    = b.booking_id
left join d_customer dc    on b.customer_id   = dc.customer_id
left join d_fare     dfare on b.fare_class    = dfare.fare_class
                            and b.fare_family = dfare.fare_family
left join d_date     dd    on cast(o.offer_at as date) = dd.date_day
