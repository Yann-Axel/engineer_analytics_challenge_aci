-- Singular test: every HighValueAtRiskCustomer must carry at least one
-- dissatisfaction signal (complaint, negative sentiment, or churn risk ≥ 0.4).
-- Returns rows that VIOLATE the rule (test fails if any).
select customer_id
from {{ ref('ont_high_value_at_risk_customer') }}
where complaint_count = 0
  and avg_sentiment >= 0
  and churn_risk_score < 0.40
