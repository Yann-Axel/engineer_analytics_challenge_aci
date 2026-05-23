{{ config(materialized='table') }}

-- Tokenise raw feedback text into one row per (feedback_id, token, position).
-- Splits on any non-letter character (keeps accented chars for FR).
with split as (
    select
        feedback_id,
        regexp_split_to_array(normalised_text, '[^a-zàâäéèêëîïôöùûüç]+') as tokens
    from {{ ref('stg_customer_feedback') }}
),

exploded as (
    select
        feedback_id,
        generate_subscripts(tokens, 1) as token_position,
        unnest(tokens)                  as token
    from split
)

select
    feedback_id,
    token_position,
    token
from exploded
where token is not null and token <> ''
