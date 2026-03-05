"""Load and save mapping CSV files with workspace column preservation."""

import os
import sys
import tempfile
from pathlib import Path

import pandas as pd

# Add scripts/ to path so we can import cvb_constants
_repo_root = None


def _get_repo_root() -> Path:
    from lib.vocab_discovery import find_repo_root
    global _repo_root
    if _repo_root is None:
        _repo_root = find_repo_root()
    return _repo_root


def _get_constants():
    repo_root = _get_repo_root()
    scripts_dir = str(repo_root / "scripts")
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    import cvb_constants
    return cvb_constants


def load_mapping_csv(filepath: Path) -> pd.DataFrame:
    """Load a mapping CSV, normalizing column names.

    Reads all columns as strings with empty string defaults (no NaN).
    """
    constants = _get_constants()

    df = pd.read_csv(filepath, dtype=str, keep_default_na=False)

    # Normalize column names
    df.columns = [constants.normalize_column_name(c) for c in df.columns]

    return df


def save_mapping_csv(df: pd.DataFrame, filepath: Path) -> None:
    """Save DataFrame to CSV atomically.

    Column order: EXPECTED_COLUMNS order → ws_* columns → any extras.
    Uses atomic write (tmpfile + rename) to prevent data loss.
    """
    constants = _get_constants()

    # Determine column order
    expected = constants.EXPECTED_COLUMNS
    ws_cols = sorted(c for c in df.columns if c.startswith("ws_"))
    other_cols = [
        c for c in df.columns
        if c not in expected and c not in ws_cols
    ]

    ordered = [c for c in expected if c in df.columns]
    ordered += [c for c in ws_cols if c not in ordered]
    ordered += [c for c in other_cols if c not in ordered]

    df_out = df[ordered]

    # Atomic write: write to tmpfile in same directory, then rename
    dirpath = filepath.parent
    fd, tmp_path = tempfile.mkstemp(suffix=".csv", dir=dirpath)
    try:
        os.close(fd)
        df_out.to_csv(tmp_path, index=False)
        os.replace(tmp_path, filepath)
    except Exception:
        # Clean up temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
