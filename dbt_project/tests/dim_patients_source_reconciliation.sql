with expected as (
    select patient_id, birth_date, death_date, gender
    from {{ source('synthea_source', 'patients') }}
),
actual as (
    select patient_id, birth_date, death_date, gender
    from {{ ref('dim_patients') }}
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
