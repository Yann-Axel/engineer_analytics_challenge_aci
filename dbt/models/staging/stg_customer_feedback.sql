{{ config(materialized='view') }}

-- Unstructured feedback: free text only at this stage.
-- NLP scoring (sentiment, category, tags) happens downstream in intermediate/nlp/.
with source as (
    select * from {{ source('air_cote_divoire', 'customer_feedback') }}
),

renamed as (
    select
        cast(feedback_id        as varchar)   as feedback_id,
        cast(customer_id        as varchar)   as customer_id,
        cast(booking_id         as varchar)   as booking_id,
        cast(flight_id          as varchar)   as flight_id,
        cast(route_id           as varchar)   as route_id,
        cast(feedback_channel   as varchar)   as feedback_channel,
        cast(feedback_date      as timestamp) as feedback_at,
        cast(language           as varchar)   as language_raw,
        cast(raw_text           as varchar)   as raw_text,
        -- normalised lowercase version for downstream NLP matching
        lower(cast(raw_text as varchar))      as normalised_text,
        current_timestamp                     as _loaded_at
    from source
)

select * from renamed
