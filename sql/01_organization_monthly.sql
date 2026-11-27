-- Question 1: In what ways does the quantity of encounters and the cost of each encounter vary between different organizations as well as between various UTC calendar months for the year 2026? 
-- We set the same period to ensure consistent results.
SELECT
    o.organization_id,
    o.name AS organization_name,
    DATE_TRUNC('month', e.encounter_date::TIMESTAMP)::DATE AS encounter_month,
    COUNT(*) AS encounter_count,
    SUM(e.base_encounter_cost) AS total_base_encounter_cost
FROM analytics.fact_encounters AS e
INNER JOIN analytics.dim_organizations AS o
    ON e.organization_id = o.organization_id
WHERE
    e.encounter_date >= DATE '2026-01-01'
    AND e.encounter_date < DATE '2027-01-01'
GROUP BY
    DATE_TRUNC('month', e.encounter_date::TIMESTAMP)::DATE,
    o.organization_id,
    o.name
ORDER BY
    encounter_month,
    o.organization_id;
