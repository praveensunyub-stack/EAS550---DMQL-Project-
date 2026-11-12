# Synthea source and selection

This is synthetic data from the Synthea project, published by the Synthetic Health community and The MITRE Corporation. The publisher permits unrestricted use and requests attribution. No real patient records are used.

- Publisher and small sample: https://synthetichealth.github.io/synthea-sample-data/
- CSV field dictionary: https://github.com/synthetichealth/synthea/wiki/CSV-File-Data-Dictionary
- Input supplied by the user: `synthea_sample_data_csv_latest.zip`.
- Inspection date: November 11, 2026. Original retrieval date, generator version and generation date: **unknown**. Do not infer them from the filename or filesystem timestamp.
- SHA-256: `990d52064037bbf83d10f13163da428964b56ae673b7f39bf549d78c1e7eda16`.

## Reproducing the exact input

The exact supplied ZIP is available from the publisher at a commit-pinned URL:

https://raw.githubusercontent.com/synthetichealth/synthea-sample-data/84f59805d481b9f01f3141ef39e68bdbbeb80132/downloads/latest/synthea_sample_data_csv_latest.zip

Run `python scripts/download_data.py` from the project root. The script verifies SHA-256 before saving into ignored `data/raw/`, reuses a matching existing archive and refuses to overwrite a different one. The publisher repository commit is `84f59805d481b9f01f3141ef39e68bdbbeb80132`, dated October 21, 2026, 23:20:05 UTC in its commit metadata. This establishes a repository snapshot, not the data generation date. The pinned download was independently compared with the user's supplied archive on November 11, 2026. The ZIP is not committed, and the loader refuses a checksum mismatch by default.

Select all rows from only `patients.csv`, `organizations.csv`, and `encounters.csv` in the ZIP. Select the columns listed below. Keep all organizations, including the 35 with no encounters. This deterministic row selection preserves every referenced parent. Source counts are 111 patients, 267 organizations and 5,059 encounters; accepted counts must be justified by the validation report, not forced to match.

| Member | SHA-256 of uncompressed CSV bytes |
|---|---|
| patients.csv | `7cc321753455e7cd0cabe0d7526432d7329fe6a4522e408f97a62819ee99e280` |
| organizations.csv | `1b7d32d8ef8ac165c59e7861119a901e3296eb36d3f2baa15140ed01cb159c78` |
| encounters.csv | `7f9723603541d7dc64d4cbb4862b5d381513e8d4f0c812b74caa6f1749856ef8` |

## Column mapping

| CSV | Source field | Database column |
|---|---|---|
| patients | Id | source.patients.patient_id |
| patients | BIRTHDATE | birth_date |
| patients | DEATHDATE | death_date |
| patients | GENDER | gender |
| organizations | Id | source.organizations.organization_id |
| organizations | NAME | name |
| encounters | Id | source.encounters.encounter_id |
| encounters | PATIENT | patient_id |
| encounters | ORGANIZATION | organization_id |
| encounters | START | start_time |
| encounters | STOP | stop_time |
| encounters | ENCOUNTERCLASS | encounter_class |
| encounters | BASE_ENCOUNTER_COST | base_encounter_cost |

Other columns are deliberately omitted. Code/description pairs can introduce additional dependencies; provider/payer IDs are outside the three-table scope. Patient names, SSNs and addresses are not needed. Base encounter cost excludes broader claim line items; total claim cost and payer coverage are not loaded or mislabeled. Derive age, duration and encounter counts in queries.

## Rules and valid exceptions

Keys must be UUIDs and required fields must be present. Whitespace normalization and canonical representations are explained in loader reports. Invalid nonempty dates, timestamps or amounts are rejected rather than converted to NULL. Dates and aware timestamps must parse and be finite; death must not precede birth, stop must not precede start, and encounter start must not precede patient birth. These are subset-quality rules, not clinical claims.

Death and stop may be absent. Names are not unique, and a patient may visit the same organization repeatedly. The fixed snapshot permits ten encounter classes: ambulatory, emergency, home, hospice, inpatient, outpatient, snf, urgentcare, virtual and wellness. Future snapshots require a reviewed contract change. Costs are finite nonnegative Decimal values with no more than two decimal places and no more than 12 integer digits. Invalid rows receive explicit reasons; parent rejection can cause encounter rejection.

Duplicate comparison uses selected strings after trimming, canonical UUID spelling and class lowercasing. Identical normalized rows keep the first occurrence; conflicting rows sharing an ID are rejected as a group. Textually different money/timestamp spellings are conservatively treated as conflicts even if they could represent the same amount/instant. The validation report reconciles every input row into exactly one outcome: accepted unchanged, accepted corrected, rejected or removed duplicate. Inspect the implemented details in `src/eas550/source.py` and the saved evidence.

The inspected ZIP has 18 CSV members, no duplicate/missing/invalid IDs in the selected tables, and no unresolved patient/organization references. There are 252 distinct organization names and 294 recurring patient/organization pairs. All observed stop timestamps are populated, but absence remains valid. These source findings alone are not evidence of a successful database load.
