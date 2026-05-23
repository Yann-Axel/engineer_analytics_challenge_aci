{{ config(materialized='table') }}

-- Grain: 1 row per loyalty event (earn or redeem).
with src as (
    select * from {{ ref('stg_loyalty_activity') }}
),
d_customer as (
    select customer_sk, customer_id from {{ ref('dim_customer_current') }}
),
d_route as (
    select route_sk, route_id from {{ ref('dim_route') }}
),
d_date as (
    select date_sk, date_day from {{ ref('dim_date') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['s.loyalty_event_id']) }} as loyalty_event_sk,
    s.loyalty_event_id,
    dc.customer_sk,
    s.customer_id,
    dr.route_sk,
    s.route_id,
    s.flight_id,
    s.tier_at_event,
    s.event_type,
    s.points_delta,
    case when s.event_type = 'earn'   then s.points_delta else 0 end as points_earned,
    case when s.event_type = 'redeem' then -s.points_delta else 0 end as points_redeemed,
    dd.date_sk as event_date_sk,
    cast(s.event_at as date) as event_date,
    s.event_at
from src s
left join d_customer dc on s.customer_id = dc.customer_id
left join d_route    dr on s.route_id    = dr.route_id
left join d_date     dd on cast(s.event_at as date) = dd.date_day
