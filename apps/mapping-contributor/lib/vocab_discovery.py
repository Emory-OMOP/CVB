"""Discover CVB vocab directories and their mapping CSV files."""

import os
from pathlib import Path


def find_repo_root() -> Path:
    """Find the CVB repo root by walking up from this file or using env var."""
    env_root = os.environ.get("CVB_REPO_ROOT")
    if env_root:
        return Path(env_root)

    # Walk up from apps/mapping-contributor/lib/ → repo root
    current = Path(__file__).resolve().parent
    for _ in range(10):
        if (current / "scripts" / "cvb_constants.py").is_file():
            return current
        current = current.parent

    raise FileNotFoundError(
        "Cannot find CVB repo root. Set CVB_REPO_ROOT env var or run from within the repo."
    )


def discover_vocabs(repo_root: Path) -> list[dict]:
    """Discover vocab directories with Mappings/ subdirs.

    Returns list of dicts: {"name": str, "path": Path, "mappings_dir": Path}
    """
    vocabs = []
    for entry in sorted(os.listdir(repo_root)):
        if entry.startswith(("_", ".")):
            continue
        mappings_dir = repo_root / entry / "Mappings"
        if mappings_dir.is_dir():
            vocabs.append({
                "name": entry,
                "path": repo_root / entry,
                "mappings_dir": mappings_dir,
            })
    return vocabs


def discover_mapping_files(mappings_dir: Path) -> list[Path]:
    """List CSV files in a Mappings/ directory."""
    return sorted(
        p for p in mappings_dir.iterdir()
        if p.suffix.lower() == ".csv" and p.is_file()
    )


def load_vocab_env(vocab_dir: Path) -> dict:
    """Parse a vocab.env file into a dict."""
    env_file = vocab_dir / "vocab.env"
    env = {}
    if env_file.is_file():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                env[key.strip()] = val.strip().strip('"').strip("'")
    return env
