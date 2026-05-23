{{ config(materialized='table') }}

-- ONTOLOGY: IROPS-Heavy Route
-- A route showing operational fragility: top-quintile disruption rate
-- OR cancellation rate > 5%. We use OR (not AND) because the two failure modes
-- are distinct: weather/tech disruptions don't always materialise as cancellations,
-- and high cancellation rates can come from causes other than recorded disruptions.
-- Senior choice: relative threshold (top quintile) + absolute (5%) — captures
-- both percentile outliers and any route breaching the 5% cancellation industry
-- "alarm" line.
-- Rule:  disruption_percentile_12m >= 0.80   (top quintile by disruption rate)
--        OR cancellation_rate_12m > 0.05     (cancellation alarm threshold)
-- Owner: COO / Operations Director
-- Refresh: weekly
with flights_12m as (
    select
        f.route_id,
        f.flight_id,
        f.is_cancelled,
        f.has_disruption
    from {{ ref('fct_flights') }} f
    where f.flight_date >= (
        select max(flight_date) from {{ ref('fct_flights') }}
    ) - interval '12 months'
),

per_route as (
    select
        route_id,
        count(*)                                           as total_flights_12m,
        sum(case when is_cancelled    then 1 else 0 end)   as cancellations_12m,
        sum(case when has_disruption  then 1 else 0 end)   as disruptions_12m,
        sum(case when is_cancelled    then 1 else 0 end)::double / count(*) as cancellation_rate_12m,
        sum(case when has_disruption  then 1 else 0 end)::double / count(*) as disruption_rate_12m
    from flights_12m
    group by 1
),

with_rank as (
    select
        *,
        percent_rank() over (order by disruption_rate_12m) as disruption_percentile
    from per_route
),

routes as (
    select route_id, route_type, is_strategic, distance_band from {{ ref('dim_route') }}
)

select
    r.route_id,
    r.route_type,
    r.distance_band,
    r.is_strategic,
    pr.total_flights_12m,
    pr.cancellations_12m,
    pr.disruptions_12m,
    pr.cancellation_rate_12m,
    pr.disruption_rate_12m,
    pr.disruption_percentile,
    'IROPSHeavyRoute'                  as ontology_concept,
    current_timestamp                  as inferred_at
from with_rank pr
join routes    r on pr.route_id = r.route_id
where pr.disruption_percentile  >= 0.80
   or pr.cancellation_rate_12m   > 0.05
