CREATE TABLE IF NOT EXISTS renewal_offer (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id integer NOT NULL REFERENCES follow_up_tasks(id),
    tenant_id integer NOT NULL REFERENCES tenants(id),
    lease_end date NOT NULL,
    budget_id integer NOT NULL REFERENCES retention_budget(id),
    ref text NOT NULL UNIQUE,
    term_months integer NOT NULL CHECK (term_months BETWEEN 2 AND 18),
    lease_start date NOT NULL,
    proposed_end date NOT NULL,
    list_cents bigint NOT NULL CHECK (list_cents>0),
    monthly_discount_cents bigint NOT NULL CHECK (monthly_discount_cents>=0 AND monthly_discount_cents<list_cents),
    total_discount_cents bigint GENERATED ALWAYS AS (monthly_discount_cents*term_months) STORED,
    valid_through date NOT NULL,
    rationale text NOT NULL,
    status text NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','issued','signed','declined','withdrawn')),
    created_by integer NOT NULL REFERENCES users(id),
    created_at timestamptz NOT NULL DEFAULT now(),
    issued_by integer REFERENCES users(id),
    acted_at timestamptz,
    closing_note text,
    CHECK (lease_start=lease_end+1 AND proposed_end>lease_start AND valid_through<=lease_end),
    CHECK (status NOT IN ('issued','signed','declined') OR issued_by IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS renewal_offer_active_lease ON renewal_offer(tenant_id,lease_end)
    WHERE status IN ('draft','issued','signed');
CREATE INDEX IF NOT EXISTS renewal_offer_budget_use ON renewal_offer(budget_id,status);
