{{ config(materialized='table') }}

-- Point-in-time "current" customer dimension from the SCD2 snapshot.
-- Used by analyses that need the latest state without time travel.
-- Facts that need point-in-time accurate joins should use the snapshot directly.
with snap as (
    select * from {{ ref('dim_customer_snapshot') }}
    where dbt_valid_to is null  -- current version only
),

enriched as (
    select
        {{ dbt_utils.generate_surrogate_key(['customer_id']) }}     as customer_sk,
        customer_id,
        first_name,
        last_name,
        gender,
        birth_date,
        country,
        city,
        customer_segment,
        loyalty_tier,
        coalesce(loyalty_tier, 'non_member')                          as loyalty_tier_safe,
        case when loyalty_tier is not null then true else false end   as is_loyalty_member,
        signup_date,
        preferred_channel,
        date_diff('year', birth_date, current_date)                   as age_years,
        date_diff('day', signup_date, current_date)                   as tenure_days
    from snap
)

select * from enriched
