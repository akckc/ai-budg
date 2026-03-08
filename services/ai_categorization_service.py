import os
import requests
from db import get_db
from repositories.ai_category_repository import (
    list_uncategorized_merchants,
    get_cached_suggestion,
    upsert_suggestion,
    apply_suggestion_to_uncategorized,
)

# Environment configuration with defaults
AI_ENABLED = os.getenv("AI_ENABLED", "false").lower() in ("true", "1", "yes")
AI_OLLAMA_BASE_URL = os.getenv("AI_OLLAMA_BASE_URL", "http://localhost:11434")
AI_MODEL = os.getenv("AI_MODEL", "qwen2.5:14b")
AI_TIMEOUT_SECONDS = int(os.getenv("AI_TIMEOUT_SECONDS", "10"))
AI_MAX_MERCHANTS_PER_RUN = int(os.getenv("AI_MAX_MERCHANTS_PER_RUN", "10"))
AI_NUM_PREDICT = int(os.getenv("AI_NUM_PREDICT", "30"))

# Fixed allowed categories (Sprint 12 v1)
ALLOWED_CATEGORIES = {
    "Mortgage",
    "Home Improvement",
    "Car Payment",
    "Gas",
    "Car Repairs/Maintenance",
    "Groceries",
    "Restaurant",
    "Pet Care",
    "Utilities",
    "Clothing",
    "Life Insurance",
    "Car Insurance",
    "Health/Fitness",
    "Student Loans",
    "Credit Cards",
    "Subscriptions",
    "Income",
    "Transfer",
    "Uncategorized",
}


def run_ai_reclassify_uncategorized(max_merchants: int = None) -> dict:
    """
    Orchestrate AI categorization job.
    Deterministic, no side effects on error.
    Returns dict with success, error, merchants_processed, transactions_updated,
    cache_hits, ai_calls, failures list.
    """
    if not AI_ENABLED:
        return {
            "success": False,
            "error": "AI categorization is disabled (AI_ENABLED=false)",
            "merchants_processed": 0,
            "transactions_updated": 0,
            "cache_hits": 0,
            "ai_calls": 0,
            "failures": [],
        }

    conn = get_db()
    try:
        limit = min(max_merchants or AI_MAX_MERCHANTS_PER_RUN, AI_MAX_MERCHANTS_PER_RUN)
        merchants = list_uncategorized_merchants(conn, limit=limit)

        if not merchants:
            return {
                "success": True,
                "error": None,
                "merchants_processed": 0,
                "transactions_updated": 0,
                "cache_hits": 0,
                "ai_calls": 0,
                "failures": [],
            }

        merchants_processed = 0
        transactions_updated = 0
        cache_hits = 0
        ai_calls = 0
        failures = []

        for merchant in merchants:
            try:
                # Check for credit card payment rule (deterministic override)
                if _is_credit_card_payment(merchant):
                    category = "Transfer"
                    upsert_suggestion(conn, merchant, category, "rule:credit_card_payment")
                    rows_updated = apply_suggestion_to_uncategorized(conn, merchant, category)
                    transactions_updated += rows_updated
                    merchants_processed += 1
                    cache_hits += 1  # rule is effectively a cache hit
                    continue

                # Check cache
                cached = get_cached_suggestion(conn, merchant)
                if cached:
                    rows_updated = apply_suggestion_to_uncategorized(conn, merchant, cached)
                    transactions_updated += rows_updated
                    merchants_processed += 1
                    cache_hits += 1
                    continue

                # Call Ollama AI
                suggested_category = _call_ollama(merchant)
                if suggested_category:
                    upsert_suggestion(conn, merchant, suggested_category, AI_MODEL)
                    rows_updated = apply_suggestion_to_uncategorized(conn, merchant, suggested_category)
                    transactions_updated += rows_updated
                    merchants_processed += 1
                    ai_calls += 1
                else:
                    failures.append({
                        "merchant": merchant,
                        "reason": "AI returned invalid/no category",
                    })
                    merchants_processed += 1
                    ai_calls += 1

            except Exception as e:
                failures.append({
                    "merchant": merchant,
                    "reason": str(e),
                })
                merchants_processed += 1

        return {
            "success": True,
            "error": None,
            "merchants_processed": merchants_processed,
            "transactions_updated": transactions_updated,
            "cache_hits": cache_hits,
            "ai_calls": ai_calls,
            "failures": failures,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "merchants_processed": 0,
            "transactions_updated": 0,
            "cache_hits": 0,
            "ai_calls": 0,
            "failures": [],
        }
    finally:
        conn.close()


def _call_ollama(merchant_normalized: str) -> str | None:
    """
    Call Ollama /api/generate with temp=0, num_predict=30, timeout=10s.
    Return validated category or None.
    Fail-open: returns None on error.
    """
    try:
        url = f"{AI_OLLAMA_BASE_URL}/api/generate"
        prompt = f"""Categorize this merchant into ONE category from this list:
Mortgage, Home Improvement, Car Payment, Gas, Car Repairs/Maintenance, Groceries, Restaurant, Pet Care, Utilities, Clothing, Life Insurance, Car Insurance, Health/Fitness, Student Loans, Credit Cards, Subscriptions, Income, Transfer, Uncategorized

Merchant: {merchant_normalized}

Return ONLY the category name, nothing else."""

        payload = {
            "model": AI_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0,
                "num_predict": AI_NUM_PREDICT,
            },
        }

        response = requests.post(url, json=payload, timeout=AI_TIMEOUT_SECONDS)
        if response.status_code != 200:
            return None

        data = response.json()
        suggested = data.get("response", "").strip()

        # Validate against allowed categories (case-insensitive match)
        for allowed in ALLOWED_CATEGORIES:
            if suggested.lower() == allowed.lower():
                return allowed

        # Fallback to Uncategorized if AI response is not in allowed set
        return "Uncategorized"

    except Exception:
        # Fail-open: return None on any error
        return None


def _is_credit_card_payment(merchant_normalized: str) -> bool:
    """
    Check if merchant matches credit card payment keywords.
    Return True to force Transfer category.
    Deterministic rule.
    """
    merchant_lower = merchant_normalized.lower()
    keywords = ["chase", "autopay", "payment"]
    return any(kw in merchant_lower for kw in keywords)
