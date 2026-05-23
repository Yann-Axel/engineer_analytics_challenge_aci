{{ config(materialized='table') }}

with src as (
    select * from {{ ref('stg_airports') }}
)

select
    -- Surrogate key (deterministic)
    {{ dbt_utils.generate_surrogate_key(['airport_code']) }}     as airport_sk,
    airport_code,
    airport_name,
    city,
    country,
    timezone,
    latitude,
    longitude,
    -- Derived: hub flag (ABJ is the home hub)
    case when airport_code = 'ABJ' then true else false end       as is_hub,
    -- Derived: country group
    case
        when country in ('Côte d''Ivoire', 'Ghana', 'Senegal', 'Nigeria',
                         'Benin', 'Burkina Faso', 'Togo')              then 'West Africa'
        when country in ('Morocco')                                     then 'North Africa'
        when country in ('UAE')                                         then 'Middle East'
        when country in ('France')                                      then 'Europe'
        else 'Other'
    end                                                            as country_group
from src
