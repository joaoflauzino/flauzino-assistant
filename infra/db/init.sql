CREATE TABLE IF NOT EXISTS spents (
    id SERIAL PRIMARY KEY,
    category VARCHAR NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    payment_method VARCHAR,
    payment_owner VARCHAR,
    location VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_spents_category ON spents (category);

CREATE TABLE IF NOT EXISTS spending_limits (
    id SERIAL PRIMARY KEY,
    category VARCHAR NOT NULL UNIQUE,
    amount DOUBLE PRECISION NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_spending_limits_category ON spending_limits (category);
