{{ config(materialized='table') }}

-- Required by dbt Semantic Layer (MetricFlow): a daily time spine.
-- We expose the same date_day as dim_date so they stay aligned.
select date_day from {{ ref('dim_date') }}
