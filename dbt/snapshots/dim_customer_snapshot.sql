{% snapshot dim_customer_snapshot %}

{{
    config(
      target_schema='snapshots',
      unique_key='customer_id',
      strategy='check',
      check_cols=['loyalty_tier', 'customer_segment', 'preferred_channel']
    )
}}

-- SCD2 historisation: tracks changes in loyalty_tier, customer_segment and
-- preferred_channel. Run `dbt snapshot` to capture a new version when these
-- attributes change. dbt_valid_from / dbt_valid_to bracket each version.
select
    customer_id,
    first_name,
    last_name,
    gender,
    birth_date,
    country,
    city,
    customer_segment,
    loyalty_tier,
    signup_date,
    preferred_channel
from {{ ref('stg_customers') }}

{% endsnapshot %}
