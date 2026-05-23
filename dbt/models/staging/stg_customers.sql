{{ config(materialized='view') }}

with source as (
    select * from {{ source('air_cote_divoire', 'customers') }}
),

renamed as (
    select
        cast(customer_id        as varchar)   as customer_id,
        cast(first_name         as varchar)   as first_name,
        cast(last_name          as varchar)   as last_name,
        cast(gender             as varchar)   as gender,
        cast(birth_date         as date)      as birth_date,
        cast(country            as varchar)   as country,
        cast(city               as varchar)   as city,
        cast(customer_segment   as varchar)   as customer_segment,
        cast(loyalty_tier       as varchar)   as loyalty_tier,
        cast(signup_date        as date)      as signup_date,
        cast(preferred_channel  as varchar)   as preferred_channel,
        current_timestamp                     as _loaded_at
    from source
)

select * from renamed
