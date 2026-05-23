{{ config(materialized='table') }}

-- Grain: 1 row per flight.
with flights as (
    select * from {{ ref('int_flight_full') }}
),
d_route as (
    select route_sk, route_id from {{ ref('dim_route') }}
),
d_aircraft as (
    select aircraft_sk, tail_number from {{ ref('dim_aircraft') }}
),
d_airport as (
    select airport_sk, airport_code from {{ ref('dim_airport') }}
),
d_date as (
    select date_sk, date_day from {{ ref('dim_date') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['f.flight_id']) }} as flight_sk,
    f.flight_id,
    f.flight_number,
    dr.route_sk,
    f.route_id,
    da.aircraft_sk,
    f.tail_number,
    f.aircraft_type,
    ao.airport_sk as origin_airport_sk,
    ad.airport_sk as destination_airport_sk,
    f.origin_airport_code,
    f.destination_airport_code,
    f.route_type,
    f.distance_km,
    dd.date_sk as flight_date_sk,
    f.flight_date,
    f.scheduled_departure_at,
    f.actual_departure_at,
    f.scheduled_arrival_at,
    f.actual_arrival_at,
    f.flight_status,
    f.delay_min,
    f.seat_capacity,
    f.pax_count,
    f.load_factor,
    f.is_on_time_15,
    f.ticket_revenue_usd,
    f.ancillary_revenue_usd,
    f.total_revenue_usd,
    f.fuel_cost_usd,
    f.crew_cost_usd,
    f.airport_fees_usd,
    f.maintenance_alloc_usd,
    f.irops_penalty_usd,
    f.total_operating_cost_usd,
    f.flight_margin_usd,
    f.flight_margin_pct,
    f.disruption_type,
    f.disruption_severity,
    f.disruption_duration_min,
    f.root_cause_text,
    f.origin_weather_severity,
    case when f.flight_status = 'Cancelled' then true else false end as is_cancelled,
    case when f.disruption_type is not null then true else false end as has_disruption
from flights f
left join d_route    dr on f.route_id                = dr.route_id
left join d_aircraft da on f.tail_number             = da.tail_number
left join d_airport  ao on f.origin_airport_code     = ao.airport_code
left join d_airport  ad on f.destination_airport_code = ad.airport_code
left join d_date     dd on f.flight_date             = dd.date_day
