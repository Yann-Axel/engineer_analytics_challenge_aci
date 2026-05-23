{{ config(materialized='view') }}

with source as (
    select * from {{ source('air_cote_divoire', 'loyalty_activity') }}
),

renamed as (
    select
        cast(loyalty_event_id as varchar)   as loyalty_event_id,
        cast(customer_id      as varchar)   as customer_id,
        cast(tier_at_event    as varchar)   as tier_at_event,
        cast(event_type       as varchar)   as event_type,
        cast(points_delta     as integer)   as points_delta,
        cast(event_date       as timestamp) as event_at,
        cast(flight_id        as varchar)   as flight_id,
        cast(route_id         as varchar)   as route_id,
        current_timestamp                   as _loaded_at
    from source
)

select * from renamed
