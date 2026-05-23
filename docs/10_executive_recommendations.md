# Executive Growth Allocation — Recommendations

> **For**: CEO, CFO, COMEX — Air Côte d'Ivoire
> **From**: Analytics Engineering team
> **Decision window**: next 12 months
> **Source**: Executive Growth Allocation dashboard (5 pages, 34 charts, 5 ontology concepts) — see `docs/09_dashboard_design.md`

---

## ❶ Decision question (reminder)

*Where should Air Côte d'Ivoire invest first to maximise profitable growth: **route expansion**, **customer retention**, or **upsell / cross-sell**?*

## ❷ Verdict in one sentence

**Allocate 40% to operations stabilisation of 5 underperforming routes, 35% to high-value customer retention, and 25% to premium upsell activation.** This sequencing prioritises *margin recovery first*, then *revenue protection*, then *revenue growth* — in decreasing order of certainty and speed-to-value.

---

## ❸ Top 3 actions, prioritised

### Action 1 — Stabilise the 5 IROPS-heavy routes (margin recovery, FAST)

| Element | Value |
|---|---|
| **What** | Operations task force on R015 (ABJ–LFW), R005 (ABJ–DKR), R008 (ABJ–OUA), R004 (ABJ–ACC), R006 (ABJ–LOS) |
| **Why** | These 5 routes carry **20–35 % disruption rates** and **3–7 % cancellation rates** (vs 3.6 % network average). They are flagged by the `ont_irops_heavy_route` concept. |
| **Evidence** | R015 alone: 34.5 % disruption, 6.9 % cancellation — the most fragile route on the network. R006 cancellation rate at 6.8 %, R004 at 5.2 %. |
| **Impact** | At ~1,300 flights/year combined, cutting cancellations to the network average reclaims **~30 cancelled flights/year** = ~$200K direct IROPS penalty avoided + sentiment uplift. |
| **Risk** | West African rainy season (June–August) is partially uncontrollable — gains will be operational (fleet rotation, crew positioning), not weather. |
| **Owner** | COO + Operations Director |
| **Budget share** | **40 %** of next-12-month growth budget |

### Action 2 — Retention campaign on 20 high-value at-risk customers (revenue protection)

| Element | Value |
|---|---|
| **What** | Personalised retention push (call, dedicated account manager, fare credit) on the **20 customers** flagged `ont_high_value_at_risk_customer`. |
| **Why** | These customers carry **$13.6 M cumulative lifetime revenue** (avg **$682 K each**) and have signalled dissatisfaction (43 complaints + negative sentiment + recency drift). |
| **Evidence** | Top at-risk customer: CUST0166 with $1.39 M lifetime + multiple complaints. The bottom 5 on the list each still represent >$500 K. |
| **Impact** | Saving even 50 % of these customers protects **~$0.7 M/year recurring revenue** + halo effect on the loyalty Gold cohort (`ont_loyal_detractor` shows 22 more at risk). |
| **Risk** | Without root-cause fix (Action 1), retention spend on disrupted routes is a band-aid. |
| **Owner** | Chief Customer Officer |
| **Budget share** | **35 %** |

### Action 3 — Activate the 48 premium upsell candidates (revenue growth)

| Element | Value |
|---|---|
| **What** | Dedicated upgrade-offer programme targeting the **48 customers** in `ont_premium_upsell_candidate` (Standard/Business segment, Silver/Gold tier, top-quartile acceptance). |
| **Why** | Current acceptance rate on this cohort is **17.3 %** (vs 12 % network) — they convert. With 24,557 offers presented and only 4,289 accepted, headroom is large. |
| **Evidence** | Ancillary acceptance currently captures **$23 M out of $88 M** in offered value (35 % capture rate). |
| **Impact** | If we present the 48 candidates an additional 5 upgrade offers each over 12 months with 17 % conversion, expected uplift = **$1.5–3 M new ancillary revenue**. |
| **Risk** | Over-pushing premium offers can degrade NPS — apply offer cadence limits per customer. |
| **Owner** | Ancillary Manager + Loyalty Manager |
| **Budget share** | **25 %** |

---

## ❹ Budget allocation snapshot

```
              ┌────────────────────────┐
   40 %  ───▶ │  Network / Ops fix     │   Margin recovery on 5 routes
              ├────────────────────────┤
   35 %  ───▶ │  Customer retention     │   $13.6 M revenue at stake
              ├────────────────────────┤
   25 %  ───▶ │  Premium upsell push   │   $1.5–3 M growth potential
              └────────────────────────┘
```

**Rationale for this sequencing**: every dollar fixing ops protects margin *immediately*; every dollar retaining protects existing revenue; every dollar on upsell builds incremental growth. Reverse the order at your peril — pushing upgrades on disrupted routes erodes trust.

---

## ❺ Evidence summary (from the dashboards)

| Headline | Value | Source page |
|---|---|---|
| Total revenue (24 months) | **$485.5 M** | Page 0 |
| Route margin % (network) | **77.9 %** | Page 0 |
| Load factor | **71.9 %** | Page 0 |
| OTP15 (≤15 min) | **66.5 %** | Page 0 (improvable, target 75 %+) |
| Cancellation rate | **3.6 %** | Page 0 (5 IROPS routes drag this up) |
| Avg customer sentiment | **−0.103** | Page 0 (slight net-negative — actionable) |
| Strategic long-haul routes (R009 + R013 = ABJ-CDG pair) | **$155.0 M / 32 % of revenue** | Page 1 |
| At-risk high-value customers | **20** (lifetime $13.6 M) | Page 2, Page 4 |
| Loyal Gold detractors (early warning) | **22** | Page 2 |
| IROPS-heavy routes | **5** (R015, R005, R008, R004, R006) | Page 1, Page 4 |
| Premium upsell candidates | **48** (17 % acceptance) | Page 3, Page 4 |
| Ancillary attach rate | **80.2 %** | Page 0 |
| Premium cabin mix | **22.0 %** | Page 0 |

---

## ❻ KPIs to track in the next 90 days

| KPI | Today | 90-day target | Owner |
|---|---|---|---|
| Cancellation rate on R015/R005/R008/R004/R006 | 3.6 – 6.9 % | **< 3.5 %** each | COO |
| Avg sentiment on disrupted routes | −0.10 | **> +0.05** | COO + CCO |
| Count of at-risk customers (`ont_high_value_at_risk_customer`) | 20 | **≤ 10** | CCO |
| Upgrade acceptance rate on the 48 candidates | 17.3 % | **≥ 20 %** | Ancillary Manager |
| Ancillary revenue per pax (ARPP) | proxy at fare-class level | **+15 % vs baseline** | Ancillary Manager |
| OTP15 network-wide | 66.5 % | **≥ 72 %** | COO |

These KPIs are all in the semantic layer (`dbt/models/semantic/_metrics.yml`); the dashboard reads them without re-derivation.

---

## ❼ Risks & assumptions

| # | Risk / assumption | Mitigation |
|---|---|---|
| R1 | **Margin % (77.9 %) is high on synthetic data** — production costs will likely compress margins | Re-validate on actual cost data; if margin drops below 50 %, IROPS recovery becomes even more critical (Action 1 priority rises) |
| R2 | 24-month dataset limits churn signal precision | Re-run `int_customer_lifetime` after 12+ more months of actual booking data |
| R3 | West African weather is uncontrollable | Action 1 targets *operational* drivers (turnaround, crew positioning), not weather mitigation |
| R4 | Aggressive upsell may degrade NPS | Cap at 5 offers/customer/year (configurable in `seeds/` if formalised) |
| R5 | Strategic long-haul (R009/R013) shown at 74 % margin — fuel volatility could compress this fast | Hedge fuel; revisit Action allocation quarterly |

---

## ❽ One-line recap for the COMEX

> *"We protect what we have before we grow: $0.40 of every growth dollar fixes the operations of our 5 fragile routes, $0.35 retains our top 20 at-risk customers ($13.6 M lifetime value), $0.25 activates 48 customers with already-proven upgrade appetite."*

---

*Generated from the Executive Growth Allocation dashboard. All numbers are live as of the latest `dbt build` run. Methodology: `docs/09_dashboard_design.md`. Ontology rules: `docs/05_ontology_rules.yml`.*
