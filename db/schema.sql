-- existing schema above

CREATE TABLE IF NOT EXISTS category_budgets (
    category_name TEXT PRIMARY KEY,
    monthly_budget REAL,
    active BOOLEAN NOT NULL DEFAULT TRUE
);
