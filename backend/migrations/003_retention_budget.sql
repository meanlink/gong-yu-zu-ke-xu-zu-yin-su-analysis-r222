CREATE TABLE IF NOT EXISTS retention_budget (
    id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    neighborhood text NOT NULL,
    starts_month date NOT NULL CHECK (extract(day from starts_month)=1),
    cap_cents bigint NOT NULL CHECK (cap_cents>=0),
    justification text NOT NULL,
    configured_by integer NOT NULL REFERENCES users(id),
    UNIQUE (neighborhood,starts_month)
);
