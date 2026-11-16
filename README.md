# EAS 550 Phase 1 Synthea Relational Foundation

**Team:** Praveen, Akshitha, and Thomas

For Phase 1 project, we have written the Python script for loading and validating the data available in the following three PostgreSQL tables:Patients, Organizations,Encounters. We are utilizing the original encounter IDs for this particular project. The selected columns provide information to calculate the number of encounters per class/organization, base encounter costs, and duration. In Phase 1, we are focusing on the above three source tables only.

## Source data and relational design

We took the dataset provided via our professor’s link for the Synthea. We retained all rows in patients.csv, organizations.csv, and encounters.csv but selected only the needed columns.

| Table | Rows |
| --- | ---: |
| Patients | 111 |
| Organizations | 267 |
| Encounters | 5,059 |

There is no filtering of data by date nor any random selection of rows. There are 111 patients and 232 organizations related to encounters. 35 organizations have no encounters, but those are kept as valid records. The small dataset was saved in data/phase1_subset.zip file containing 15 selected columns from 3 CSV files. Subset manifest consists of information about selected columns, number of rows in each table, hashes of original files and hashes of subsets. Source data were verified on November 12, 2026, but we don’t know the version of the simulator or the original publishing date.

UUID is the primary key in each table. Every encounter is related to one patient and one organization through foreign keys. One patient and one organization may be related to many encounters or even have no encounters at all. When the same patient visits the same organization more than once, each visit is recorded as a new row. Empty death date and stop time values are allowed, NUMERIC(14,2) was used for storing the precise base encounter cost.

The (([docs/erd.svg](https://github.com/praveensunyub-stack/EAS550---DMQL-Project-/blob/main/docs/erd.md))) displays the relationship between our tables. Our (docs/design_note.md) describes functional dependencies, 3NF, database constraints, and exceptions. The schema.sql file will create our tables and indexes when it runs in an empty database.

Our data source is Synthea, a synthetic patient generator by The MITRE Corporation. We used its [CSV dictionary](https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary) to identify the column names. The data is synthetic, so our results only demonstrate how the database works and are not clinical conclusions.

## Setup and execution

For the program to work, Python 3.12 and PostgreSQL must be installed on the local system. The `createdb` and `psql` commands must be available in the PATH environment variable. All commands must be executed from the project root directory, which contains the `schema.sql` file. In our setup, we used Python 3.12.14, PostgreSQL 18.6, Pandas 3.0.1, SQLAlchemy 2.0.44, and psycopg 3.2.12 on Windows.

Now, set up the Python virtual environment and then install the necessary packages:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

We now have to configure the PostgreSQL connection settings for our system. Host, port, and user name may vary as per the PostgreSQL installation. Password will be supplied at the prompt:

```powershell
$env:PGHOST = '127.0.0.1'
$env:PGPORT = '5432'
$env:PGDATABASE = 'eas550_phase1'
$env:PGUSER = 'postgres'
$env:PGSSLMODE = 'disable'
$env:PGPASSWORD = [System.Net.NetworkCredential]::new('', (Read-Host 'Local PostgreSQL password' -AsSecureString)).Password
```

The Python code uses environment variables for the database connection configuration. It does not parse .env file automatically. The .env.example file contains the name of the environment variables without any value, and .gitignore is utilized to prevent pushing the real environment files. The above SSL configuration was used for our local PostgreSQL server. In case of a remote server, the corresponding TLS configurations should be made.

Now that you have configured the connection, created an empty database, and prepared the needed data, let us conduct the acceptance tests:

```powershell
createdb -h $env:PGHOST -p $env:PGPORT -U $env:PGUSER $env:PGDATABASE
.\.venv\Scripts\python.exe -m src.prepare_data --bundled --out data/raw
.\.venv\Scripts\python.exe -m src.run_acceptance --data-dir data/raw --manifest data/subset_manifest.json --output-dir evidence/reproduced
```

If the database is already made and is empty, then we can skip the step of making the database using `createdb` command. Acceptance program requires the source schema to be absent, and also the output folder must be empty or doesn’t exist yet. If you wish to run an acceptance test again, then you require to make a new database and also a new evidence folder. If the tables are present already, then you can use the following commands to reload.

Firstly, the acceptance program creates the tables, loads the small test data from tests/fixtures/valid/ and checks for the result. Then it loads the full selected dataset twice and compares both of the results. Small test data contains 2 patients, 2 organizations and 3 encounters where one of the encounter has no stop time. In case of successful execution, then you will see:

```text
PASS: small fixture, full source load, source-to-database reconciliation, and unchanged rerun.
```

Test report files are stored in evidence/reproduced/. Any failed test would result in a non-zero exit code. In case of macOS or Linux, we could use python3 -m venv .venv and .venv/bin/python along with shell export for six connection variables. Rest all of Python module arguments would remain the same.

## Validation and safe reruns

Our reading process utilizes Pandas to load the CSV data as strings before transforming them into UUIDs, dates, timestamp with timezone, and Decimal values. Our validation process covers the necessary columns, IDs, duplicate rows, patient and organization IDs references, dates, and cost. The empty optional values will become null. Any additional space, case differences between UUID letters, and uppercases for encounter classes will be fixed and reported. In case of duplicate rows with the same selected data, the first record will be kept. If the same ID is associated with the different data, all the rows with the same ID will be rejected. If the encounter belongs to the patient or organization which is invalid, then the encounter will be rejected.

The loading reports include the total number of input rows, the number of accepted rows, corrected rows, and rejected rows. It also provides the reasons for rejection, source row numbers, expected null values, and warning IDs. There could be several issues for one row, so the total number of reasons for rejection might be greater than the total number of rejected rows.

The reload of the data using SQLAlchemy will happen in one transaction, where we delete the encounters and the patients and organizations. Then, we insert the patients and organizations and the encounters. It won’t affect the existing tables, constraints, and indexes. We also have an advisory lock to prevent multiple loaders from running at the same time. While the load process is going on, no other process should perform any action on the source schema. All changes will be reverted if there is an error with any of the database actions. Also, we halt the reload process before removing the existing data if there is any accepted table that is empty.

To reload the data in an existing Phase 1 database, we can use the following commands:

```powershell
.\.venv\Scripts\python.exe -m src.ingest_data --data-dir data/raw --manifest data/subset_manifest.json --report evidence/manual/load1.json
.\.venv\Scripts\python.exe -m src.verify_ingestion --data-dir data/raw --report evidence/manual/verify1.json
.\.venv\Scripts\python.exe -m src.ingest_data --data-dir data/raw --manifest data/subset_manifest.json --report evidence/manual/load2.json
.\.venv\Scripts\python.exe -m src.verify_ingestion --data-dir data/raw --report evidence/manual/verify2.json --compare evidence/manual/verify1.json
```

If we need to retain our previous reports, we can create another folder for our new reports. Verification works on the basis of checking the database through a snapshot and comparing it with the input validated data. The checks are done against row count, primary key, selected values, calculated measures, table names, and rules for the data. Matching of row count alone is not enough, so we also do data checks.

## Recorded results

Acceptance Test Recording:
The test was performed using our dataset twice, with each run containing 111 patients, 267 organizations, and 5,059 encounters. No rows have been corrected or rejected.

| Check | Result |
| --- | --- |
| Primary-key and complete-row hashes across both loads | Identical for all three tables |
| Base encounter cost total | 609,964.59 USD |
| Completed duration total | 89,458,859 seconds |
| Duplicate keys and missing parent references | 0 |
| Invalid costs, encounters before birth, and stops before starts | 0 |
| Null death dates | 99 |
| Encounters starting after a recorded death date | 10 retained warnings |

The ten encounters that start after the recorded death date are all Synthea "Death Certification" encounters, which the simulator schedules after death. They are valid, so we keep their original values and report their encounter IDs as warnings. The full input has no missing stop times; the small fixture verifies that a missing stop time remains valid.

The test result data is stored in (evidence/recorded/load1.json), (evidence/recorded/verify1.json), (evidence/recorded/load2.json), (evidence/recorded/verify2.json), and the (evidence/recorded/rerun_comparison.json). If we conduct the test once more, then timestamp may be different, but the results would remain the same.

## Query the relationships

Open `psql` using the configured environment variables:

```powershell
psql -X -v ON_ERROR_STOP=1
```

Once the connection with the database is established, then the following SQL query can be executed for viewing the encounters with patients and organizations details:

```sql
SELECT e.encounter_id, p.patient_id, p.birth_date,
       o.organization_id, o.name, e.encounter_class,
       e.start_time, e.stop_time, e.base_encounter_cost
FROM source.encounters AS e
JOIN source.patients AS p ON p.patient_id = e.patient_id
JOIN source.organizations AS o ON o.organization_id = e.organization_id
ORDER BY e.encounter_id
LIMIT 10;
```

Type `\q` to return to PowerShell.

## Team records

We have already talked about the contributions of our team members and project files in (docs/contributions.md). The test results and other information are available in (docs/integration_notes.md). We have also performed the tests, analyzed the results, and kept the reports for our project.
