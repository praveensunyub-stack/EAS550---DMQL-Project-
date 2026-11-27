with expected as (
    select organization_id, name, city, state
    from {{ source('synthea_source', 'organizations') }}
),
actual as (
    select organization_id, name, city, state
    from {{ ref('dim_organizations') }}
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
