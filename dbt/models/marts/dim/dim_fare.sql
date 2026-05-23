{{ config(materialized='table') }}

-- Fare dimension is the cross of fare_class × fare_family.
-- We build it from the distinct combinations observed in bookings.
with combos as (
    select distinct fare_class, fare_family
    from {{ ref('stg_bookings') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['fare_class', 'fare_family']) }} as fare_sk,
    fare_class,
    fare_family,
    -- Rules-of-thumb to drive dashboard semantics
    case fare_class
        when 'Business'         then 'J'
        when 'Premium Economy'  then 'W'
        when 'Economy'          then 'Y'
    end                                                                    as cabin_code,
    case fare_family
        when 'Basic'      then 'restrictive'
        when 'Standard'   then 'standard'
        when 'Flex'       then 'flexible'
    end                                                                    as fare_rule_band,
    case
        when fare_class = 'Business'        then true
        when fare_class = 'Premium Economy' then true
        else false
    end                                                                    as is_premium_cabin
from combos
