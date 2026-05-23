# Part 2 — NLP pipeline (unstructured → structured)

The brief requires:
> *"Show how unstructured data is integrated. Examples: sentiment scoring, complaint categories, route-level issue themes, or semantic tags."*

We deliver **all four**: sentiment scoring, complaint category, semantic tags, route-level themes.

## Approach: rule-based lexicon + SQL (not ML)

| Approach | Pros | Cons | Verdict |
|---|---|---|---|
| Transformer (DistilBERT multilingual) | Highest precision | ~250 MB, latency, opaque, dependency | ❌ Overkill for the brief |
| VADER | Industry standard | English-only, fragmentation with FR data | ❌ |
| **Lexicon CSV + SQL** | Light, **explainable**, offline, versionable | Finite lexical coverage | ✅ **Senior trade-off** |

**Why senior**: every score is traceable to specific words in specific feedback rows — perfect for auditing and explaining recommendations to executives.

If we industrialised, only the `int_feedback_sentiment` model would be swapped (e.g. external API call). The contract (raw_text → sentiment_score) stays identical.

## Pipeline (dbt-native)

```
data/enriched/customer_feedback.parquet   (3,000 rows, FR/EN free text)
    │
    ▼
stg_customer_feedback                     (cast, lowercase, normalised_text)
    │
    ▼
int_feedback_tokens                       (one row per (feedback, token, position))
    │
    ├─ joins with seeds/lexicon_sentiment.csv
    └─ joins with seeds/negation_words.csv
    ▼
int_feedback_sentiment                    (score in [-1, +1] + label)
    │
    ├─ joins with seeds/complaint_taxonomy.csv
    ▼
int_feedback_category                     (primary category + all_categories array)
    │
    ▼
int_feedback_tags                         (semantic_tags array, e.g. ['delay:neg','crew:cat'])
    │
    ▼
fct_customer_feedback                     (FACT: all enrichments + joins to dims)
    │
    ▼
int_route_complaint_themes                (route × month: top 3 themes + avg sentiment)
```

## The 3 NLP seeds

| Seed | Rows | Role |
|---|---|---|
| `lexicon_sentiment.csv` | 145 words (FR+EN) | Polarised vocabulary (-1 / +1) |
| `complaint_taxonomy.csv` | 62 entries (FR+EN) | 10 categories × keywords with priority |
| `negation_words.csv` | 18 words (FR+EN) | Flips polarity of the next token |

All three are **declarative CSV files** — a business owner can review and edit them without touching SQL.

## Negation handling

For every polarised token at position `p`, we check whether **any token at position `p-1` or `p-2`** is in `negation_words`. If so, the token's polarity is flipped. This handles "pas bon" → negative, "not great" → negative.

The implementation is a single SQL `EXISTS` clause in `int_feedback_sentiment.sql`.

## Distribution observed on 3,000 feedbacks

| Sentiment label | Count | Share |
|---|---|---|
| negative | 1,191 | 40% |
| neutral | 952 | 32% |
| positive | 857 | 29% |

| Complaint category | Count |
|---|---|
| general (fallback) | 848 |
| crew | 433 |
| baggage | 309 |
| food | 303 |
| upgrade | 267 |
| seat | 208 |
| delay | 206 |
| booking_app | 201 |
| lounge | 161 |
| refund | 64 |

## Limitations and next steps

| Limitation | Mitigation |
|---|---|
| Lexicon misses slang / typos | Add to `lexicon_sentiment.csv` (versioned) |
| Negation window is 2 tokens — won't catch "I didn't think the crew was very polite" | Acceptable trade-off; extend window if precision becomes an issue |
| Code-switched feedback (FR+EN) handled per-token but not contextually | Acceptable; both lexicons covered |
| Sarcasm / irony untouched | Out of scope for a lexicon-based approach; would require ML |

If we need higher precision later, the swap point is `int_feedback_sentiment.sql`: replace the SQL with an external NLP call, keep the rest of the pipeline.

## Tests on NLP outputs

- `sentiment_score ∈ [-1, +1]` enforced via `dbt_expectations` on `fct_customer_feedback.sentiment_score`
- `sentiment_label ∈ {negative, neutral, positive}` via `accepted_values`
- All `feedback_id` are unique and not null

All passing in `dbt build` (160/160 tests).
