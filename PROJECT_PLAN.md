# ============================================
# Budget-AI — Canonical Project State
# Phase 2: Stabilization & Architecture
# ============================================

# --------------------------------------------
# Core Status
# --------------------------------------------

core = {
    "csv_ingestion": True,
    "deduplication": True,
    "dashboard_basic": True,
    "demo_ready": True,
}

# --------------------------------------------
# Architecture Hardening
# --------------------------------------------

architecture = {
    "routes_are_thin": False,
    "service_layer_extracted": False,
    "normalization_module_clean": False,
    "column_maps_configurable": False,
    "db_schema_reviewed": False,
    "error_handling_standardized": False,
}

# --------------------------------------------
# Multi-Account Support
# --------------------------------------------

multi_account = {
    "account_name_in_transactions": True,
    "dedupe_includes_account": True,
    "column_map_per_account": False,
    "account_table_created": False,
    "account_metadata_supported": False,
}

# --------------------------------------------
# Reconciliation System (Upgrade)
# --------------------------------------------

reconciliation = {
    "bank_statement_rename": False,
    "unmatched_detection_clean": False,
    "approve_flow_clean": False,
    "reconciliation_ui_polished": False,
}

# --------------------------------------------
# Dashboard Metrics (Production Grade)
# --------------------------------------------

dashboard_metrics = {
    "current_balance": True,
    "monthly_income": True,
    "monthly_expenses": True,
    "category_breakdown": True,
    "recurring_projection": False,
    "account_filtering": False,
}

# --------------------------------------------
# Recurring System
# --------------------------------------------

recurring = {
    "table_exists": False,
    "seed_data": False,
    "dashboard_display": False,
    "auto_projection_engine": False,
}

# --------------------------------------------
# Rules Engine Evolution
# --------------------------------------------

rules_engine = {
    "basic_rules_working": True,
    "account_specific_rules": False,
    "priority_ordering": False,
    "rule_testing_mode": False,
}

# --------------------------------------------
# Data Integrity & Safety
# --------------------------------------------

data_integrity = {
    "schema_constraints_enforced": False,
    "transactions_immutable": False,
    "audit_fields_added": False,   # created_at, updated_at
    "backup_strategy_defined": False,
}

# --------------------------------------------
# Phase 2 Primary Focus
# --------------------------------------------

current_focus = """
1. Extract proper service layer (routes thin, logic in services)
2. Clean normalization module with configurable column maps
3. Introduce account table for multi-account clarity
4. Standardize error handling in ingestion pipeline
5. Prepare recurring system foundation
"""

# --------------------------------------------
# Philosophy
# --------------------------------------------

notes = """
This is a personal, self-hosted budgeting backend.

Guiding principles:
- Keep it simple.
- No overengineering.
- Clean separation of concerns.
- Stability before new features.
- Design for multi-account future expansion.
"""