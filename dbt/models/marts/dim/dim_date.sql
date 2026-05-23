{{ config(materialized='table') }}

-- Rich date dimension: 2023-01-01 .. 2026-12-31 (buffer around flight window).
-- Carries aviation seasonality and CI/FR public holidays so downstream KPIs
-- can be sliced by 'peak/shoulder/off-peak' or 'is_holiday_*'.
with date_spine as (
    select
        cast(d as date) as date_day
    from generate_series(
        cast('2023-01-01' as date),
        cast('2026-12-31' as date),
        interval '1 day'
    ) g(d)
),

enriched as (
    select
        date_day,
        cast(strftime(date_day, '%Y%m%d') as integer)        as date_sk,
        extract(year from date_day)::integer                  as year_num,
        extract(quarter from date_day)::integer               as quarter_num,
        extract(month from date_day)::integer                 as month_num,
        strftime(date_day, '%B')                              as month_name,
        extract(week from date_day)::integer                  as iso_week,
        extract(dayofweek from date_day)::integer             as day_of_week,  -- 0 = Sunday in DuckDB
        strftime(date_day, '%A')                              as day_name,
        extract(day from date_day)::integer                   as day_of_month,
        case when extract(dayofweek from date_day) in (0, 6) then true else false end
            as is_weekend,
        -- Aviation seasonality (West Africa / France focus)
        case
            when extract(month from date_day) in (7, 8, 12)            then 'peak'
            when extract(month from date_day) in (6, 11, 1)            then 'shoulder'
            else 'off_peak'
        end as season_aviation,
        -- Public holidays (illustrative, not exhaustive)
        case
            when (extract(month from date_day) = 1  and extract(day from date_day) = 1)  -- New Year
              or (extract(month from date_day) = 8  and extract(day from date_day) = 7)  -- CI Independence
              or (extract(month from date_day) = 11 and extract(day from date_day) = 15) -- National Peace Day CI
              or (extract(month from date_day) = 12 and extract(day from date_day) = 25)
              or (extract(month from date_day) = 5  and extract(day from date_day) = 1)
                then true
            else false end as is_holiday_ci,
        case
            when (extract(month from date_day) = 1  and extract(day from date_day) = 1)
              or (extract(month from date_day) = 5  and extract(day from date_day) = 1)
              or (extract(month from date_day) = 5  and extract(day from date_day) = 8)
              or (extract(month from date_day) = 7  and extract(day from date_day) = 14) -- Bastille
              or (extract(month from date_day) = 8  and extract(day from date_day) = 15)
              or (extract(month from date_day) = 11 and extract(day from date_day) = 1)
              or (extract(month from date_day) = 11 and extract(day from date_day) = 11)
              or (extract(month from date_day) = 12 and extract(day from date_day) = 25)
                then true
            else false end as is_holiday_fr,
        date_trunc('month',   date_day)::date as month_start_date,
        date_trunc('quarter', date_day)::date as quarter_start_date,
        date_trunc('year',    date_day)::date as year_start_date
    from date_spine
)

select * from enriched
