{{ config(materialized='table') }}

-- Semantic tags = distinct polarised words AND taxonomy keywords found in a feedback.
-- Each tag is suffixed with its polarity sign for downstream filtering
-- (e.g. "delayed:neg", "smooth:pos", "baggage:cat").

with tokens as (
    select * from {{ ref('int_feedback_tokens') }}
),

sentiment_tags as (
    select
        t.feedback_id,
        t.token || case when l.polarity < 0 then ':neg' else ':pos' end as tag
    from tokens t
    inner join {{ ref('lexicon_sentiment') }} l on t.token = l.word
),

category_tags as (
    select
        t.feedback_id,
        tx.category || ':cat' as tag
    from tokens t
    inner join {{ ref('complaint_taxonomy') }} tx on t.token = tx.keyword
),

all_tags as (
    select feedback_id, tag from sentiment_tags
    union
    select feedback_id, tag from category_tags
),

agg as (
    select
        feedback_id,
        list(distinct tag order by tag) as semantic_tags
    from all_tags
    group by 1
),

all_feedback as (
    select feedback_id from {{ ref('stg_customer_feedback') }}
)

select
    af.feedback_id,
    coalesce(a.semantic_tags, [])  as semantic_tags
from all_feedback af
left join agg a on af.feedback_id = a.feedback_id
