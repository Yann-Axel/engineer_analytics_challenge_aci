{{ config(materialized='table') }}

with src as (
    select * from {{ ref('stg_routes') }}
),

airports as (
    select airport_sk, airport_code from {{ ref('dim_airport') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['r.route_id']) }} as route_sk,
    r.route_id,
    a_o.airport_sk as origin_airport_sk,
    a_d.airport_sk as destination_airport_sk,
    r.origin_airport_code,
    r.destination_airport_code,
    r.route_type,
    r.distance_km,
    r.block_time_min,
    r.route_status,
    r.is_strategic,
    -- Derived: distance band
    case
        when r.distance_km < 800              then 'short_haul'
        when r.distance_km < 3500             then 'medium_haul'
        else                                       'long_haul'
    end as distance_band
from src r
left join airports a_o on r.origin_airport_code      = a_o.airport_code
left join airports a_d on r.destination_airport_code = a_d.airport_code
