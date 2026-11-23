CREATE TABLE IF NOT EXISTS renewal_contract (
    offer_id integer PRIMARY KEY REFERENCES renewal_offer(id),
    contract_ref text NOT NULL UNIQUE,
    signed_on date NOT NULL,
    recorded_by integer NOT NULL REFERENCES users(id),
    recorded_at timestamptz NOT NULL DEFAULT now(),
    first_period_end date NOT NULL,
    first_expected_cents bigint NOT NULL CHECK (first_expected_cents>=0)
);
CREATE TABLE IF NOT EXISTS renewal_invoice_check (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    offer_id integer NOT NULL REFERENCES renewal_contract(offer_id),
    invoice_ref text NOT NULL UNIQUE,
    invoiced_cents bigint NOT NULL CHECK (invoiced_cents>=0),
    expected_cents bigint NOT NULL CHECK (expected_cents>=0),
    status text GENERATED ALWAYS AS (CASE WHEN invoiced_cents=expected_cents THEN 'matched' ELSE 'variance' END) STORED,
    note text NOT NULL,
    checked_by integer NOT NULL REFERENCES users(id),
    checked_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS renewal_invoice_one_match ON renewal_invoice_check(offer_id) WHERE status='matched';
