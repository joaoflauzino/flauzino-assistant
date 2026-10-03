-- Categories table for dynamic category management
CREATE TABLE IF NOT EXISTS categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_categories_key ON categories (key);

-- Accounts table (Contas Bancárias, Carteiras e Investimentos)
CREATE TABLE IF NOT EXISTS accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    bank VARCHAR(50) NOT NULL DEFAULT 'outro',
    owner VARCHAR(50) NOT NULL DEFAULT 'joao',
    type VARCHAR(30) NOT NULL DEFAULT 'CHECKING',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_accounts_key ON accounts (key);

-- Credit Cards table (Cartões de Crédito vinculados a Contas)
CREATE TABLE IF NOT EXISTS credit_cards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(50) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    closing_day INT NOT NULL,
    due_day INT NOT NULL,
    credit_limit DOUBLE PRECISION DEFAULT 0.0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_credit_cards_key ON credit_cards (key);
CREATE INDEX IF NOT EXISTS ix_credit_cards_account_id ON credit_cards (account_id);

-- Legacy Payment Methods table (mantida para compatibilidade)
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

-- Spents table
CREATE TABLE IF NOT EXISTS spents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    item_bought VARCHAR NOT NULL,
    payment_method VARCHAR NOT NULL,
    location VARCHAR NOT NULL,
    payment_type VARCHAR(20) NOT NULL DEFAULT 'CREDIT',
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    credit_card_id UUID REFERENCES credit_cards(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    installment_id UUID,
    current_installment INT,
    total_installments INT
);

CREATE INDEX IF NOT EXISTS ix_spents_category ON spents (category);
CREATE INDEX IF NOT EXISTS ix_spents_installment_id ON spents (installment_id);
CREATE INDEX IF NOT EXISTS ix_spents_account_id ON spents (account_id);
CREATE INDEX IF NOT EXISTS ix_spents_credit_card_id ON spents (credit_card_id);

-- Subscriptions table
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    category VARCHAR NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    payment_method VARCHAR NOT NULL,
    payment_type VARCHAR(20) NOT NULL DEFAULT 'CREDIT',
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    credit_card_id UUID REFERENCES credit_cards(id) ON DELETE SET NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_subscriptions_category ON subscriptions (category);
CREATE INDEX IF NOT EXISTS ix_subscriptions_is_active ON subscriptions (is_active);

-- Spending Limits table
CREATE TABLE IF NOT EXISTS spending_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category VARCHAR NOT NULL UNIQUE,
    amount DOUBLE PRECISION NOT NULL
);

-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_method_key VARCHAR(50) NOT NULL,
    credit_card_id UUID REFERENCES credit_cards(id) ON DELETE CASCADE,
    reference_month VARCHAR(7) NOT NULL,
    real_closing_date DATE NOT NULL,
    real_due_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'OPEN',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_invoices_payment_method_month 
    ON invoices (payment_method_key, reference_month);

-- Tabela de Categorias de Receitas
CREATE TABLE IF NOT EXISTS income_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(50) NOT NULL UNIQUE,
    display_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_income_categories_key ON income_categories (key);

-- Tabela de Receitas
CREATE TABLE IF NOT EXISTS incomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    description VARCHAR NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    category VARCHAR(50) NOT NULL,
    payment_method VARCHAR(50),
    account_id UUID REFERENCES accounts(id) ON DELETE SET NULL,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_income_category
        FOREIGN KEY(category)
        REFERENCES income_categories(key)
        ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_incomes_category ON incomes (category);
CREATE INDEX IF NOT EXISTS ix_incomes_received_at ON incomes (received_at);
CREATE INDEX IF NOT EXISTS ix_incomes_account_id ON incomes (account_id);

-- Seeds para categories
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

-- Seeds para income_categories
INSERT INTO income_categories (key, display_name) VALUES
    ('salario', 'Salário'),
    ('pix', 'Pix Recebido'),
    ('premiacao', 'Premiação / Bônus'),
    ('investimentos', 'Rendimentos / Investimentos'),
    ('reembolso', 'Reembolso'),
    ('outros', 'Outros')
ON CONFLICT (key) DO NOTHING;

-- Seeds para accounts
INSERT INTO accounts (key, name, bank, owner, type) VALUES
    ('itau_joao', 'Itaú (João Lucas)', 'itau', 'joao', 'CHECKING'),
    ('nubank_joao', 'Nubank (João Lucas)', 'nubank', 'joao', 'CHECKING'),
    ('nubank_lailla', 'Nubank (Lailla)', 'nubank', 'lailla', 'CHECKING'),
    ('picpay_joao', 'PicPay (João Lucas)', 'picpay', 'joao', 'CHECKING'),
    ('c6_joao', 'C6 (João Lucas)', 'c6', 'joao', 'CHECKING')
ON CONFLICT (key) DO NOTHING;

-- Seeds para credit_cards vinculados às contas
INSERT INTO credit_cards (key, name, account_id, closing_day, due_day, credit_limit)
SELECT 'itau_card_joao', 'Itaú Mastercard Black', id, 2, 10, 15000.0 FROM accounts WHERE key = 'itau_joao'
ON CONFLICT (key) DO NOTHING;

INSERT INTO credit_cards (key, name, account_id, closing_day, due_day, credit_limit)
SELECT 'nubank_card_joao', 'Nubank Gold (João)', id, 2, 10, 10000.0 FROM accounts WHERE key = 'nubank_joao'
ON CONFLICT (key) DO NOTHING;

INSERT INTO credit_cards (key, name, account_id, closing_day, due_day, credit_limit)
SELECT 'nubank_card_lailla', 'Nubank Gold (Lailla)', id, 2, 10, 8000.0 FROM accounts WHERE key = 'nubank_lailla'
ON CONFLICT (key) DO NOTHING;

INSERT INTO credit_cards (key, name, account_id, closing_day, due_day, credit_limit)
SELECT 'picpay_card_joao', 'PicPay Card', id, 2, 10, 5000.0 FROM accounts WHERE key = 'picpay_joao'
ON CONFLICT (key) DO NOTHING;

INSERT INTO credit_cards (key, name, account_id, closing_day, due_day, credit_limit)
SELECT 'c6_card_joao', 'C6 Carbon Black', id, 2, 10, 12000.0 FROM accounts WHERE key = 'c6_joao'
ON CONFLICT (key) DO NOTHING;

-- Seed payment_methods (legado para compatibilidade retroativa)
INSERT INTO payment_methods (key, display_name, is_credit_card, closing_day, due_day) VALUES
    ('itau_joao', 'Itaú (João Lucas)', true, 2, 10),
    ('nubank_joao', 'Nubank (João Lucas)', true, 2, 10),
    ('nubank_lailla', 'Nubank (Lailla)', true, 2, 10),
    ('picpay_joao', 'PicPay (João Lucas)', true, 2, 10),
    ('c6_joao', 'C6 (João Lucas)', true, 2, 10),
    ('pix_joao', 'Pix (João Lucas)', false, null, null),
    ('pix_lailla', 'Pix (Lailla)', false, null, null)
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
