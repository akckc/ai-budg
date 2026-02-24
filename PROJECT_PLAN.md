============================================
Budget-AI — Project Plan (Post Sprint 2)
Phase 2: Platform Stabilization → Intelligence
============================================

PHASE_1_COMPLETE = True # Structural refactor + service layer separation
PHASE_2_FOUNDATION_COMPLETE = True # Multi-account + ingestion hardening

------------------------------------------------
Phase 2 Summary (Completed Work)
------------------------------------------------

PHASE_2_COMPLETED = {
"multi_account_support": True,
"accounts_table_introduced": True,
"transactions_use_account_id": True,
"default_account_bootstrap": True,
"idempotent_csv_ingestion": True,
"unique_constraint_enforced": True,
"repository_layer_centralized": True,
"duckdb_sequence_primary_keys": True,
"persistent_container_storage": True,
}

Current Platform Status:
- Deterministic deduplication
- Multi-account ready
- Clean repository architecture
- Container-persistent database
- Low schema risk moving forward
------------------------------------------------
Phase 2 Remaining Focus (Intelligence Layer)
------------------------------------------------

PHASE_2_NEXT = {
"category_automation_engine": {
"priority_rules": True,
"automatic_assignment_on_ingest": True,
"reclassification_endpoint": True,
"deterministic_first_match_wins": True,
}
}

------------------------------------------------
Upcoming Sprints
------------------------------------------------

SPRINT_3 = "Category Automation Engine"
SPRINT_4 = "Ingestion Transparency + Dashboard Filtering"
SPRINT_5 = "Recurring Transactions Engine (Projection System)"
SPRINT_6 = "Merchant Normalization Layer"

------------------------------------------------
Architectural Principles (Locked In)
------------------------------------------------

ARCHITECTURE = {
"thin_routes": True,
"service_layer_business_logic": True,
"repository_layer_db_access_only": True,
"schema_constraints_enforced": True,
"idempotent_ingestion_required": True,
"multi_account_first_class": True,
}

------------------------------------------------
Risk Profile
------------------------------------------------

RISK_LEVEL = "LOW"

Infrastructure is stable.
Safe to accelerate user-visible feature development.
============================================