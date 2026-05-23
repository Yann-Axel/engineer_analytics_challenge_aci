{{ config(materialized='table') }}

-- ONTOLOGY: Strategic but Underperforming Route
-- A strategic route whose 12-month margin sits in the bottom half of all strategic
-- routes' margins AND whose load factor is decent (>= 0.65) — i.e. demand exists
-- but profitability lags peers.
-- Senior choice: relative threshold (bottom 50% of strategic peers) rather than
-- absolute "margin < 15%", since synthetic costs may not match real airline economics.
-- Rule:  is_strategic = true
--        AND margin_pct_12m <= median margin across strategic routes
--        AND load_factor_12m >= 0.65
-- Owner: VP Network
-- Refresh: monthly
with monthly as (
    select * from {{ ref('int_route_monthly_perf') }}
),
routes as (
    select route_sk, route_id, route_type, is_strategic, distance_band
    from {{ ref('dim_route') }}
),
twelve_month as (
    select
        m.route_id,
        sum(m.flights_operated)             as flights_operated_12m,
        sum(m.total_pax)                    as total_pax_12m,
        sum(m.total_seat_capacity)          as total_capacity_12m,
        sum(m.revenue_usd)                  as revenue_12m,
        sum(m.operating_cost_usd)           as cost_12m,
        sum(m.margin_usd)                   as margin_12m_usd,
        case when sum(m.revenue_usd) > 0
             then (sum(m.revenue_usd) - sum(m.operating_cost_usd)) / sum(m.revenue_usd)
             else null end                  as margin_pct_12m,
        case when sum(m.total_seat_capacity) > 0
             then sum(m.total_pax)::double / sum(m.total_seat_capacity)
             else null end                  as load_factor_12m,
        avg(m.cancellation_rate)            as avg_cancellation_rate,
        avg(m.otp15_rate)                   as avg_otp15
    from monthly m
    where m.period_month >= (select max(period_month) from monthly) - interval '12 months'
    group by 1
),

strategic_perf as (
    select r.*, t.*
    from twelve_month t
    join routes r on t.route_id = r.route_id
    where r.is_strategic = true
),

with_rank as (
    select
        *,
        percent_rank() over (order by margin_pct_12m) as margin_percentile_among_strategic
    from strategic_perf
)

select
    route_id,
    route_type,
    distance_band,
    flights_operated_12m,
    revenue_12m,
    cost_12m,
    margin_12m_usd,
    margin_pct_12m,
    margin_percentile_among_strategic,
    load_factor_12m,
    avg_cancellation_rate,
    avg_otp15,
    'StrategicUnderperformingRoute' as ontology_concept,
    current_timestamp               as inferred_at
from with_rank
where margin_percentile_among_strategic <= 0.50
  and coalesce(load_factor_12m, 0) >= 0.65
