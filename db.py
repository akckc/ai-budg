import duckdb
import logging

DB_FILE = "budget.duckdb"

def init_db():
    conn = duckdb.connect(DB_FILE)
    # --- Accounts table ---
    conn.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY,
        account_name VARCHAR NOT NULL UNIQUE,
        institution VARCHAR,
        account_type VARCHAR CHECK(account_type IN ('checking','savings','credit')),
        active BOOLEAN DEFAULT TRUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # --- Transactions table ---
    conn.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY,
        account_id INTEGER NOT NULL,
        date DATE NOT NULL,
        description VARCHAR NOT NULL,
        amount DECIMAL(10,2) NOT NULL,
        balance DECIMAL(10,2),
        category VARCHAR,
        source VARCHAR NOT NULL DEFAULT 'unknown',
        user_id INTEGER,
        merchant_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(account_id, date, description, amount),
        FOREIGN KEY(account_id) REFERENCES accounts(id)
    );
    """)
    # --- Category rules table ---
    conn.execute("""
    CREATE TABLE IF NOT EXISTS category_rules (
        id INTEGER PRIMARY KEY,
        pattern VARCHAR NOT NULL,
        category VARCHAR NOT NULL
    );
    """)
    # --- Indexes ---
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_account_date ON transactions(account_id, date);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);")
    conn.close()
    print("Database initialized successfully.")