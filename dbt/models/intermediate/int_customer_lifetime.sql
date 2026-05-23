{{ config(materialized='table') }}

-- LTV proxy and churn risk signal per customer.
-- LTV proxy: cumulative revenue × engagement factor.
-- Churn risk: blends recency, complaint signals, and sentiment.
with rfm as (
    select * from {{ ref('int_customer_rfm') }}
),

ancillary as (
    -- Total ancillary acceptance from offers
    select
        b.customer_id,
        sum(case when o.accepted_flag then 1 else 0 end) as accepted_offers,
        count(o.ancillary_offer_id)                       as presented_offers
    from {{ ref('stg_bookings') }} b
    left join {{ ref('stg_ancillary_offers') }} o on o.booking_id = b.booking_id
    group by 1
),

lifetime as (
    select
        r.customer_id,
        r.last_booking_date,
        r.recency_days,
        r.frequency_total,
        r.frequency_12m,
        r.monetary_total_usd,
        r.monetary_12m_usd,
        r.r_score, r.f_score, r.m_score,
        r.monetary_12m_percentile,
        coalesce(a.accepted_offers, 0)        as accepted_offers,
        coalesce(a.presented_offers, 0)       as presented_offers,
        case when coalesce(a.presented_offers, 0) > 0
             then a.accepted_offers::double / a.presented_offers
             else null end                    as offer_acceptance_rate,
        -- LTV proxy: monetary × frequency_factor
        r.monetary_total_usd * (1 + ln(greatest(r.frequency_total, 1)))
            as ltv_proxy_usd,
        -- Churn risk: 0-1 scale, higher = more risk
        least(1.0,
            (r.recency_days::double / 365.0) * 0.6
            + case when r.frequency_12m = 0 then 0.4 else 0.0 end
        ) as churn_risk_score
    from rfm r
    left join ancillary a on r.customer_id = a.customer_id
)

select * from lifetime
