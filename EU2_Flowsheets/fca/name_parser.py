"""Parse DISP_NAME into structured clinical attributes.

Deterministic regex + dictionary extraction for reproducibility.
No ML or probabilistic models — same input always yields same output.

Usage:
    from fca.name_parser import parse_display_name
    attrs = parse_display_name("RLE Edema")
    # {'laterality': 'right', 'body_site': 'lower_extremity',
    #  'assessment': 'edema'}
"""

from __future__ import annotations

from .constants import (
    ASSESSMENT_PATTERNS,
    BODY_SITE_PATTERNS,
    LATERALITY_PATTERNS,
)


def parse_display_name(name: str) -> dict[str, str | None]:
    """Extract clinical attributes from a flowsheet DISP_NAME.

    Returns dict with keys: laterality, body_region, body_site, assessment.
    Values are None when not detected.
    """
    if not name or not isinstance(name, str):
        return {
            'laterality': None,
            'body_region': None,
            'body_site': None,
            'assessment': None,
        }

    name = name.strip()

    laterality = None
    body_region_from_lat = None
    body_site = None
    assessment = None

    # Extract laterality (first match wins)
    for pattern, match in LATERALITY_PATTERNS:
        if pattern.search(name):
            laterality = match.laterality
            body_region_from_lat = match.body_region
            break

    # Extract body site (first match wins)
    for pattern, site in BODY_SITE_PATTERNS:
        if pattern.search(name):
            body_site = site
            break

    # If body site not found from name but laterality implied one, use that
    if body_site is None and body_region_from_lat is not None:
        body_site = body_region_from_lat

    # Extract assessment type (first match wins)
    for pattern, atype in ASSESSMENT_PATTERNS:
        if pattern.search(name):
            assessment = atype
            break

    return {
        'laterality': laterality,
        'body_region': body_region_from_lat,
        'body_site': body_site,
        'assessment': assessment,
    }


def parse_batch(names: list[str]) -> list[dict[str, str | None]]:
    """Parse a batch of display names. Returns list in same order."""
    return [parse_display_name(n) for n in names]
