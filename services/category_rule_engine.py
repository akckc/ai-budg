"""
Category Rule Engine — Deterministic Rule-Based Category Assignment

Pure functions for evaluating transaction descriptions against a sorted rule set.
No database access; no side effects.
"""


def evaluate_category(description: str, rules: list) -> str | None:
    """
    Deterministically evaluate a transaction description against sorted rules.

    Args:
        description: Transaction description to match against rules.
        rules: List of rule dicts with 'pattern' and 'category' keys.
               MUST be explicitly sorted by priority BEFORE calling.

    Returns:
        Matched category (str) or None if no rule matches.

    Pure function: same inputs → same output, no side effects.
    """
    if not description or not rules:
        return None

    description_lower = description.lower()

    for rule in rules:
        pattern = rule.get("pattern", "").lower()
        if not pattern:
            continue

        # Simple substring match (case-insensitive)
        if pattern in description_lower:
            return rule.get("category")

    return None


def apply_rules_to_description(description: str, rules: list) -> str | None:
    """
    Alias for evaluate_category.
    
    Convenience function name for callers that prefer explicit wording.
    """
    return evaluate_category(description, rules)
