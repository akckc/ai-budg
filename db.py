import duckdb
import os
import logging
from datetime import datetime

# -----------------------------
# Setup Logging
# -----------------------------
LOG_FILE = "db_setup.log"
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def log_info(message):
    logging.info(message)
    print(message)

def log_error(message):
    logging.error(message)
    print(message)

# -----------------------------
# Database Connection
# -----------------------------
DB_FILE = "budget.duckdb"
conn = duckdb.connect(DB_FILE)
log_info(f"Connected to database: {DB_FILE}")

# -----------------------------
# Accounts Table
# -----------------------------
try:
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
except Exception as e:
    log_error(f"Error creating accounts table: {e}")

# -----------------------------
# Transactions Table
# -----------------------------
try:
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
    log_info("Transactions table ensured.")
except Exception as e:
    log_error(f"Error creating transactions table: {e}")

# -----------------------------
# Category Rules Table
# -----------------------------
try:
    conn.execute("""
    CREATE TABLE IF NOT EXISTS category_rules (
        id INTEGER PRIMARY KEY,
        pattern VARCHAR NOT NULL,
        category VARCHAR NOT NULL
    );
    """)
    log_info("Category rules table ensured.")
except Exception as e:
    log_error(f"Error creating category_rules table: {e}")

# -----------------------------
# Indexes
# -----------------------------
try:
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_account_date ON transactions(account_id, date);")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions(category);")
    log_info("Indexes created/ensured.")
except Exception as e:
    log_error(f"Error creating indexes: {e}")

# -----------------------------
# Default Account
# -----------------------------
try:
    conn.execute("""
    INSERT INTO accounts (id, account_name, institution, account_type)
    SELECT 1, 'Primary Account', 'Unknown', 'checking'
    WHERE NOT EXISTS (SELECT 1 FROM accounts WHERE id = 1);
    """)
    log_info("Default account ensured.")
except Exception as e:
    log_error(f"Error inserting default account: {e}")

# -----------------------------
# Close Connection
# -----------------------------
conn.close()
log_info("Database setup complete and connection closed.")