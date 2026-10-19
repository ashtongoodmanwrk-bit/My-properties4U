# Database design

Entity-relationship diagram of the PostgreSQL schema. `PK` is a primary key, `FK` a foreign key and `UK` a unique column.

```mermaid
erDiagram
    USERS ||--o{ PROPERTIES : owns
    PROPERTIES ||--o{ UNITS : contains
    UNITS ||--o{ LEASES : "is leased by"
    USERS ||--o{ LEASES : "rents as tenant"
    LEASES ||--o{ RENT_CHARGES : generates
    RENT_CHARGES ||--o{ PAYMENTS : "is paid by"
    USERS ||--o{ PAYMENTS : makes
    UNITS ||--o{ MAINTENANCE_REQUESTS : has
    USERS ||--o{ MAINTENANCE_REQUESTS : reports
    USERS |o--o{ AUDIT_LOG : "acts in"

    USERS {
        int id PK
        string email UK
        string password_hash
        string full_name
        string role "landlord, tenant or admin"
        datetime created_at
    }
    PROPERTIES {
        int id PK
        int owner_id FK
        string name
        string address_line
        string city
        string postcode
        datetime created_at
    }
    UNITS {
        int id PK
        int property_id FK
        string unit_number "unique per property"
        int bedrooms
        decimal monthly_rent
    }
    LEASES {
        int id PK
        int unit_id FK
        int tenant_id FK
        date start_date
        date end_date
        decimal rent_amount
        int due_day "1 to 28"
        string status "active, ended or cancelled"
        datetime created_at
    }
    RENT_CHARGES {
        int id PK
        int lease_id FK
        date due_date "unique per lease"
        decimal amount
        string status "pending, partial, paid or overdue"
        datetime reminder_sent_at
    }
    PAYMENTS {
        int id PK
        int rent_charge_id FK
        int user_id FK
        decimal amount
        string method "card, bank_transfer or cash"
        string idempotency_key "unique per user"
        datetime paid_at
    }
    MAINTENANCE_REQUESTS {
        int id PK
        int unit_id FK
        int reported_by FK
        string title
        string description
        string category
        string priority
        string status "submitted, assigned, in_progress or resolved"
        string assigned_to
        datetime created_at
        datetime updated_at
        datetime resolved_at
    }
    AUDIT_LOG {
        int id PK
        int actor_id FK
        string entity
        int entity_id
        string action
        json old_values
        json new_values
        datetime created_at
    }
```

## Rules enforced by the database

- **No overlapping active leases per unit:** an exclusion constraint (`btree_gist`, a date range over `start_date` and `end_date`, applied where `status = 'active'`).
- **No duplicate payments:** a unique constraint on `(user_id, idempotency_key)`.
- **One rent charge per lease per due date:** a unique constraint on `(lease_id, due_date)`.
- **Valid values:** check constraints on roles, statuses, categories, priorities, payment methods, positive amounts, the lease date order and `due_day`.
- **Balances:** a view, `v_charge_balances`, gives each charge's paid and outstanding amounts for the dashboard queries.

`audit_log.entity_id` points at a row in whichever table `entity` names, so it is deliberately not a foreign key.
