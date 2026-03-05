"""Classify template names into clinical categories.

Uses deterministic regex patterns from constants.py.

Usage:
    from fca.template_classifier import classify_template
    cat = classify_template("IP OB POSTPARTUM")
    # 'ob_labor_delivery'
"""

from __future__ import annotations

from .constants import TEMPLATE_CATEGORY_PATTERNS


def classify_template(template_name: str) -> str:
    """Classify a TEMPLATE_NAME into a clinical category.

    Returns the category string, or 'uncategorized' if no pattern matches.
    """
    if not template_name or not isinstance(template_name, str):
        return 'uncategorized'

    template_name = template_name.strip()

    for pattern, category in TEMPLATE_CATEGORY_PATTERNS:
        if pattern.search(template_name):
            return category

    return 'uncategorized'


def classify_batch(names: list[str]) -> list[str]:
    """Classify a batch of template names. Returns list in same order."""
    return [classify_template(n) for n in names]
