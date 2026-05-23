-- Singular test: every StrategicUnderperformingRoute must be tagged is_strategic = true
-- in dim_route. Sanity-checks the ontology's own input.
select o.route_id
from {{ ref('ont_strategic_underperforming_route') }} o
left join {{ ref('dim_route') }} r on o.route_id = r.route_id
where coalesce(r.is_strategic, false) = false
