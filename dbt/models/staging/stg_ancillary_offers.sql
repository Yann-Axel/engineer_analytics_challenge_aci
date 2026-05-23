{{ config(materialized='view') }}

with source as (
    select * from {{ source('air_cote_divoire', 'ancillary_offers') }}
),

renamed as (
    select
        cast(ancillary_offer_id as varchar)        as ancillary_offer_id,
        cast(booking_id         as varchar)        as booking_id,
        cast(offer_type         as varchar)        as offer_type,
        cast(offer_price_usd    as decimal(10,2))  as offer_price_usd,
        cast(presented_flag     as boolean)        as presented_flag,
        cast(accepted_flag      as boolean)        as accepted_flag,
        cast(offer_date         as timestamp)      as offer_at,
        current_timestamp                          as _loaded_at
    from source
)

select * from renamed
