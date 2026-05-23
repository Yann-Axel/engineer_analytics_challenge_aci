{{ config(materialized='table') }}

-- Grain: 1 row per feedback, fully enriched with NLP-derived fields.
-- This is the "unstructured -> structured" bridge required by the brief.
with f as (
    select * from {{ ref('stg_customer_feedback') }}
),
sent as (
    select * from {{ ref('int_feedback_sentiment') }}
),
cat as (
    select * from {{ ref('int_feedback_category') }}
),
tags as (
    select * from {{ ref('int_feedback_tags') }}
),
d_customer as (
    select customer_sk, customer_id from {{ ref('dim_customer_current') }}
),
d_route as (
    select route_sk, route_id from {{ ref('dim_route') }}
),
d_flight as (
    select flight_sk, flight_id from {{ ref('fct_flights') }}
),
d_date as (
    select date_sk, date_day from {{ ref('dim_date') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['f.feedback_id']) }} as feedback_sk,
    f.feedback_id,
    dc.customer_sk,
    f.customer_id,
    dr.route_sk,
    f.route_id,
    df.flight_sk,
    f.flight_id,
    f.booking_id,
    dd.date_sk as feedback_date_sk,
    cast(f.feedback_at as date) as feedback_date,
    f.feedback_at,
    f.feedback_channel,
    f.language_raw                   as language,
    f.raw_text,
    -- NLP-derived
    sent.sentiment_score,
    sent.sentiment_label,
    sent.polarised_word_count,
    cat.complaint_category,
    cat.all_categories,
    tags.semantic_tags,
    -- Helper flags
    case when sent.sentiment_label = 'negative' then true else false end as is_negative,
    case when sent.sentiment_label = 'positive' then true else false end as is_positive
from f
left join sent       on f.feedback_id    = sent.feedback_id
left join cat        on f.feedback_id    = cat.feedback_id
left join tags       on f.feedback_id    = tags.feedback_id
left join d_customer dc on f.customer_id = dc.customer_id
left join d_route    dr on f.route_id    = dr.route_id
left join d_flight   df on f.flight_id   = df.flight_id
left join d_date     dd on cast(f.feedback_at as date) = dd.date_day
