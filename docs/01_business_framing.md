# Part 1 — Business framing & decision questions

> **Decision question** (per brief): *Where should Air Côte d'Ivoire invest first to maximize profitable growth: route expansion and optimization, customer retention, or upsell / cross-sell?*

## 1. Business domains in scope

A flag carrier with long-haul ambitions is steered along five interdependent domains. The analytics product must serve them all because the decision question is cross-functional.

| Domain | Decision owner | Strategic question (next 12 months) | Structured signals | Unstructured signals |
|---|---|---|---|---|
| **Network & Revenue Management** | VP Network, CCO | Which routes to open / reinforce / close? Capacity allocation per aircraft type? | Routes, Flights, Capacity, Yield, Competitor schedule | External demand reports, codeshare arrangements |
| **Operations** | COO, Ops Director | Which routes lose margin to operational issues vs weak demand? | Flight status, delay, disruption type, aircraft availability, crew | Ops notes, disruption logs, weather alerts |
| **Commercial / Pricing** | Revenue Manager | Fare class mix, dynamic pricing, channel strategy? | Bookings, fare class/family, channel | A/B test logs, elasticity studies |
| **Customer & Loyalty** | CCO, Loyalty Manager | Who to retain, who to upgrade in tier, who to reactivate? | Customers, loyalty tier, repeat behavior, RFM | Sentiment, NPS, support tickets, complaints |
| **Ancillary Revenue** | Ancillary Manager, Digital | Which ancillaries to push, to whom, when? Cargo opportunity? | Ancillary revenue, bags, seat selection, cargo | Offer copy A/B tests, customer propensity |

**Mapping to the three challenge themes**

- **Route optimization & growth** ← Network + Operations + Competitor benchmark
- **Customer retention** ← Customer/Loyalty + Operations signals (delays drive churn) + Unstructured sentiment
- **Upsell / Cross-sell** ← Ancillary + Customer + Commercial

## 2. Decision makers & their questions

| Persona | Primary question | Granularity needed | Cadence |
|---|---|---|---|
| **CEO / Executive Committee** | Where do we deploy the next $X of marketing/capacity budget? | Theme x quarter | Quarterly |
| **VP Network** | Which routes should grow, defend, exit? | Route x month | Monthly |
| **COO** | Which routes are underperforming due to ops, not demand? | Route x month | Monthly + weekly OTP |
| **Chief Customer Officer** | Which high-value customers are at risk of churn? | Customer | Weekly batch |
| **Revenue Manager** | What fare class mix and price points to optimize yield? | Route x fare class x day | Daily |
| **Loyalty Manager** | Which loyalty members should we proactively upgrade or rescue? | Customer x tier | Monthly |

## 3. KPI catalogue (24 metrics, grouped by theme)

Each KPI has a unique formula. These definitions become the **source of truth** for the semantic layer in Part 2.

### 3.1 Route optimization & growth (8 KPIs)

| KPI | Formula | Grain |
|---|---|---|
| Route Revenue | `SUM(ticket_price_usd + ancillary_revenue_usd)` on Flown bookings | Route × period |
| Direct Operating Cost | `SUM(fuel + crew + airport_fees + maintenance + irops_penalty)` | Route × period |
| Route Margin % | `(Revenue − Direct Operating Cost) / Revenue` | Route × period |
| Load Factor | `SUM(passengers) / SUM(seat_capacity)` | Flight → Route |
| Yield (RASK) | `Revenue / (seat_capacity × distance_km)` | Flight → Route |
| OTP15 | `flights with delay_min ≤ 15 / total flights` | Route × period |
| Cancellation Rate | `cancelled / scheduled` | Route × period |
| Demand Trend Index | bookings 30d rolling vs same window N-1 | Route × period |

### 3.2 Customer retention (8 KPIs)

| KPI | Formula | Grain |
|---|---|---|
| Repeat Booking Rate | customers with ≥2 bookings in 12 months / active customers | Segment × period |
| Recency (RFM-R) | days since last booking | Customer |
| Frequency (RFM-F) | flown segments in trailing 12 months | Customer |
| Monetary (RFM-M) | trailing 12-month total revenue | Customer |
| Customer Lifetime Value | observed cumulative revenue × retention factor | Customer |
| Churn Risk Score | composite (Recency × NPS × complaints) | Customer |
| Loyalty Tier Progression Rate | members moving up tier in 12 months / total members | Tier |
| Avg Sentiment | mean sentiment_score on feedback (Part 2 NLP output) | Customer / Route |

### 3.3 Upsell / cross-sell (8 KPIs)

| KPI | Formula | Grain |
|---|---|---|
| Ancillary Attach Rate | bookings with ancillary > 0 / total | Segment × Route |
| Ancillary Revenue per Pax (ARPP) | `SUM(ancillary) / passengers` | Segment × Route |
| Upgrade Conversion Rate | accepted upgrades / presented upgrades | Segment × Fare |
| Cargo Revenue per Long-Haul Flight | cargo revenue / long-haul flights | Route × Aircraft |
| Cross-sell Coverage | customers with ≥2 ancillary products / total | Segment |
| Offer Acceptance Rate | accepted / presented offers | Offer type × Channel |
| Average Ancillary Order Value | mean ancillary revenue per booking | Segment |
| Premium Mix | `Business + Premium Eco bookings / total` | Route × period |
