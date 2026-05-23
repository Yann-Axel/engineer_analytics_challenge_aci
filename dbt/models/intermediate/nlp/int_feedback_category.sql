{{ config(materialized='table') }}

-- Complaint categorisation: join tokens against the taxonomy seed.
-- A feedback can match multiple categories; we keep all matches AND the
-- dominant (highest-count, then highest-priority) category as the primary.

with tokens as (
    select * from {{ ref('int_feedback_tokens') }}
),

taxonomy as (
    select category, keyword, priority from {{ ref('complaint_taxonomy') }}
),

matches as (
    select
        t.feedback_id,
        tx.category,
        min(tx.priority) as best_priority,
        count(*)         as match_count
    from tokens t
    inner join taxonomy tx on t.token = tx.keyword
    group by t.feedback_id, tx.category
),

ranked as (
    select
        feedback_id,
        category,
        match_count,
        best_priority,
        row_number() over (
            partition by feedback_id
            order by match_count desc, best_priority asc, category asc
        ) as rn
    from matches
),

dominant as (
    select feedback_id, category as primary_category
    from ranked
    where rn = 1
),

all_categories as (
    select
        feedback_id,
        list(distinct category order by category) as all_categories
    from matches
    group by feedback_id
),

all_feedback as (
    select feedback_id from {{ ref('stg_customer_feedback') }}
)

select
    af.feedback_id,
    coalesce(d.primary_category, 'general')  as complaint_category,
    coalesce(ac.all_categories, [])          as all_categories
from all_feedback af
left join dominant       d  on af.feedback_id = d.feedback_id
left join all_categories ac on af.feedback_id = ac.feedback_id
