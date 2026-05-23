{{ config(materialized='table') }}

-- Materialised because reused by fct_flights + ontology layer.
-- One row per flight, enriched with cost, pax, revenue, disruption, weather.
with flights as (
    select * from {{ ref('stg_flights') }}
),
costs as (
    select * from {{ ref('stg_flight_costs') }}
),
pax as (
    select * from {{ ref('int_flight_passenger_count') }}
),
revenue as (
    select * from {{ ref('int_flight_revenue') }}
),
disruption as (
    -- A flight can have at most 1 disruption in our model
    select
        flight_id,
        disruption_type,
        severity,
        duration_min as disruption_duration_min,
        root_cause_text
    from {{ ref('stg_disruptions') }}
),
weather as (
    -- Weather at origin airport on flight_date
    select
        airport_code,
        weather_date,
        severity_flag as weather_severity
    from {{ ref('stg_weather_daily') }}
),
routes as (
    select route_id, origin_airport_code, destination_airport_code, route_type, distance_km
    from {{ ref('stg_routes') }}
)

select
    f.flight_id,
    f.flight_number,
    f.route_id,
    r.origin_airport_code,
    r.destination_airport_code,
    r.route_type,
    r.distance_km,
    f.tail_number,
    f.aircraft_type,
    f.flight_date,
    f.scheduled_departure_at,
    f.actual_departure_at,
    f.scheduled_arrival_at,
    f.actual_arrival_at,
    f.seat_capacity,
    f.flight_status,
    f.delay_min,
    coalesce(p.pax_flown, 0)              as pax_count,
    coalesce(rev.ticket_revenue_usd, 0)   as ticket_revenue_usd,
    coalesce(rev.ancillary_revenue_usd, 0) as ancillary_revenue_usd,
    coalesce(rev.total_revenue_usd, 0)    as total_revenue_usd,
    c.fuel_cost_usd,
    c.crew_cost_usd,
    c.airport_fees_usd,
    c.maintenance_alloc_usd,
    c.irops_penalty_usd,
    c.total_operating_cost_usd,
    -- Derived: margin
    coalesce(rev.total_revenue_usd, 0) - coalesce(c.total_operating_cost_usd, 0)
        as flight_margin_usd,
    case
        when coalesce(rev.total_revenue_usd, 0) > 0 then
            (coalesce(rev.total_revenue_usd, 0) - coalesce(c.total_operating_cost_usd, 0))
            / rev.total_revenue_usd
        else null
    end as flight_margin_pct,
    -- Derived: load factor
    case when f.seat_capacity > 0 then coalesce(p.pax_flown, 0)::double / f.seat_capacity
         else null end as load_factor,
    -- Derived: on-time flag (≤15 min)
    case when f.flight_status = 'Cancelled' then null
         when f.delay_min <= 15 then true else false end as is_on_time_15,
    d.disruption_type,
    d.severity                as disruption_severity,
    d.disruption_duration_min,
    d.root_cause_text,
    w.weather_severity as origin_weather_severity
from flights f
left join routes     r   on f.route_id    = r.route_id
left join costs      c   on f.flight_id   = c.flight_id
left join pax        p   on f.flight_id   = p.flight_id
left join revenue    rev on f.flight_id   = rev.flight_id
left join disruption d   on f.flight_id   = d.flight_id
left join weather    w   on r.origin_airport_code = w.airport_code
                        and f.flight_date         = w.weather_date
