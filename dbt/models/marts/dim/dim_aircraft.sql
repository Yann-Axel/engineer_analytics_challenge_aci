{{ config(materialized='table') }}

with src as (
    select * from {{ ref('stg_aircraft') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['tail_number']) }} as aircraft_sk,
    tail_number,
    aircraft_type,
    manufacturer,
    build_year,
    fleet_status,
    seats_business,
    seats_premium_eco,
    seats_economy,
    total_seats,
    typed_capacity,
    -- Derived: age in years (relative to reference year 2026 = latest flight year + 1)
    2026 - build_year                                       as age_years,
    -- Derived: widebody flag (long-haul capable)
    case when aircraft_type = 'A330-900neo' then true else false end as is_widebody
from src
