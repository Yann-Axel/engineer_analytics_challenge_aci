{{ config(materialized='table') }}

-- RFM analysis per customer.
-- Reference date = latest booking date in the dataset (proxy for "today").
with bookings as (
    select * from {{ ref('stg_bookings') }}
    where booking_status in ('Flown', 'Confirmed')
),

reference_date as (
    select max(booking_date) as ref_date from bookings
),

rfm as (
    select
        b.customer_id,
        max(b.booking_date)                                       as last_booking_date,
        date_diff('day', max(b.booking_date), r.ref_date)         as recency_days,
        count(*)                                                  as frequency_total,
        count(case when date_diff('day', b.booking_date, r.ref_date) <= 365
                   then 1 end)                                    as frequency_12m,
        sum(b.ticket_price_usd + b.ancillary_revenue_usd)         as monetary_total_usd,
        sum(case when date_diff('day', b.booking_date, r.ref_date) <= 365
                 then b.ticket_price_usd + b.ancillary_revenue_usd
                 else 0 end)                                      as monetary_12m_usd
    from bookings b
    cross join reference_date r
    group by b.customer_id, r.ref_date
),

with_percentiles as (
    select
        *,
        ntile(5) over (order by recency_days desc)        as r_score,  -- lower recency = higher score
        ntile(5) over (order by frequency_12m)            as f_score,
        ntile(5) over (order by monetary_12m_usd)         as m_score,
        percent_rank() over (order by monetary_12m_usd)   as monetary_12m_percentile
    from rfm
)

select * from with_percentiles
