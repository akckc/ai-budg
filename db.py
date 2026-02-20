import duckdb

DB_PATH = "data/budget-dev.db"

def get_db():
    return duckdb.connect(DB_PATH)

def init_db():
    conn = get_db()
    
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS transactions_id_seq
        START 1
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY DEFAULT nextval('transactions_id_seq'),

            date DATE NOT NULL,
            description VARCHAR NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            balance DECIMAL(10,2),
            category VARCHAR,

            source VARCHAR NOT NULL DEFAULT 'unknown',

            account_id INTEGER NULL,
            user_id INTEGER NULL,
            merchant_id INTEGER NULL,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS category_rules_id_seq START 1;
    """)
    conn.execute("""    
        CREATE TABLE IF NOT EXISTS category_rules (
            id INTEGER PRIMARY KEY DEFAULT nextval('category_rules_id_seq'),
            pattern VARCHAR NOT NULL,
            min_amount DECIMAL(10,2),
            max_amount DECIMAL(10,2),
            category VARCHAR NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.close()