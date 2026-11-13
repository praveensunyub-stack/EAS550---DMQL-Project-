# EAS 550 – Phase 1: Synthea Database Project

**Team members:** Praveen, Akshitha, and Thomas

## Scope

Phase 1 will include building a small relational database based on Synthea healthcare data. We will be using Python with Pandas and SQLAlchemy for data checking and data loading into PostgreSQL.

There are three tables: source.patients, source.organizations, and source.encounters. Each encounter belongs to one patient and one organization. We will keep each encounter as a single record since a single patient may visit an organization more than once.

This phase will include database schema creation, ER diagram creation, data checking, data loading, and re-running of the data loading process to verify the consistency of the results.


## Dataset

We have used the synthea_sample_data_csv_latest.zip file provided in the link sent to us by our professor.

For this task, we have chosen 15 columns out of three CSV files and retained all the rows. We did not randomly select any records nor filter them on the basis of dates.

| CSV file | Rows kept |
| --- | ---: |
| `patients.csv` | 111 |
| `organizations.csv` | 267 |
| `encounters.csv` | 5,059 |

The small dataset is stored in the form of data/phase1_subset.zip file.

## Proposed Roles

We have decided that all of us three will work on this in the following way:

| Team member | Proposed work |
| --- | --- |
| **Praveen** | Creation of database tables and relations, making an ER diagram, database rules creation and writing of SQL queries for data verification. |
| **Akshitha** | Data set creation, input data checking, writing Python code to load data into the database, connecting the database and testing data verification. |
| **Thomas** | Database tests creation, checking whether reloading the same data is working well, noting test results and helping with documentation of the project. |

We will review each other’s work and record the completed and reviewed tasks in contributions.md.