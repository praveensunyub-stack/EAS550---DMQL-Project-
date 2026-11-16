# Phase 1 contributions

Team : Praveen, Akshitha, and Thomas. Our work involved designing the tables for Phase 1, loading of Synthea data into the database and verifying the outcome. The assignment has been divided among ourselves based on different roles.

| Team member | Responsibility | Project artifacts |
| --- | --- | --- |
| Praveen | Database Table creation, Primary Key, Foreign Key and constraints and 3NF explanation. | [Schema](../schema.sql), [schema creation](../src/create_schema.py), [ERD](erd.svg), [design note](design_note.md) |
| Akshitha | Data source was prepared, input parameters were validated, code to load the data in one transaction was written, database connection properties were managed, and data source documentation was done. | [Validation](../src/validation.py), [ingestion](../src/ingest_data.py), [source preparation](../src/prepare_data.py), [database configuration](../src/db.py), [subset manifest](../data/subset_manifest.json) |
| Thomas | Reviewed the loaded data individually, did acceptance testing, recorded instructions on re-running the project, and stored the testing results. | [Verification](../src/verify_ingestion.py), [acceptance runner](../src/run_acceptance.py), [README](../README.md), [rerun evidence](../evidence/recorded/rerun_comparison.json) |

For our project, we have made sure to keep all encounters as individual records, we have checked the references, and we have loaded patients and organizations before the encounters. Automated tests have been done and all 33 tests have passed. We have also done the data loading twice and each time we got 111 patients, 267 organizations, and 5,059 encounters. All IDs, complete row hashes, and total values are identical for both data loads.

[integration notes](integration_notes.md) for our project contain information about the completed work and test results. [verification report](../evidence/recorded/verify2.json) and [rerun comparison](../evidence/recorded/rerun_comparison.json) include record counts and data validation.

We worked all together while implementing and testing Phase 1. We even sought some help from AI during debugging in case we had errors in our code. We looked at the suggested solutions, made the necessary adjustments and re-ran our tests. This has been explained in our docs/[AI_USAGE.md](AI_USAGE.md).

