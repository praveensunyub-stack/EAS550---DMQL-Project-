
BEGIN;

CREATE SCHEMA source;

CREATE TABLE source.patients (
    patient_id UUID PRIMARY KEY,
    birth_date DATE NOT NULL,
    death_date DATE,
    gender TEXT NOT NULL,
    CONSTRAINT patients_birth_finite CHECK (isfinite(birth_date)),
    CONSTRAINT patients_death_finite CHECK (death_date IS NULL OR isfinite(death_date)),
    CONSTRAINT patients_death_order CHECK (death_date IS NULL OR death_date >= birth_date),
    CONSTRAINT patients_gender_nonblank CHECK (gender !~ '^[[:space:]]*$')
);

CREATE TABLE source.organizations (
    organization_id UUID PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    state TEXT,
    CONSTRAINT organizations_name_nonblank CHECK (name !~ '^[[:space:]]*$'),
    CONSTRAINT organizations_city_nonblank CHECK (city !~ '^[[:space:]]*$'),
    CONSTRAINT organizations_state_nonblank CHECK (
        state IS NULL OR state !~ '^[[:space:]]*$'
    )
);

CREATE TABLE source.encounters (
    encounter_id UUID PRIMARY KEY,
    patient_id UUID NOT NULL,
    organization_id UUID NOT NULL,
    start_time TIMESTAMPTZ NOT NULL,
    stop_time TIMESTAMPTZ,
    encounter_class TEXT NOT NULL,
    base_encounter_cost NUMERIC(14, 2) NOT NULL,
    CONSTRAINT encounters_patient_fk FOREIGN KEY (patient_id)
        REFERENCES source.patients (patient_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT encounters_organization_fk FOREIGN KEY (organization_id)
        REFERENCES source.organizations (organization_id)
        ON UPDATE RESTRICT ON DELETE RESTRICT,
    CONSTRAINT encounters_start_finite CHECK (isfinite(start_time)),
    CONSTRAINT encounters_stop_finite CHECK (stop_time IS NULL OR isfinite(stop_time)),
    CONSTRAINT encounters_time_order CHECK (stop_time IS NULL OR stop_time >= start_time),
    CONSTRAINT encounters_class_nonblank CHECK (encounter_class !~ '^[[:space:]]*$'),
    CONSTRAINT encounters_cost_nonnegative_finite CHECK (
        base_encounter_cost >= 0
        AND base_encounter_cost NOT IN ('NaN'::NUMERIC, 'Infinity'::NUMERIC, '-Infinity'::NUMERIC)
    )
);


CREATE INDEX encounters_patient_idx ON source.encounters (patient_id);
CREATE INDEX encounters_organization_idx ON source.encounters (organization_id);

COMMENT ON SCHEMA source IS 'Phase 1 normalized Synthea source tables only';
COMMENT ON TABLE source.encounters IS 'One row per original Synthea encounter UUID';
COMMENT ON COLUMN source.encounters.stop_time IS 'NULL means no recorded end; do not invent an end or duration';
COMMENT ON COLUMN source.encounters.base_encounter_cost IS 'Synthea BASE_ENCOUNTER_COST in USD; excludes broader claim costs';

COMMIT;
