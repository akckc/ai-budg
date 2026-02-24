import duckdb
import logging

DB_FILE = "budget.duckdb"

# -----------------------------
# Logging
# -----------------------------
logging.basicConfig(
    filename="db_setup.log",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log_info(msg):
    logging.info(msg)
    print(msg)

def log_error(msg):
    logging.error(msg)
    print(msg)

# -----------------------------
# Get a DB connection
# -----------------------------
def get_db():
    """
    Returns a new DuckDB connection.
    """
    return duckdb.connect(DB_FILE)

# -----------------------------
# Initialize database schema
# -----------------------------
def init_db():
    conn = get_db()
    try:
        # Accounts table
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
        log_info("Accounts table ensured.")

        # Transactions table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
            account_id BIGINT NOT NULL,
            date DATE NOT NULL,
            description TEXT NOT NULL,
            amount DOUBLE NOT NULL,
            balance DOUBLE,
            category TEXT,
            source TEXT,
            user_id BIGINT,
            merchant_id BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(account_id, date, description, amount)
        );
        """)
        log_info("Transactions table ensured.")

        # Category rules table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS category_rules (
            id INTEGER PRIMARY KEY,
            pattern VARCHAR NOT NULL,
            category VARCHAR NOT NULL
        );
        """)
        log_info("Category rules table ensured.")

        # Indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_account_date ON transactions(account_id, date);")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);")
        log_info("Indexes created/ensured.")

        # Default Primary Account
        conn.execute("""
        INSERT INTO accounts (id, account_name, institution, account_type)
        SELECT 1, 'Primary Account', 'Unknown', 'checking'
        WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE id = 1);
        """)
        log_info("Default primary account ensured.")

    except Exception as e:
        log_error(f"Error initializing DB: {e}")
    finally:
        conn.close()
        log_info("Database setup complete and connection closed.")