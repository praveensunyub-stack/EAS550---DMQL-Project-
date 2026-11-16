# Phase 1 integration notes

Our automated integration test was done using a new database in PostgreSQL 18.6. 

## Integrated design

There were three normalized tables as the sources which include Patients, Organizations and Encounters. Each encounter has its unique id and is linked to a pre-existing patient and organization. For example, if a patient returns to the same organization on different occasions, there will be separate entries for each occasion. Empty stop times will be accepted, while different encounter classes can be accepted as long as they are not null.

The validation process before loading the data involved validation of data types, missing values, ids, dates, costs, duplicates and references. For data loading, one SQLAlchemy transaction was used. Encounters will be deleted, followed by deleting the patients and organizations. The patients and organizations will be inserted and finally the encounters will be inserted. The schema and constraints will remain unchanged. Loading failure was tested to verify the rollback of changes in case of failures.

## Corrections and results

Some additional tests were conducted for incorrect time zone offset values and presence of NUL character. Changes in verification process were done in order to prevent overwriting of the original comparison results. Duration totals and full row hashes were used to verify the data, as row counts and totals sometimes may not cover all the differences between datasets.

In our recording, at the beginning, a small dataset was checked that contained 2 patients, 2 organizations and 3 encounters. Later, full dataset was loaded twice, and both times the result was 111 patients, 267 organizations and 5,059 encounters with 0 corrected and 0 rejected rows. Also, the duplicates, missing references, invalid costs, pre-birth date encounters and stop times prior to start times were tested and none of those were found.

The results of our recorded test results revealed that there were 33 successful tests, which comprised of 18 validation tests, 3 fingerprint tests, and 12 database and transaction tests. The two full loads had the same IDs, row hash, data quality results, and totals.

There are 10 cases where the starting time was later than the patient's death date. We retained all the records. All ten are Synthea "Death Certification" encounters, which the simulator schedules after death, so they are valid. We did not make any changes to any original value. The results are visible in the verification report.

We all three have worked together in implementing and testing this project. Sometimes we even took help from AI while debugging the code in case there were any errors. After doing the error corrections, we executed the test again and did the verification.
