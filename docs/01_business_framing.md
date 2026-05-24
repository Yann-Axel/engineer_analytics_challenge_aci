# Part 1 — Business framing & KPIs

> **Decision question** (per brief): *Where should Air Côte d'Ivoire invest first — route expansion, customer retention, or upsell / cross-sell?*

## 1. The five domains and how they map to the brief's three themes

| Domain | Owner | Strategic question (12 m) |
|---|---|---|
| Network & Revenue Mgmt | VP Network | Open / reinforce / close which routes? |
| Operations | COO | Which routes lose margin to ops, not demand? |
| Commercial / Pricing | Revenue Mgr | Fare mix, dynamic pricing, channel? |
| Customer & Loyalty | CCO | Retain / upgrade / reactivate? |
| Ancillary Revenue | Ancillary Mgr | What to push, to whom, when? |

- **Theme 1 — Route optimisation & growth** ← Network + Operations
- **Theme 2 — Customer retention** ← Customer + Operations (delays drive churn) + unstructured feedback
- **Theme 3 — Upsell / cross-sell** ← Ancillary + Customer + Commercial

```mermaid
flowchart LR
    NET[Network] --> T1{{Theme 1<br/>Routes}}
    OPS[Operations] --> T1
    OPS --> T2{{Theme 2<br/>Retention}}
    CUS[Customer & Loyalty] --> T2
    NLP[Unstructured feedback] --> T2
    CUS --> T3{{Theme 3<br/>Upsell}}
    ANC[Ancillary] --> T3
    COM[Commercial] --> T3

    classDef theme fill:#fef3c7,stroke:#92400e,color:#92400e
    class T1,T2,T3 theme
```

## 2. The 10 KPIs

The brief lists 9 example KPIs. We cover all of them plus **Recency** (the basis of the RFM churn signal).

| KPI | Formula | Theme |
|---|---|---|
| Route Revenue | `SUM(ticket + ancillary)` on Flown bookings | Route |
| Route Margin % | `(Revenue − DOC) / Revenue` | Route |
| Load Factor | `SUM(pax) / SUM(seats)` | Route |
| Delay Rate (OTP-inv) | `delay_min > 15 / operated` | Route |
| Cancellation Rate | `cancelled / scheduled` | Route |
| Repeat Booking Rate | `≥2 bookings / active customer / 12m` | Retention |
| Recency (RFM-R) | days since last booking | Retention |
| Loyalty Engagement | points earned per active member / 12m | Retention |
| Ancillary Attach Rate | `bookings with ancillary > 0 / bookings` | Upsell |
| Customer Sentiment | mean score derived from feedback text | Retention / Route |

Each formula is the source of truth materialised in [dbt/models/semantic/_metrics.yml](../dbt/models/semantic/_metrics.yml) (Part 2).
