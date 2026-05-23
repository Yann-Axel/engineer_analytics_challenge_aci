{{ config(materialized='view') }}

with source as (
    select * from {{ source('air_cote_divoire', 'competitors') }}
),

renamed as (
    select
        cast(route_id          as varchar)        as route_id,
        cast(competitor_name   as varchar)        as competitor_name,
        cast(snapshot_month    as date)           as snapshot_month,
        cast(avg_fare_usd      as decimal(10,2))  as avg_fare_usd,
        cast(weekly_frequency  as integer)        as weekly_frequency,
        current_timestamp                         as _loaded_at
    from source
)

select * from renamed
