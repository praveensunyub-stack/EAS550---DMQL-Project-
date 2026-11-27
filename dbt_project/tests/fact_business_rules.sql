select encounter_id
from {{ ref('fact_encounters') }}
where base_encounter_cost is null
    or base_encounter_cost < 0
    or base_encounter_cost in ('NaN'::numeric, 'Infinity'::numeric, '-Infinity'::numeric)
    or start_time is null
    or not isfinite(start_time)
    or (stop_time is not null and (not isfinite(stop_time) or stop_time < start_time))
    or encounter_class is null
    or encounter_class ~ '^[[:space:]]*$'
    or encounter_date is distinct from (start_time at time zone 'UTC')::date
    or (stop_time is null) <> (duration_seconds is null)
    or duration_seconds < 0
    or duration_seconds is distinct from extract(epoch from (stop_time - start_time))
    or is_after_death is null
