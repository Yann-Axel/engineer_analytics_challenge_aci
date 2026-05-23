-- Singular test: every LoyalDetractor must currently be on Gold tier.
select customer_id, loyalty_tier
from {{ ref('ont_loyal_detractor') }}
where loyalty_tier <> 'Gold'
