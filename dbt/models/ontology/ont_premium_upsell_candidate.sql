{{ config(materialized='table') }}

-- ONTOLOGY: Premium Upsell Candidate
-- A customer in Standard/Business segment with Silver/Gold tier
-- whose acceptance of upgrade offers ranks in the top quartile.
-- Rule:  customer_segment IN ('Standard', 'Business')
--        AND loyalty_tier IN ('Silver', 'Gold')
--        AND upgrade_acceptance_rate >= P75
-- Owner: Ancillary Manager
-- Refresh: monthly
with customer_segments as (
    select customer_sk, customer_id, customer_segment, loyalty_tier
    from {{ ref('dim_customer_current') }}
    where customer_segment in ('Standard', 'Business')
      and loyalty_tier     in ('Silver', 'Gold')
),

offers as (
    select * from {{ ref('fct_ancillary_offers') }}
    where offer_type in ('upgrade_W', 'upgrade_J')
),

per_customer as (
    select
        o.customer_id,
        count(*) filter (where o.presented_flag) as presented,
        count(*) filter (where o.accepted_flag)  as accepted,
        case when count(*) filter (where o.presented_flag) > 0
             then (count(*) filter (where o.accepted_flag))::double
                  / count(*) filter (where o.presented_flag)
             else 0 end                          as upgrade_acceptance_rate
    from offers o
    join customer_segments cs on o.customer_id = cs.customer_id
    group by 1
),

with_rank as (
    select
        *,
        percent_rank() over (order by upgrade_acceptance_rate) as acceptance_percentile
    from per_customer
)

select
    cs.customer_id,
    cs.customer_segment,
    cs.loyalty_tier,
    pc.presented           as upgrade_offers_presented,
    pc.accepted            as upgrade_offers_accepted,
    pc.upgrade_acceptance_rate,
    pc.acceptance_percentile,
    'PremiumUpsellCandidate' as ontology_concept,
    current_timestamp        as inferred_at
from customer_segments cs
join with_rank pc on cs.customer_id = pc.customer_id
where pc.acceptance_percentile >= 0.75
  and pc.presented >= 2
