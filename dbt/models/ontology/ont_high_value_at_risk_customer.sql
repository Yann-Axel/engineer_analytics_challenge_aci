{{ config(materialized='table') }}

-- ONTOLOGY: High-Value At-Risk Customer
-- Captures customers with substantial lifetime spend who are now disengaging
-- (above-median recency) AND signalling dissatisfaction.
-- Senior choice: thresholds are percentile-based (robust across datasets).
-- We use TOTAL monetary (lifetime value) rather than 12m because, on a short
-- analysis window, top-12m spenders are mechanically the most recent flyers
-- (anti-correlated with recency). Lifetime value + recent disengagement is the
-- real "at-risk" signal an airline cares about.
--
-- Rule:  monetary_total_percentile >= 0.60  (top 40% lifetime spend)
--        AND recency_percentile     >= 0.60  (worst 40% recency)
--        AND (complaint_count >= 1 OR avg_sentiment < 0 OR churn_risk_score >= 0.40)
-- Owner: Chief Customer Officer
-- Refresh: weekly
with rfm as (
    select
        *,
        percent_rank() over (order by recency_days)         as recency_percentile,
        percent_rank() over (order by monetary_total_usd)   as monetary_total_percentile
    from {{ ref('int_customer_lifetime') }}
),
feedback as (
    select
        customer_id,
        count(*)                                    as feedback_count,
        sum(case when is_negative then 1 else 0 end) as complaint_count,
        avg(sentiment_score)                        as avg_sentiment
    from {{ ref('fct_customer_feedback') }}
    group by 1
),
joined as (
    select
        r.customer_id,
        r.last_booking_date,
        r.recency_days,
        r.recency_percentile,
        r.frequency_12m,
        r.monetary_total_usd,
        r.monetary_total_percentile,
        r.monetary_12m_usd,
        r.monetary_12m_percentile,
        r.ltv_proxy_usd,
        r.churn_risk_score,
        coalesce(f.complaint_count, 0) as complaint_count,
        coalesce(f.avg_sentiment, 0)   as avg_sentiment
    from rfm r
    left join feedback f on r.customer_id = f.customer_id
)

select
    customer_id,
    last_booking_date,
    recency_days,
    recency_percentile,
    frequency_12m,
    monetary_total_usd,
    monetary_total_percentile,
    monetary_12m_usd,
    monetary_12m_percentile,
    ltv_proxy_usd,
    churn_risk_score,
    complaint_count,
    avg_sentiment,
    'HighValueAtRiskCustomer' as ontology_concept,
    current_timestamp         as inferred_at
from joined
where monetary_total_percentile >= 0.60
  and recency_percentile        >= 0.60
  and (complaint_count >= 1 or avg_sentiment < 0 or churn_risk_score >= 0.40)
