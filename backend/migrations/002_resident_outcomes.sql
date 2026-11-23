ALTER TABLE follow_up_tasks ADD COLUMN IF NOT EXISTS lease_end_snapshot date;
UPDATE follow_up_tasks f SET lease_end_snapshot=t.lease_end_date
    FROM tenants t WHERE f.tenant_id=t.id AND f.lease_end_snapshot IS NULL;

CREATE TABLE IF NOT EXISTS retention_remedy (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id integer NOT NULL REFERENCES follow_up_tasks(id),
    event_id integer NOT NULL UNIQUE REFERENCES service_events(id),
    promise_due date NOT NULL,
    tenant_impact text NOT NULL CHECK (length(tenant_impact) >= 4),
    status text NOT NULL DEFAULT 'assigned' CHECK (status IN ('assigned','pending_check','rework','accepted','cancelled')),
    created_by integer NOT NULL REFERENCES users(id),
    evidence text,
    evidence_at timestamptz,
    evidence_by integer REFERENCES users(id),
    reviewed_by integer REFERENCES users(id),
    review_note text,
    revision integer NOT NULL DEFAULT 0 CHECK (revision >= 0),
    CHECK (status IN ('assigned','cancelled') OR (evidence IS NOT NULL AND evidence_by IS NOT NULL AND evidence_at IS NOT NULL)),
    CHECK (status NOT IN ('rework','accepted') OR (reviewed_by IS NOT NULL AND review_note IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS checkout_appointment (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id integer NOT NULL REFERENCES follow_up_tasks(id),
    tenant_id integer NOT NULL REFERENCES tenants(id),
    property_id integer NOT NULL REFERENCES properties(id),
    lease_end date NOT NULL,
    starts_at timestamptz NOT NULL,
    ends_at timestamptz NOT NULL CHECK (ends_at > starts_at),
    instructions text NOT NULL CHECK (length(instructions) >= 4),
    status text NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled','cancelled','completed')),
    created_by integer NOT NULL REFERENCES users(id),
    acted_by integer REFERENCES users(id),
    inspection_reference text,
    returned_keys integer CHECK (returned_keys BETWEEN 0 AND 20),
    unit_condition text CHECK (unit_condition IN ('ready','repair')),
    CHECK (status <> 'completed' OR (inspection_reference IS NOT NULL AND returned_keys IS NOT NULL AND unit_condition IS NOT NULL AND acted_by IS NOT NULL))
);
CREATE UNIQUE INDEX IF NOT EXISTS checkout_tenancy_slot ON checkout_appointment (tenant_id, lease_end) WHERE status <> 'cancelled';
CREATE INDEX IF NOT EXISTS checkout_property_slot ON checkout_appointment (property_id, starts_at, ends_at) WHERE status <> 'cancelled';

CREATE TABLE IF NOT EXISTS renewal_result (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id integer NOT NULL REFERENCES follow_up_tasks(id),
    tenant_id integer NOT NULL REFERENCES tenants(id),
    lease_end date NOT NULL,
    result text NOT NULL CHECK (result IN ('renewed','moved_out')),
    intent_score numeric(5,2) NOT NULL CHECK (intent_score BETWEEN 1 AND 10),
    appointment_id integer REFERENCES checkout_appointment(id),
    new_lease_end date,
    supporting_reference text NOT NULL CHECK (length(supporting_reference) >= 4),
    status text NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted','returned','confirmed')),
    revision integer NOT NULL DEFAULT 1 CHECK (revision > 0),
    created_by integer NOT NULL REFERENCES users(id),
    reviewed_by integer REFERENCES users(id),
    review_note text,
    UNIQUE (tenant_id, lease_end),
    CHECK ((result = 'renewed' AND new_lease_end >= lease_end + 30 AND new_lease_end IS NOT NULL AND appointment_id IS NULL)
        OR (result = 'moved_out' AND new_lease_end IS NULL AND appointment_id IS NOT NULL)),
    CHECK (status = 'submitted' OR (reviewed_by IS NOT NULL AND review_note IS NOT NULL))
);
