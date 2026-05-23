{{ config(materialized='table') }}

-- ONTOLOGY: Loyal Detractor (early-warning retention signal)
-- A Gold-tier frequent flyer whose recent feedback skews negative.
-- Rule:  loyalty_tier = 'Gold'
--        AND frequency_12m >= 4
--        AND avg_sentiment_6m < -0.3
-- Owner: Loyalty Manager
-- Refresh: weekly
with customers_gold as (
    select customer_sk, customer_id, loyalty_tier, customer_segment
    from {{ ref('dim_customer_current') }}
    where loyalty_tier = 'Gold'
),

frequency as (
    select customer_id, frequency_12m
    from {{ ref('int_customer_rfm') }}
),

recent_sentiment as (
    -- 6-month rolling window from latest observed feedback_date
    select
        customer_id,
        count(*)                          as feedback_count_6m,
        avg(sentiment_score)              as avg_sentiment_6m,
        sum(case when sentiment_label = 'negative' then 1 else 0 end) as negative_count_6m
    from {{ ref('fct_customer_feedback') }}
    where feedback_date >= (
        select max(feedback_date) from {{ ref('fct_customer_feedback') }}
    ) - interval '180 days'
    group by 1
),

joined as (
    select
        c.customer_id,
        c.customer_segment,
        c.loyalty_tier,
        f.frequency_12m,
        rs.feedback_count_6m,
        rs.avg_sentiment_6m,
        rs.negative_count_6m
    from customers_gold c
    join frequency        f  on c.customer_id = f.customer_id
    join recent_sentiment rs on c.customer_id = rs.customer_id
)

select
    customer_id,
    customer_segment,
    loyalty_tier,
    frequency_12m,
    feedback_count_6m,
    avg_sentiment_6m,
    negative_count_6m,
    'LoyalDetractor'                as ontology_concept,
    current_timestamp                as inferred_at
from joined
where frequency_12m   >= 4
  and avg_sentiment_6m < -0.3
