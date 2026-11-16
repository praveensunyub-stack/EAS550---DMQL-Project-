# Phase 1 Team Contributions

Our team has three members: Praveen, Akshitha, and Thomas. We have divided the Phase 1 work into database design, data preparation and loading, and testing and verification. The table below shows the roles we agreed to work on. We will update it as each person finishes their work and reviews another member's changes.

## Planned Responsibilities

| Team member | Main responsibility | Related files |
| --- | --- | --- |
| **Praveen** | Work on the table structure, ER diagram, keys, constraints, and SQL checks. | [schema.sql](../schema.sql), [create_schema.py](../src/create_schema.py), [erd.md](erd.md), [design_note.md](design_note.md), [verify.sql](../sql/verify.sql) |
| **Akshitha** | Prepare the selected Synthea data, check for invalid values, load the data into PostgreSQL, and test the validation code. | [data/README.md](../data/README.md), [build_subset.py](../src/build_subset.py), [validation.py](../src/validation.py), [ingest_data.py](../src/ingest_data.py), [db.py](../src/db.py), [test_validation.py](../tests/test_validation.py) |
| **Thomas** | Check the loaded data, test the database rules, compare repeated loads, and document the test steps and results. | [verify_ingestion.py](../src/verify_ingestion.py), [run_acceptance.py](../src/run_acceptance.py), [test_database.py](../tests/test_database.py), [test_verification.py](../tests/test_verification.py), [evidence/README.md](../evidence/README.md), [project README](../README.md) |

## Test Results Recorded in the Project

The existing test logs report **33 passing automated tests**: 18 validation tests, 3 fingerprint tests, and 12 PostgreSQL and transaction tests. They also report two full data loads with **111 patients, 267 organizations, and 5,059 encounters**. The recorded loads match on primary keys, complete-row hashes, and measures. The recorded base encounter cost total is **609,964.59 USD**, and the completed encounter duration total is **89,458,859 seconds**.

These results come from the project's recorded tests. They do not, by themselves, show which team member ran a test or made a particular change. The details are in the [unit-test log](../evidence/recorded/unit_tests.txt), [database-test log](../evidence/recorded/database_tests.txt), and [rerun comparison](../evidence/recorded/rerun_comparison.json).

## Work and Reviews to Record

As we complete our parts, we will add the actual GitHub issue, commit, pull-request, and review links here. We will also note any problems we found and how we fixed them. This is important because the planned roles above are not a record of completed individual contributions.

The project implementation and recorded automated runs used Codex assistance. We have documented this in [AI_USAGE.md](AI_USAGE.md). We will keep our team discussions and integration results in [integration_notes.md](integration_notes.md).
