-- Question 2: How do mean base cost and completed duration vary by encounter
-- class and the patient's recorded gender across the complete source subset?
SELECT
    e.encounter_class,
    p.gender,
    COUNT(*) AS encounter_count,
    COUNT(e.duration_seconds) AS completed_duration_count,
    SUM(e.base_encounter_cost) AS total_base_encounter_cost,
    ROUND(AVG(e.base_encounter_cost), 2) AS mean_base_encounter_cost,
    ROUND(AVG(e.duration_seconds) / 60, 2) AS mean_completed_duration_minutes,
    COUNT(*) FILTER (WHERE e.is_after_death) AS after_death_encounter_count
FROM analytics.fact_encounters AS e
INNER JOIN analytics.dim_patients AS p
    ON e.patient_id = p.patient_id
GROUP BY
    e.encounter_class,
    p.gender
ORDER BY
    e.encounter_class,
    p.gender;
