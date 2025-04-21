CREATE TABLE alunos (
    id BIGINT PRIMARY KEY,
    cv TEXT NOT NULL,
    nome TEXT,
    curso TEXT,
    unidade TEXT,
    rg TEXT,
    data_expedicao DATE,
    data_nascimento DATE
);

CREATE TABLE blockchain (
    id SERIAL PRIMARY KEY,
    block_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pending_transactions (
    id SERIAL PRIMARY KEY,
    transaction_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
