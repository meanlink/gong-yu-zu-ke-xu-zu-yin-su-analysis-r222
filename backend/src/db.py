import time
from pathlib import Path
import psycopg
from psycopg.rows import dict_row
from .config import DATABASE_URL

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
 id SERIAL PRIMARY KEY,
 email TEXT UNIQUE NOT NULL,
 full_name TEXT NOT NULL,
 role TEXT NOT NULL CHECK (role IN ('analyst','customer_manager','service_coordinator')),
 password_hash TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS properties (
 id SERIAL PRIMARY KEY,
 code TEXT UNIQUE NOT NULL,
 name TEXT NOT NULL,
 neighborhood TEXT NOT NULL,
 monthly_rent NUMERIC(10,2) NOT NULL,
 floor INTEGER NOT NULL,
 property_age_years NUMERIC(5,2) NOT NULL,
 occupancy_status TEXT NOT NULL DEFAULT 'occupied',
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS tenants (
 id SERIAL PRIMARY KEY,
 full_name TEXT NOT NULL,
 email TEXT UNIQUE NOT NULL,
 property_id INTEGER NOT NULL REFERENCES properties(id),
 move_in_date DATE NOT NULL,
 lease_end_date DATE NOT NULL,
 status TEXT NOT NULL CHECK (status IN ('active','moved_out')) DEFAULT 'active',
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS service_events (
 id SERIAL PRIMARY KEY,
 tenant_id INTEGER NOT NULL REFERENCES tenants(id),
 property_id INTEGER NOT NULL REFERENCES properties(id),
 category TEXT NOT NULL,
 severity TEXT NOT NULL CHECK (severity IN ('routine','urgent','emergency')),
 opened_at TIMESTAMPTZ NOT NULL,
 resolved_at TIMESTAMPTZ,
 resolution_days NUMERIC(8,2),
 satisfaction_score NUMERIC(5,2),
 status TEXT NOT NULL CHECK (status IN ('open','resolved','cancelled')) DEFAULT 'open',
 summary TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS renewal_surveys (
 id SERIAL PRIMARY KEY,
 tenant_id INTEGER NOT NULL REFERENCES tenants(id),
 lease_period TEXT NOT NULL,
 collected_at TIMESTAMPTZ NOT NULL,
 cleanliness_score NUMERIC(5,2) NOT NULL,
 service_score NUMERIC(5,2) NOT NULL,
 value_score NUMERIC(5,2) NOT NULL,
 community_score NUMERIC(5,2) NOT NULL,
 renewal_intent NUMERIC(5,2) NOT NULL,
 comments TEXT,
 status TEXT NOT NULL CHECK (status IN ('submitted','reviewed','archived')) DEFAULT 'submitted',
 analyzed_at TIMESTAMPTZ,
 reviewed_at TIMESTAMPTZ,
 UNIQUE (tenant_id, lease_period)
);
CREATE TABLE IF NOT EXISTS follow_up_tasks (
 id SERIAL PRIMARY KEY,
 tenant_id INTEGER NOT NULL REFERENCES tenants(id),
 survey_id INTEGER NOT NULL REFERENCES renewal_surveys(id),
 task_type TEXT NOT NULL,
 priority TEXT NOT NULL CHECK (priority IN ('high','medium','low')),
 owner TEXT NOT NULL,
 due_date DATE NOT NULL,
 status TEXT NOT NULL CHECK (status IN ('open','contacted','closed')) DEFAULT 'open',
 reason TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 UNIQUE (survey_id)
);
CREATE TABLE IF NOT EXISTS audit_logs (
 id SERIAL PRIMARY KEY,
 actor_email TEXT NOT NULL,
 action TEXT NOT NULL,
 entity_type TEXT NOT NULL,
 entity_id INTEGER,
 detail TEXT NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
"""

def connect():
    return psycopg.connect(DATABASE_URL, row_factory=dict_row)

def init_db():
    last = None
    for _ in range(30):
        try:
            with connect() as conn:
                conn.execute(SCHEMA)
                migrations = Path(__file__).resolve().parents[1] / 'migrations'
                for migration in sorted(migrations.glob('*.sql')):
                    conn.execute(migration.read_text())
                conn.commit()
            return
        except Exception as exc:
            last = exc
            time.sleep(2)
    raise last

def query(sql, params=()):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

def one(sql, params=()):
    rows = query(sql, params)
    return rows[0] if rows else None

def execute(sql, params=()):
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            result = cur.fetchone() if cur.description else None
        conn.commit()
        return result
