# Database entity-relationship overview

Core relational model for orgs, users, pipelines, traces, chunks, and analysis jobs. Primary keys are `VARCHAR(36)` UUIDs. Full column detail lives in `backend/app/models/models.py` and Alembic migrations.

```mermaid
erDiagram
    ORGANIZATIONS ||--o{ USERS : has
    ORGANIZATIONS ||--o{ ORGANIZATION_MEMBERS : includes
    USERS ||--o{ ORGANIZATION_MEMBERS : joins
    USERS ||--o{ PIPELINES : owns
    USERS ||--o{ API_KEYS : issues
    USERS ||--o{ REFRESH_TOKENS : holds
    USERS ||--o| USER_SETTINGS : configures
    PIPELINES ||--o{ QUERY_TRACES : records
    QUERY_TRACES ||--o{ RETRIEVED_CHUNKS : contains
    QUERY_TRACES ||--o| ANALYSIS_JOBS : analyzed_by
    PIPELINES ||--o{ DOCUMENTS : indexes
    USERS ||--o{ ALERT_RULES : defines
    USERS ||--o{ FIX_RECOMMENDATIONS : receives

    ORGANIZATIONS {
        string id PK
        string name
        string slug UK
        boolean sso_required
        boolean mfa_required
    }
    USERS {
        string id PK
        string organization_id FK
        string email UK
        string password_hash
        enum role
        enum subscription_plan
        boolean email_verified
    }
    PIPELINES {
        string id PK
        string user_id FK
        string name
        int queries_per_month
        float cost_per_wrong_answer_usd
    }
    QUERY_TRACES {
        string id PK
        string pipeline_id FK
        string query_text
        string answer_text
        float faithfulness_score
        float grounded_fraction
        enum failure_type
        string status
    }
    RETRIEVED_CHUNKS {
        string id PK
        string trace_id FK
        string content
        float similarity_score
        float bm25_score
        boolean is_flagged
    }
    ANALYSIS_JOBS {
        string id PK
        string trace_id FK
        enum status
        string error_message
    }
    API_KEYS {
        string id PK
        string user_id FK
        string key_hash
        string prefix
        boolean is_active
    }
```

Indexes for list filters (status, pipeline, created_at) are documented in [`INDEXES.md`](../INDEXES.md). Vector extension is optional on Postgres for embedding workloads.

See also: [DATABASE.md](../engineering/DATABASE.md).
