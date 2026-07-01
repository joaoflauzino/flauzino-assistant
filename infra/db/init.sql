CREATE TABLE IF NOT EXISTS spents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    item_bought VARCHAR NOT NULL,
    payment_method VARCHAR NOT NULL,
    location VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    installment_id UUID,
    current_installment INT,
    total_installments INT
);

CREATE INDEX IF NOT EXISTS ix_spents_category ON spents (category);
CREATE INDEX IF NOT EXISTS ix_spents_installment_id ON spents (installment_id);

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    payment_method VARCHAR NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_subscriptions_category ON subscriptions (category);
CREATE INDEX IF NOT EXISTS ix_subscriptions_is_active ON subscriptions (is_active);

CREATE TABLE IF NOT EXISTS spending_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR NOT NULL UNIQUE,
    amount DOUBLE PRECISION NOT NULL
);

-- Categories table for dynamic category management
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_categories_key ON categories (key);

-- Payment Methods table
CREATE TABLE IF NOT EXISTS payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    is_credit_card BOOLEAN DEFAULT false,
    closing_day INT,
    due_day INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_payment_methods_key ON payment_methods (key);



-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_method_key VARCHAR(50) NOT NULL,
    reference_month VARCHAR(7) NOT NULL,
    real_closing_date DATE NOT NULL,
    real_due_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_payment_method
        FOREIGN KEY(payment_method_key)
        REFERENCES payment_methods(key)
        ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_invoices_payment_method_month 
    ON invoices (payment_method_key, reference_month);

-- Seed payment_methods
INSERT INTO payment_methods (key, display_name, is_credit_card, closing_day, due_day) VALUES
    ('itau_joao', 'Itaú (João Lucas)', true, 2, 10),
    ('nubank_joao', 'Nubank (João Lucas)', true, 2, 10),
    ('nubank_lailla', 'Nubank (Lailla)', true, 2, 10),
    ('picpay_joao', 'PicPay (João Lucas)', true, 2, 10),
    ('c6_joao', 'C6 (João Lucas)', true, 2, 10),
    ('pix_joao', 'Pix (João Lucas)', false, null, null),
    ('pix_lailla', 'Pix (Lailla)', false, null, null)
ON CONFLICT (key) DO NOTHING;

-- Seed categories with existing category mappings
INSERT INTO categories (key, display_name) VALUES
    ('alimentacao', 'Alimentação'),
    ('comer_fora', 'Comer fora'),
    ('farmacia', 'Farmácia'),
    ('mercado', 'Mercado'),
    ('transporte', 'Transporte'),
    ('moradia', 'Moradia'),
    ('saude', 'Saúde'),
    ('lazer', 'Lazer'),
    ('educação', 'Educação'),
    ('compras', 'Compras'),
    ('vestuario', 'Vestuário'),
    ('viagem', 'Viagem'),
    ('servicos', 'Serviços'),
    ('criancas', 'Crianças'),
    ('outros', 'Outros')
ON CONFLICT (key) DO NOTHING;

CREATE TABLE IF NOT EXISTS chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT fk_session
        FOREIGN KEY(session_id)
        REFERENCES chat_sessions(id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id ON chat_messages (session_id);

CREATE TABLE IF NOT EXISTS telegram_sessions (
    chat_id BIGINT PRIMARY KEY,
    session_id UUID NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT now()
);