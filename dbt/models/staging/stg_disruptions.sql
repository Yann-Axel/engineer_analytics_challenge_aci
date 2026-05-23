{{ config(materialized='view') }}

with source as (
    select * from {{ source('air_cote_divoire', 'disruptions') }}
),

renamed as (
    select
        cast(disruption_id   as varchar) as disruption_id,
        cast(flight_id       as varchar) as flight_id,
        cast(disruption_type as varchar) as disruption_type,
        cast(severity        as varchar) as severity,
        cast(duration_min    as integer) as duration_min,
        cast(root_cause_text as varchar) as root_cause_text,
        current_timestamp                as _loaded_at
    from source
)

select * from renamed
