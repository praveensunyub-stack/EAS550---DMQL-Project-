-- Question 3: Which patients have the three highest distinct cumulative base
-- encounter cost totals within each organization, including ties?
WITH patient_organization_costs AS (
    SELECT
        organization_id,
        patient_id,
        COUNT(*) AS encounter_count,
        SUM(base_encounter_cost) AS total_base_encounter_cost,
        COUNT(*) FILTER (WHERE is_after_death) AS after_death_encounter_count
    FROM analytics.fact_encounters
    GROUP BY
        organization_id,
        patient_id
),

ranked_costs AS (
    SELECT
        organization_id,
        patient_id,
        encounter_count,
        total_base_encounter_cost,
        after_death_encounter_count,
        DENSE_RANK() OVER (
            PARTITION BY organization_id
            ORDER BY total_base_encounter_cost DESC
        ) AS cost_rank
    FROM patient_organization_costs
)

SELECT
    o.organization_id,
    o.name AS organization_name,
    p.patient_id,
    p.gender,
    r.cost_rank,
    r.encounter_count,
    r.total_base_encounter_cost,
    r.after_death_encounter_count
FROM ranked_costs AS r
INNER JOIN analytics.dim_organizations AS o
    ON r.organization_id = o.organization_id
INNER JOIN analytics.dim_patients AS p
    ON r.patient_id = p.patient_id
WHERE r.cost_rank <= 3
ORDER BY
    o.organization_id,
    r.cost_rank,
    p.patient_id;
