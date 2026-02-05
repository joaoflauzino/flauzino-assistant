CREATE TABLE IF NOT EXISTS spents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
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
    ('xp', 'XP'),
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
    ('comer_fora', 'Comer Fora'),
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
    ('serviços', 'Serviços'),
    ('crianças', 'Crianças'),
    ('outros', 'Outros')
ON CONFLICT (key) DO NOTHING;

-- Seed spending limits
INSERT INTO spending_limits (category, amount) VALUES
    ('mercado', 2000.00),
    ('comer_fora', 800.00),
    ('transporte', 500.00),
    ('lazer', 400.00),
    ('farmacia', 300.00),
    ('vestuario', 600.00),
    ('moradia', 1500.00),
    ('saude', 500.00),
    ('educação', 1000.00),
    ('serviços', 300.00),
    ('viagem', 2000.00),
    ('compras', 1000.00),
    ('outros', 200.00)
ON CONFLICT (category) DO NOTHING;

-- Seed spents
INSERT INTO spents (category, amount, payment_method, payment_owner, location) VALUES
    ('mercado', 350.50, 'itau', 'joao_lucas', 'Supermercado ABC'),
    ('mercado', 125.80, 'nubank', 'lailla', 'Hortifruti'),
    ('comer_fora', 85.00, 'nubank', 'joao_lucas', 'Restaurante XYZ'),
    ('comer_fora', 45.90, 'itau', 'lailla', 'Cafeteria'),
    ('transporte', 22.50, 'picpay', 'joao_lucas', 'Uber'),
    ('transporte', 15.00, 'picpay', 'joao_lucas', 'Metrô'),
    ('lazer', 120.00, 'itau', 'joao_lucas', 'Cinema'),
    ('farmacia', 85.50, 'itau', 'lailla', 'Farmácia Pague Menos'),
    ('vestuario', 159.90, 'itau', 'joao_lucas', 'Loja de Roupas'),
    ('moradia', 1200.00, 'picpay', 'joao_lucas', 'Aluguel'),
    ('moradia', 150.00, 'nubank', 'lailla', 'Condomínio'),
    ('saude', 350.00, 'itau', 'joao_lucas', 'Plano de Saúde'),
    ('saude', 120.00, 'nubank', 'lailla', 'Consulta Médica'),
    ('educação', 800.00, 'picpay', 'joao_lucas', 'Curso de Inglês'),
    ('serviços', 100.00, 'itau', 'lailla', 'Netflix/Spotify'),
    ('viagem', 450.00, 'itau', 'joao_lucas', 'Passagem Aérea'),
    ('viagem', 1200.00, 'itau', 'lailla', 'Hotel'),
    ('mercado', 400.00, 'itau', 'joao_lucas', 'Feira Mensal'),
    ('mercado', 89.90, 'nubank', 'lailla', 'Padaria'),
    ('comer_fora', 120.00, 'itau', 'joao_lucas', 'Jantar Japonês'),
    ('comer_fora', 35.00, 'nubank', 'lailla', 'Sorveteria'),
    ('transporte', 45.00, 'picpay', 'joao_lucas', 'Gasolina'),
    ('transporte', 18.90, 'nubank', 'lailla', 'Uber'),
    ('lazer', 250.00, 'itau', 'joao_lucas', 'Show'),
    ('lazer', 60.00, 'nubank', 'lailla', 'Livros'),
    ('farmacia', 45.00, 'itau', 'joao_lucas', 'Vitaminas'),
    ('vestuario', 200.00, 'itau', 'lailla', 'Tênis'),
    ('compras', 150.00, 'itau', 'joao_lucas', 'Presente Aniversário'),
    ('outros', 50.00, 'picpay', 'joao_lucas', 'Manutenção Casa');

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
