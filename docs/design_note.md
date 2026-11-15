# Phase 1 Relational Design

## Scope and table relationships

As part of Phase 1, we developed three normalized PostgreSQL tables, namely, `source.patients`, `source.organizations`, and `source.encounters`. We chose the necessary columns to get encounter counts based on class and organization, as well as base encounter cost and duration. Relational source tables only are developed in Phase 1. Fact tables, dimension tables, and dbt models will be developed in Phase 2.

We took all 111 patients, 267 organizations, and 5,059 encounters from the selected Synthea CSV files. All 111 patients and 232 organizations have encounters; however, there are 35 organizations without encounters, which we included due to valid records. [subset manifest](../data/subset_manifest.json) includes the information about the selected files and their checksums, while [ERD](erd.svg) demonstrates the relationship between the tables.

For each record, we used the original encounter UUID. Every encounter is linked with one patient and one organization through foreign keys. One patient or organization may have multiple encounters or none at all. Encounters table links patients and organizations while keeping each visit separate. There is no uniqueness constraint between patients and organizations since the same patient can visit the same organization multiple times within the same recorded time frame.

## Functional dependencies and 3NF

Our selected attributes have these functional dependencies:

- `patient_id -> birth_date, death_date, gender`.
- `organization_id -> name, city, state`.
- `encounter_id -> patient_id, organization_id, start_time, stop_time, encounter_class, base_encounter_cost`.

Each table holds atomic elements and has a one-column primary key, which is a condition for the fulfillment of first normal form and absence of partial dependencies from a composite key. Based on our assumptions about the domain, none of the selected non-key attributes is a determinant of another non-key attribute in the same table. Names of organizations are not necessarily unique, cities do not uniquely determine states, and encounter class does not determine a certain cost or duration. Thus, the tables are in third normal form.

We put all the attributes of patients and organizations to their tables. Including the name of an organization in encounters would generate the transitive dependency `encounter_id -> organization_id -> name`. Also, we did not include clinical code/description couples that should be explicitly keyed terminologies if added. Attributes related to providers, payers, and claims fall out of our selection. We did not add more general simulation totals like total revenue of an organization and healthcare costs of a patient, since they are not properties of any encounter.

## Data types and constraints

UUID primary keys were selected to retain unique identifiers from sources. Primary keys ensure uniqueness and non-nullity, thus there was no need to create redundant `UNIQUE` constraints and uniqueness for names and visits. Restrictions are applied for updates and deletions for foreign keys to avoid orphaned visits. Patient and organization foreign keys are indexed for relations' retrieval.

Dates of birth and death are `DATE` type; start and stop times for encounters are `TIMESTAMPTZ`. Non-null fields are required, as well as non-empty text fields. Fields for death date, stop time and organization state can be `NULL`. If date or time is `NULL`, this means that value is not available. If death date is presented, it should not be before birth date; if stop time is presented, it should not be before start time. Date and timestamp values also do not allow infinite values.

The attribute that stores the base encounter cost has been declared to be of `NUMERIC(14,2)` data type in order to keep the financial values as accurate as possible. The value zero is permitted whereas negative numbers and non-finite numbers are not accepted. Invalidation of entries with excessive decimal places happens before storing them.

## Loading and verification

The ingestion program loads data into pandas using strings, then validates identifiers, types, required fields, duplicate and parent fields. It outputs number of accepted rows, corrected rows and rejected rows. Optional blanks become nulls. Identical duplicate rows keep the first instance while duplicate rows with conflicting IDs are rejected collectively.

Transactional full replacement was implemented using SQLAlchemy. This loader deletes children rows before parents and loads patients and organizations before encounters. This loader keeps the same table design, constraints and indexes. If the database operation fails, the entire replacement is rolled back, and an empty accepted table is rejected and deleted.

The logs of the two executions showed successful loading of all chosen rows without any corrections or rejections. Two full load operations created identical hashes for primary keys and complete rows with base encounter cost. The key, reference and required domain validations passed. The cross table chronology validation is done separately from row constraints. There are ten encounters that occur after recorded death date but those encounters are kept as anomalies in the source because we do not know their reason.

