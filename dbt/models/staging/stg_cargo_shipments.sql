{{ config(materialized='view') }}

with source as (
    select * from {{ source('air_cote_divoire', 'cargo_shipments') }}
),

renamed as (
    select
        cast(cargo_shipment_id as varchar)        as cargo_shipment_id,
        cast(flight_id         as varchar)        as flight_id,
        cast(weight_kg         as decimal(10,1))  as weight_kg,
        cast(revenue_usd       as decimal(10,2))  as revenue_usd,
        cast(cargo_type        as varchar)        as cargo_type,
        cast(shipper_country   as varchar)        as shipper_country,
        current_timestamp                         as _loaded_at
    from source
)

select * from renamed
