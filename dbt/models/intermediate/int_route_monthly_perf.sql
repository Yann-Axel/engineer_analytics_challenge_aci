{{ config(materialized='table') }}

-- Pre-aggregated route × month KPIs.
-- Drives the route-optimization theme in the dashboard and the ontology layer.
with flights as (
    select
        route_id,
        date_trunc('month', flight_date)::date as period_month,
        flight_status,
        seat_capacity,
        pax_count,
        total_revenue_usd,
        total_operating_cost_usd,
        is_on_time_15,
        flight_id
    from {{ ref('int_flight_full') }}
)

select
    route_id,
    period_month,
    count(*)                                                  as flights_scheduled,
    sum(case when flight_status = 'Cancelled' then 1 else 0 end)  as flights_cancelled,
    sum(case when flight_status <> 'Cancelled' then 1 else 0 end) as flights_operated,
    sum(pax_count)                                            as total_pax,
    sum(seat_capacity)                                        as total_seat_capacity,
    sum(total_revenue_usd)                                    as revenue_usd,
    sum(total_operating_cost_usd)                             as operating_cost_usd,
    sum(total_revenue_usd) - sum(total_operating_cost_usd)    as margin_usd,
    case when sum(total_revenue_usd) > 0
         then (sum(total_revenue_usd) - sum(total_operating_cost_usd))
              / sum(total_revenue_usd)
         else null end                                        as margin_pct,
    case when sum(seat_capacity) > 0
         then sum(pax_count)::double / sum(seat_capacity)
         else null end                                        as load_factor,
    case when count(*) > 0
         then sum(case when flight_status = 'Cancelled' then 1 else 0 end)::double / count(*)
         else null end                                        as cancellation_rate,
    case when sum(case when flight_status <> 'Cancelled' then 1 else 0 end) > 0
         then sum(case when is_on_time_15 then 1 else 0 end)::double
              / sum(case when flight_status <> 'Cancelled' then 1 else 0 end)
         else null end                                        as otp15_rate
from flights
group by 1, 2
