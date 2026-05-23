{{ config(materialized='view') }}

with source as (
    select * from {{ source('air_cote_divoire', 'flight_costs') }}
),

renamed as (
    select
        cast(flight_id                as varchar)        as flight_id,
        cast(block_hours              as decimal(8,3))   as block_hours,
        cast(fuel_cost_usd            as decimal(10,2))  as fuel_cost_usd,
        cast(crew_cost_usd            as decimal(10,2))  as crew_cost_usd,
        cast(airport_fees_usd         as decimal(10,2))  as airport_fees_usd,
        cast(maintenance_alloc_usd    as decimal(10,2))  as maintenance_alloc_usd,
        cast(irops_penalty_usd        as decimal(10,2))  as irops_penalty_usd,
        cast(total_operating_cost_usd as decimal(10,2))  as total_operating_cost_usd,
        current_timestamp                                as _loaded_at
    from source
)

select * from renamed
