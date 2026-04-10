import duckdb
import logging

DB_FILE = "data/budget.duckdb"

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
        conn.execute("CREATE SEQUENCE IF NOT EXISTS transactions_id_seq;")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id BIGINT PRIMARY KEY DEFAULT nextval('transactions_id_seq'),
            account_id BIGINT NOT NULL,
            date DATE NOT NULL,
            description TEXT NOT NULL,
            amount DOUBLE NOT NULL,
            balance DOUBLE,
            category TEXT,
            source TEXT DEFAULT 'manual',
            source_id TEXT,
            reconciliation_status TEXT DEFAULT 'pending',
            user_id BIGINT,
            merchant_id BIGINT,
            merchant_normalized TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(account_id, date, description, amount)
        );
        """)
        
        log_info("Transactions table ensured.")
        
        # Backfill existing transactions with default reconciliation values
        conn.execute("""
        UPDATE transactions 
        SET source = 'manual', reconciliation_status = 'matched' 
        WHERE source IS NULL OR reconciliation_status IS NULL;
        """)
        log_info("Transactions backfilled with reconciliation defaults.")

        # Category rules table
        conn.execute("CREATE SEQUENCE IF NOT EXISTS category_rules_id_seq;")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS category_rules (
            id INTEGER PRIMARY KEY DEFAULT nextval('category_rules_id_seq'),
            pattern VARCHAR NOT NULL,
            category VARCHAR NOT NULL,
            min_amount DOUBLE,
            max_amount DOUBLE
        );
        """)
        log_info("Category rules table ensured.")

        # Category budgets table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS category_budgets (
            category_name TEXT PRIMARY KEY,
            monthly_budget REAL,
            active BOOLEAN NOT NULL DEFAULT TRUE
        );
        """)
        log_info("Category budgets table ensured.")

        # Ingestion run tracking
        conn.execute("CREATE SEQUENCE IF NOT EXISTS ingestion_runs_id_seq;")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ingestion_runs (
            id BIGINT PRIMARY KEY DEFAULT nextval('ingestion_runs_id_seq'),
            filename VARCHAR NOT NULL,
            inserted_count INTEGER NOT NULL,
            skipped_count INTEGER NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        log_info("Ingestion runs table ensured.")

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

        #Recurring transactions table
        conn.execute("CREATE SEQUENCE IF NOT EXISTS recurring_events_id_seq;")

        conn.execute("""
        CREATE TABLE IF NOT EXISTS recurring_events (
        id BIGINT PRIMARY KEY,
        account_id BIGINT NOT NULL,

        name VARCHAR NOT NULL,
        amount DOUBLE NOT NULL,
        category VARCHAR,

        frequency VARCHAR NOT NULL,  -- 'monthly' | 'biweekly'

        day_of_month INTEGER,        -- monthly
        anchor_date DATE NOT NULL,   -- biweekly reference

        active BOOLEAN DEFAULT TRUE
        );
        """)
        log_info("Recurring transactions table ensured.")

        # Migration: add allow_consume to recurring_events
        try:
            conn.execute("ALTER TABLE recurring_events ADD COLUMN allow_consume BOOLEAN DEFAULT TRUE")
            log_info("Added allow_consume column to recurring_events.")
        except Exception:
            pass  # Column already exists

        # Migration: add recurring_event_id to transactions
        try:
            conn.execute("ALTER TABLE transactions ADD COLUMN recurring_event_id BIGINT")
            log_info("Added recurring_event_id column to transactions.")
        except Exception:
            pass  # Column already exists

        # AI category suggestions cache table
        conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_category_suggestions (
            merchant_normalized TEXT PRIMARY KEY,
            suggested_category TEXT NOT NULL,
            model TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        log_info("AI category suggestions table ensured.")
    
    except Exception as e:
            log_error(f"Error initializing DB: {e}")
    finally:
            conn.close()
            log_info("Database setup complete and connection closed.")