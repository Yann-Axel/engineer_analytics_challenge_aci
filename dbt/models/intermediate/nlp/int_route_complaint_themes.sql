{{ config(materialized='table') }}

-- Top 3 complaint themes per route × month, plus average sentiment.
-- This is the route-level NLP aggregate that the dashboard consumes
-- to answer "what complaints drive low satisfaction on route X?".
with feedback_enriched as (
    select
        f.feedback_id,
        f.route_id,
        date_trunc('month', f.feedback_at)::date as period_month,
        c.complaint_category,
        s.sentiment_score,
        s.sentiment_label
    from {{ ref('stg_customer_feedback') }} f
    inner join {{ ref('int_feedback_category') }}  c using (feedback_id)
    inner join {{ ref('int_feedback_sentiment') }} s using (feedback_id)
    where f.route_id is not null
),

per_theme as (
    select
        route_id,
        period_month,
        complaint_category,
        count(*)                                              as theme_count,
        avg(sentiment_score)                                  as theme_avg_sentiment
    from feedback_enriched
    group by 1, 2, 3
),

ranked as (
    select
        *,
        row_number() over (
            partition by route_id, period_month
            order by theme_count desc, complaint_category asc
        ) as rk
    from per_theme
),

top3 as (
    select * from ranked where rk <= 3
),

monthly_summary as (
    select
        route_id,
        period_month,
        count(*)                                          as feedback_count,
        avg(sentiment_score)                              as avg_sentiment,
        sum(case when sentiment_label = 'negative' then 1 else 0 end)::double
            / count(*)                                    as negative_ratio,
        sum(case when sentiment_label = 'positive' then 1 else 0 end)::double
            / count(*)                                    as positive_ratio
    from feedback_enriched
    group by 1, 2
)

select
    ms.route_id,
    ms.period_month,
    ms.feedback_count,
    ms.avg_sentiment,
    ms.negative_ratio,
    ms.positive_ratio,
    max(case when t.rk = 1 then t.complaint_category end) as top_theme_1,
    max(case when t.rk = 1 then t.theme_count end)        as top_theme_1_count,
    max(case when t.rk = 2 then t.complaint_category end) as top_theme_2,
    max(case when t.rk = 2 then t.theme_count end)        as top_theme_2_count,
    max(case when t.rk = 3 then t.complaint_category end) as top_theme_3,
    max(case when t.rk = 3 then t.theme_count end)        as top_theme_3_count
from monthly_summary ms
left join top3 t using (route_id, period_month)
group by 1, 2, 3, 4, 5, 6
