{% set expected_count = var('expected_encounter_count') | int %}

select
    count(*) as actual_row_count,
    {{ expected_count }} as expected_row_count
from {{ ref('fact_encounters') }}
having count(*) <> {{ expected_count }}
    or count(*) = 0
    or {{ expected_count }} <= 0
