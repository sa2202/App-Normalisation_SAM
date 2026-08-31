"""
bulk_import.py
Grow the canonical library from an ITAM/discovery tool export (Flexera FlexNet
Manager Suite, Snow Atlas, ServiceNow SAM, etc.) instead of typing entries by hand.

These tools already do their own software recognition (Flexera's Application
Recognition Library, for example) - so their exports are normalized,
vendor-verified data: real Publisher / Product / Edition / Version, not messy
raw strings. That makes them a genuinely better seed for the canonical library
than hand-researched entries.

Design choices:
  - Column-mapping driven, not hardcoded column names - every ITAM tool's export
    schema is admin-configurable, so we ask the user which column is which
    (same pattern as the main app's product-name column mapping).
  - Dedup against what's already in the library AND within the import itself,
    by normalized (publisher, product_family, edition, version) - so re-running
    an import (e.g. a monthly Flexera refresh) doesn't create duplicate rows.
  - Never silently overwrites existing canonical_ids - only ADDS genuinely new
    products. If you need to correct an existing entry, do that by hand in
    canonical_library.csv or via the app's review/confirm step.
  - Always returns a preview before anything is written - bulk-adding hundreds
    of rows sight-unseen is exactly the kind of silent-trust failure this whole
    tool exists to avoid.
"""

import re
import pandas as pd


def _safe_str(value) -> str:
    """Convert a cell value to a clean string, treating pandas NaN/None as
    genuinely blank instead of the literal text 'nan' (a real, easy-to-miss
    bug when a column has empty cells - str(float('nan')) == 'nan')."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _slug(text: str) -> str:
    """Turn free text into an UPPER-SNAKE-ish token for building canonical_ids."""
    if not isinstance(text, str) or not text.strip():
        return ""
    text = re.sub(r"[^A-Za-z0-9]+", "-", text.strip())
    return text.strip("-").upper()


def _normalize_key(publisher, family, edition, version) -> str:
    """Dedup key: normalized publisher+family+edition+version, order/case-insensitive."""
    parts = [_safe_str(x).lower() for x in (publisher, family, edition, version) if _safe_str(x)]
    return "|".join(parts)


def preview_import(raw_df: pd.DataFrame, existing_lib: pd.DataFrame, col_map: dict) -> dict:
    """
    col_map keys (values are column names in raw_df, or None if not available):
      publisher, product, edition, version, metric

    Returns dict with:
      new_rows       - DataFrame of rows that would be ADDED (canonical_library.csv shape)
      duplicate_count - how many import rows matched something already in the library
      blank_count     - how many import rows were missing publisher or product and were skipped
    """
    existing_keys = set()
    for _, row in existing_lib.iterrows():
        existing_keys.add(_normalize_key(row["publisher"], row["product_family"], row.get("edition", ""), row.get("version", "")))

    seen_in_import = set()
    new_rows = []
    duplicate_count = 0
    blank_count = 0

    for _, row in raw_df.iterrows():
        publisher = _safe_str(row[col_map["publisher"]]) if col_map.get("publisher") else ""
        product = _safe_str(row[col_map["product"]]) if col_map.get("product") else ""
        edition = _safe_str(row[col_map["edition"]]) if col_map.get("edition") else ""
        version = _safe_str(row[col_map["version"]]) if col_map.get("version") else ""
        metric = _safe_str(row[col_map["metric"]]) if col_map.get("metric") else ""

        if not publisher or not product:
            blank_count += 1
            continue

        key = _normalize_key(publisher, product, edition, version)
        if key in existing_keys or key in seen_in_import:
            duplicate_count += 1
            continue
        seen_in_import.add(key)

        cid = "-".join(filter(None, [_slug(publisher)[:12], _slug(product)[:16], _slug(edition)[:12], _slug(version)[:8]]))
        alias = " ".join(filter(None, [publisher, product, edition, version]))

        new_rows.append({
            "canonical_id": cid,
            "publisher": publisher,
            "product_family": product,
            "edition": edition,
            "version": version,
            "metric_type": metric or "(not specified in import - confirm)",
            "aliases": alias,
        })

    return {
        "new_rows": pd.DataFrame(new_rows, columns=["canonical_id", "publisher", "product_family", "edition", "version", "metric_type", "aliases"]),
        "duplicate_count": duplicate_count,
        "blank_count": blank_count,
    }


def commit_import(normalizer, new_rows: pd.DataFrame, canonical_path: str):
    """
    Append the previewed new_rows to the normalizer's library, rebuild the
    matching index, and save to disk. Call this only after the user has
    reviewed the preview_import() output.
    """
    if len(new_rows) == 0:
        return 0
    combined = pd.concat([normalizer.lib, new_rows], ignore_index=True)
    normalizer.lib = combined
    normalizer._build_index()
    normalizer.save(canonical_path)
    return len(new_rows)
