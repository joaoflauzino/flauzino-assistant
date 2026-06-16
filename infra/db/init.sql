CREATE TABLE IF NOT EXISTS spents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    item_bought VARCHAR NOT NULL,
    payment_method VARCHAR NOT NULL,
    payment_owner VARCHAR NOT NULL,
    location VARCHAR NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_spents_category ON spents (category);

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
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_payment_methods_key ON payment_methods (key);

-- Payment Owners table
CREATE TABLE IF NOT EXISTS payment_owners (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_payment_owners_key ON payment_owners (key);

-- Seed payment_methods
INSERT INTO payment_methods (key, display_name) VALUES
    ('itau', 'Itaú'),
    ('nubank', 'Nubank'),
    ('picpay', 'PicPay'),
    ('c6', 'C6')
ON CONFLICT (key) DO NOTHING;

-- Seed payment_owners
INSERT INTO payment_owners (key, display_name) VALUES
    ('joao_lucas', 'João Lucas'),
    ('lailla', 'Lailla')
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