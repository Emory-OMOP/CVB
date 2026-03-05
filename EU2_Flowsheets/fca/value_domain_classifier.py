"""Classify custom list value sets into value domain types.

Analyzes the set of possible values for a flowsheet item's custom list
and classifies them into a value domain type (ordinal_severity,
present_absent, ordinal_quality, etc.).

Usage:
    from fca.value_domain_classifier import classify_value_domain
    domain = classify_value_domain(["None", "Trace", "1+", "2+", "3+", "4+"])
    # 'ordinal_severity'
"""

from __future__ import annotations

from .constants import VALUE_DOMAIN_PATTERNS, VALUE_DOMAIN_MIN_MATCH_RATIO


def classify_value_domain(values: list[str]) -> str:
    """Classify a set of custom list values into a value domain type.

    Args:
        values: List of string values from IP_FLO_CUSTOM_LIST.

    Returns:
        Value domain type string, or 'unclassified' if no pattern matches
        at least VALUE_DOMAIN_MIN_MATCH_RATIO of the values.
    """
    if not values:
        return 'unclassified'

    n_values = len(values)
    best_domain = 'unclassified'
    best_ratio = 0.0

    for domain, patterns in VALUE_DOMAIN_PATTERNS.items():
        matched = 0
        for v in values:
            if not v or not isinstance(v, str):
                continue
            for pat in patterns:
                if pat.search(v):
                    matched += 1
                    break

        ratio = matched / n_values if n_values > 0 else 0.0
        if ratio >= VALUE_DOMAIN_MIN_MATCH_RATIO and ratio > best_ratio:
            best_ratio = ratio
            best_domain = domain

    return best_domain


def classify_custom_lists(
    custom_lists: dict[str, list[str]],
) -> dict[str, str]:
    """Classify value domains for multiple flowsheet items.

    Args:
        custom_lists: Dict mapping FLO_MEAS_ID → list of custom list values.

    Returns:
        Dict mapping FLO_MEAS_ID → value domain type.
    """
    return {
        flo_id: classify_value_domain(values)
        for flo_id, values in custom_lists.items()
    }
