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
INSERT INTO spents (category, amount, item_bought, payment_method, payment_owner, location) VALUES
    ('mercado', 350.50, 'compras do mês', 'itau', 'joao_lucas', 'supermercado abc'),
    ('mercado', 125.80, 'frutas e verduras', 'nubank', 'lailla', 'hortifruti'),
    ('comer_fora', 85.00, 'jantar a dois', 'nubank', 'joao_lucas', 'restaurante xyz'),
    ('comer_fora', 45.90, 'café e bolo', 'itau', 'lailla', 'cafeteria'),
    ('transporte', 22.50, 'corrida para o trabalho', 'picpay', 'joao_lucas', 'uber'),
    ('transporte', 15.00, 'passagem de metrô', 'picpay', 'joao_lucas', 'metrô'),
    ('lazer', 120.00, 'ingressos para o cinema', 'itau', 'joao_lucas', 'cinema'),
    ('farmacia', 85.50, 'remédios e produtos de higiene', 'itau', 'lailla', 'farmácia pague menos'),
    ('vestuario', 159.90, 'calça jeans e camiseta', 'itau', 'joao_lucas', 'loja de roupas'),
    ('moradia', 1200.00, 'aluguel do apartamento', 'picpay', 'joao_lucas', 'aluguel'),
    ('moradia', 150.00, 'taxa de condomínio', 'nubank', 'lailla', 'condomínio'),
    ('saude', 350.00, 'mensalidade do plano de saúde', 'itau', 'joao_lucas', 'plano de saúde'),
    ('saude', 120.00, 'consulta com especialista', 'nubank', 'lailla', 'consulta médica'),
    ('educação', 800.00, 'mensalidade do curso de inglês', 'picpay', 'joao_lucas', 'curso de inglês'),
    ('serviços', 100.00, 'assinaturas de streaming', 'itau', 'lailla', 'netflix/spotify'),
    ('viagem', 450.00, 'passagem de avião para o feriado', 'itau', 'joao_lucas', 'passagem aérea'),
    ('viagem', 1200.00, 'hospedagem em hotel', 'itau', 'lailla', 'hotel'),
    ('mercado', 400.00, 'compras para o churrasco', 'itau', 'joao_lucas', 'feira mensal'),
    ('mercado', 89.90, 'pães e frios', 'nubank', 'lailla', 'padaria'),
    ('comer_fora', 120.00, 'rodízio de comida japonesa', 'itau', 'joao_lucas', 'jantar japonês'),
    ('comer_fora', 35.00, 'casquinha de sorvete', 'nubank', 'lailla', 'sorveteria'),
    ('transporte', 45.00, 'abastecimento do carro', 'picpay', 'joao_lucas', 'gasolina'),
    ('transporte', 18.90, 'corrida para o shopping', 'nubank', 'lailla', 'uber'),
    ('lazer', 250.00, 'ingresso para show', 'itau', 'joao_lucas', 'show'),
    ('lazer', 60.00, 'compra de livros', 'nubank', 'lailla', 'livros'),
    ('farmacia', 45.00, 'suplementos vitamínicos', 'itau', 'joao_lucas', 'vitaminas'),
    ('vestuario', 200.00, 'tênis de corrida', 'itau', 'lailla', 'tênis'),
    ('compras', 150.00, 'presente de aniversário', 'itau', 'joao_lucas', 'presente aniversário'),
    ('outros', 50.00, 'pequenos reparos em casa', 'picpay', 'joao_lucas', 'manutenção casa');

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
