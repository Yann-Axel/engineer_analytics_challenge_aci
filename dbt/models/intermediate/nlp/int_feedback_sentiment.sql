{{ config(materialized='table') }}

-- Lexicon-based sentiment scoring with negation handling.
-- For each polarised token, check whether the 1-2 preceding tokens are a negation
-- (e.g. "pas bon" → flip polarity of "bon"). Final score = sum / count, in [-1, +1].

with tokens as (
    select * from {{ ref('int_feedback_tokens') }}
),

lexicon as (
    select word, polarity from {{ ref('lexicon_sentiment') }}
),

negation as (
    select word from {{ ref('negation_words') }}
),

-- 1) Find polarised tokens
polarised as (
    select
        t.feedback_id,
        t.token_position,
        t.token,
        l.polarity
    from tokens t
    inner join lexicon l on t.token = l.word
),

-- 2) For each polarised token, check whether a negation appears at position-1 or position-2
with_neg_flag as (
    select
        p.feedback_id,
        p.token_position,
        p.polarity,
        case
            when exists (
                select 1
                from tokens tn
                inner join negation n on tn.token = n.word
                where tn.feedback_id = p.feedback_id
                  and tn.token_position between p.token_position - 2 and p.token_position - 1
            ) then -p.polarity
            else p.polarity
        end as effective_polarity
    from polarised p
),

aggregated as (
    select
        feedback_id,
        sum(effective_polarity)                          as sentiment_raw,
        count(*)                                         as polarised_word_count,
        case when count(*) > 0
             then sum(effective_polarity)::double / count(*)
             else 0 end                                  as sentiment_score
    from with_neg_flag
    group by 1
),

-- 3) Final: join back all feedbacks (including those with no polarised words → neutral)
all_feedback as (
    select feedback_id from {{ ref('stg_customer_feedback') }}
)

select
    af.feedback_id,
    coalesce(a.sentiment_raw, 0)                            as sentiment_raw,
    coalesce(a.polarised_word_count, 0)                     as polarised_word_count,
    coalesce(a.sentiment_score, 0)                          as sentiment_score,
    case
        when coalesce(a.sentiment_score, 0) <= -0.2 then 'negative'
        when coalesce(a.sentiment_score, 0) >=  0.2 then 'positive'
        else 'neutral'
    end as sentiment_label
from all_feedback af
left join aggregated a on af.feedback_id = a.feedback_id
