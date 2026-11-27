with expected as (
    select
        e.encounter_id,
        e.patient_id,
        e.organization_id,
        e.start_time,
        e.stop_time,
        (e.start_time at time zone 'UTC')::date as encounter_date,
        e.encounter_class,
        e.base_encounter_cost,
        extract(epoch from (e.stop_time - e.start_time)) as duration_seconds,
        coalesce(
            (e.start_time at time zone 'UTC')::date > p.death_date,
            false
        ) as is_after_death
    from {{ source('synthea_source', 'encounters') }} as e
    left join {{ source('synthea_source', 'patients') }} as p
        on e.patient_id = p.patient_id
),
actual as (
    select
        encounter_id,
        patient_id,
        organization_id,
        start_time,
        stop_time,
        encounter_date,
        encounter_class,
        base_encounter_cost,
        duration_seconds,
        is_after_death
    from {{ ref('fact_encounters') }}
)
select 'missing_or_changed' as issue, differences.*
from (
    select * from expected
    except all
    select * from actual
) as differences
union all
select 'extra_or_changed' as issue, differences.*
from (
    select * from actual
    except all
    select * from expected
) as differences
