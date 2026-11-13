# Phase 1 ER Diagram

```mermaid
erDiagram
    PATIENTS ||--o{ ENCOUNTERS : has
    ORGANIZATIONS ||--o{ ENCOUNTERS : hosts

    PATIENTS {
        UUID patient_id PK
        DATE birth_date
        DATE death_date
        TEXT gender
    }

    ORGANIZATIONS {
        UUID organization_id PK
        TEXT name
        TEXT city
        TEXT state
    }

    ENCOUNTERS {
        UUID encounter_id PK
        UUID patient_id FK
        UUID organization_id FK
        TIMESTAMPTZ start_time
        TIMESTAMPTZ stop_time
        TEXT encounter_class
        NUMERIC base_encounter_cost
    }
```

We have 3 tables: `source.patients`, `source.organizations` and `source.encounters`. One encounter is associated with one patient and one organization. One patient or one organization may have several encounters (including zero).

`PK` is primary key, `FK` is foreign key. Only `death_date`, `state` and `stop_time` may be NULL. Each encounter has an id of its own, so that one patient may have more than one encounter at the same organization.



![ER diagram as SVG](erd.svg)
