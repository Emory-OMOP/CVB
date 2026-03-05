"""Row-level and DataFrame validation wrapping cvb_constants rules."""

import sys
from pathlib import Path

import pandas as pd


def _get_constants():
    from lib.vocab_discovery import find_repo_root
    repo_root = find_repo_root()
    scripts_dir = str(repo_root / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import cvb_constants
    return cvb_constants


REJECTED_PREDICATES = {"relatedMatch", "skos:relatedMatch"}


def validate_row(row: dict, row_num: int) -> tuple[list[str], list[str]]:
    """Validate a single mapping row.

    Returns (errors, warnings) as lists of message strings.
    """
    constants = _get_constants()
    errors = []
    warnings = []

    # Predicate validation
    predicate = (row.get("predicate_id") or "").strip()

    if predicate in REJECTED_PREDICATES:
        errors.append(f"Row {row_num}: Rejected predicate '{predicate}' — relatedMatch is not supported")
        return errors, warnings

    normalized_pred = constants.PREDICATE_ALIASES.get(predicate, predicate)
    if normalized_pred and normalized_pred not in constants.VALID_PREDICATES:
        errors.append(f"Row {row_num}: Invalid predicate_id '{predicate}'")

    # Confidence check
    confidence_str = (row.get("confidence") or "").strip()
    if confidence_str:
        try:
            conf = float(confidence_str)
            if conf < 0 or conf > 1:
                errors.append(f"Row {row_num}: confidence={conf} out of range [0, 1]")
        except ValueError:
            errors.append(f"Row {row_num}: confidence '{confidence_str}' is not a valid number")

    # target_concept_id consistency
    target_str = (row.get("target_concept_id") or "").strip()
    if target_str:
        try:
            target_id = int(float(target_str))
            if normalized_pred == "noMatch" and target_id != 0:
                errors.append(f"Row {row_num}: noMatch requires target_concept_id=0, got {target_id}")
            elif normalized_pred != "noMatch" and normalized_pred in constants.VALID_PREDICATES and target_id == 0:
                warnings.append(f"Row {row_num}: target_concept_id=0 with predicate '{normalized_pred}'")
        except ValueError:
            errors.append(f"Row {row_num}: target_concept_id '{target_str}' is not a valid integer")

    # mapping_tool taxonomy
    tool = (row.get("mapping_tool") or "").strip()
    if tool and tool not in constants.VALID_MAPPING_TOOLS:
        warnings.append(
            f"Row {row_num}: mapping_tool '{tool}' not in OHDSI taxonomy"
        )

    return errors, warnings


def validate_dataframe(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    """Validate an entire DataFrame.

    Returns (errors, warnings) aggregated from all rows.
    Also checks for duplicate source_concept_codes.
    """
    constants = _get_constants()
    all_errors = []
    all_warnings = []

    # Check required columns
    header_set = set(df.columns)
    missing = constants.REQUIRED_MAPPING_COLUMNS - header_set
    if missing:
        all_errors.append(f"Missing required columns: {', '.join(sorted(missing))}")
        return all_errors, all_warnings

    # Row-by-row validation
    seen_codes = {}
    for i, (_, row) in enumerate(df.iterrows(), start=2):
        row_dict = row.to_dict()
        errs, warns = validate_row(row_dict, i)
        all_errors.extend(errs)
        all_warnings.extend(warns)

        # Duplicate check
        code = (row_dict.get("source_concept_code") or "").strip()
        if code:
            if code in seen_codes:
                all_warnings.append(
                    f"Row {i}: Duplicate source_concept_code '{code}' (first seen row {seen_codes[code]})"
                )
            else:
                seen_codes[code] = i

    return all_errors, all_warnings
