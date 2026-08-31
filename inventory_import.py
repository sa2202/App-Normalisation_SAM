"""
inventory_import.py
Parses and classifies the "software inventory" export format used for
deployment discovery data - columns:

  Host Name, Serial, IP Address, Name, Vendor, Version, Install Date,
  Install Source, Install Location, Comments

This is tab-separated per-host software inventory (one row per installed
product per machine) - a common shape from agent-based discovery tools.

Why this format is actually BETTER than free-text product strings: it already
gives you Vendor as a separate field. That means we're not just fuzzy-matching
a messy product name in isolation - we can cross-check the matched canonical
product's publisher against the source Vendor column. A mismatch there is a
strong signal something went wrong, and is exactly the kind of check that
makes automated matching trustworthy for audit-facing work instead of just
"looks plausible."
"""

import re
import pandas as pd
from normalizer import clean_text


def parse_inventory_export(path: str, sep: str = "\t") -> pd.DataFrame:
    """
    Read a tab-separated inventory export. Falls back to whitespace-splitting
    if tabs aren't found (some exports get mangled into space-padded columns
    when copy-pasted out of a viewer) - this is a best-effort fallback, not a
    substitute for getting the real delimited file when possible.
    """
    try:
        df = pd.read_csv(path, sep=sep, engine="python")
        if len(df.columns) >= 5:
            return df
    except Exception:
        pass
    # Fallback: whitespace-delimited with quoted/multi-word fields is lossy -
    # only use this if tab-parsing genuinely failed.
    return pd.read_csv(path, delim_whitespace=True, engine="python")


def classify_inventory(df: pd.DataFrame, normalizer, name_col: str = "Name",
                        vendor_col: str = "Vendor", version_col: str = "Version",
                        host_col: str = "Host Name", edition_col: str = None,
                        compose_version: bool = True) -> pd.DataFrame:
    """
    Classify every row of a Name/Vendor/Version-style inventory export.

    Adds two things beyond the normal classify() output:
      - vendor_check: "match" / "mismatch" / "no_vendor_data" - compares the
        SOURCE file's Vendor column against the canonical library's publisher
        for whatever got matched. A mismatch downgrades EXACT/HIGH matches to
        REVIEW, because ground-truth vendor data disagreeing with the match is
        a real red flag, not something to bury.
      - host_name: carried through for per-device traceability (important for
        an audit trail - "which machine is this row about" matters).
    """
    results = []
    for _, row in df.iterrows():
        raw_name = str(row.get(name_col, "")) if pd.notna(row.get(name_col)) else ""

        # Compose separate Edition/Version columns into the text being matched.
        # Sources like Flexera split these into their own columns, so matching
        # on the bare Product Title ("SQL Server") throws away the edition and
        # version that decide WHICH SKU this actually is.
        extra_parts = []
        if edition_col and edition_col in row.index and pd.notna(row.get(edition_col)):
            ed_val = str(row.get(edition_col)).strip()
            if ed_val and ed_val.lower() not in raw_name.lower():
                extra_parts.append(ed_val)
        if compose_version and version_col and version_col in row.index and pd.notna(row.get(version_col)):
            ver_val = str(row.get(version_col)).strip()
            # Only compose versions that actually IDENTIFY a product SKU:
            # release years ("2019", "2022") and vendor release codes ("19c",
            # "23ai"). Dotted build numbers ("8.0.2", "15.0.2000.5") are
            # deployment detail, not product identity - composing them in
            # measurably degrades matching, so they're deliberately excluded.
            is_release_year = re.match(r"^(19|20)\d{2}$", ver_val)
            is_release_code = re.match(r"^\d{1,2}[a-z]{1,2}$", ver_val, re.IGNORECASE)
            if (is_release_year or is_release_code) and ver_val.lower() not in raw_name.lower():
                extra_parts.append(ver_val)
        if extra_parts:
            raw_name = (raw_name + " " + " ".join(extra_parts)).strip()
        source_vendor = str(row.get(vendor_col, "")) if pd.notna(row.get(vendor_col)) else ""
        version = str(row.get(version_col, "")) if pd.notna(row.get(version_col)) else ""
        host = row.get(host_col, "") if host_col in df.columns else ""

        result = normalizer.classify(raw_name, vendor_hint=source_vendor)

        # Cross-check matched publisher against the source Vendor column.
        # Skip this for placeholder categories like "(Freeware)"/"(Component)" -
        # those are intentionally not real publisher names, so comparing them
        # against a source Vendor column (e.g. "Adobe Systems Incorporated",
        # or even a real individual author like "Igor Pavlov" for 7-Zip) would
        # always "mismatch" and wrongly downgrade a correct match.
        vendor_check = "no_vendor_data"
        matched_pub_raw = str(result["publisher"]) if result["publisher"] else ""
        if matched_pub_raw.startswith("("):
            vendor_check = "n/a (category match, not a publisher)"
        elif result["publisher"] and source_vendor:
            from product_parser import publishers_match
            if publishers_match(matched_pub_raw, source_vendor):
                vendor_check = "match"
            else:
                vendor_check = "mismatch"
                # A library match that contradicts ground-truth vendor data is
                # very likely just a bad fuzzy match. Rather than showing a
                # wrong publisher/product at REVIEW (a confidently-wrong answer
                # a reviewer might rubber-stamp), discard the library match and
                # fall back to the structural parse, which at minimum respects
                # the vendor the source file actually reported.
                from product_parser import parse_product
                parsed = parse_product(raw_name, source_vendor)
                if parsed["product"]:
                    result["publisher"] = parsed["publisher"]
                    result["product_family"] = parsed["product"]
                    result["edition"] = parsed["edition"]
                    result["version"] = parsed["version"]
                    result["canonical_id"] = None
                    result["metric_type"] = None
                    result["structurally_parsed"] = True
                    result["confidence_tier"] = "PARSED"
                    vendor_check = "mismatch (library match discarded, structurally parsed instead)"
                elif result["confidence_tier"] in ("EXACT", "HIGH"):
                    result["confidence_tier"] = "REVIEW"

        result["source_vendor"] = source_vendor
        result["source_version"] = version
        result["vendor_check"] = vendor_check
        result["host_name"] = host
        results.append(result)

    out = pd.DataFrame(results)
    # Put the traceability/cross-check columns up front for readability
    front_cols = ["host_name", "raw_input", "source_vendor", "vendor_check",
                  "confidence_tier", "match_score", "publisher", "product_family", "edition", "classification"]
    remaining = [c for c in out.columns if c not in front_cols]
    return out[front_cols + remaining]


def detect_path_consolidation(results: pd.DataFrame, raw_names, paths,
                              host_names=None) -> pd.DataFrame:
    """
    Pattern learned from real registry evidence (DisplayName + InstallLocation):
    the DisplayName varies a lot for what's genuinely ONE product - MUI
    suffixes, language-pack variants, version-in-parentheses patch entries -
    but the install folder tends to stay stable. E.g.:

        'Adobe Acrobat Reader DC MUI'  -> ...\\Adobe\\Acrobat Reader DC\\
        'Adobe Acrobat Reader'         -> ...\\Adobe\\Acrobat Reader DC\\
        'Asian Language ... Reader'    -> ...\\Adobe\\Acrobat Reader DC\\

    All three are the same install. This function groups rows by normalized
    install path and flags where the matcher assigned DIFFERENT canonical
    products to rows sharing a path - a strong signal one of those
    classifications is wrong, worth a human's attention before either row
    feeds an ELP count.

    Does NOT auto-merge anything - only surfaces disagreement for review.
    Returns a DataFrame of flagged path-groups.
    """
    def _normalize_path(p):
        if not isinstance(p, str) or not p.strip():
            return None
        p = re.sub(r"^[A-Za-z]:\\?", "", p.strip().lower())
        p = p.rstrip("\\/")
        return p or None

    work = pd.DataFrame({
        "raw_input": list(raw_names),
        "norm_path": [_normalize_path(p) for p in paths],
        "canonical_id": results["canonical_id"].values,
        "product_family": results["product_family"].values,
        "confidence_tier": results["confidence_tier"].values,
    })
    if host_names is not None:
        work["host"] = list(host_names)
        group_cols = ["host", "norm_path"]
    else:
        group_cols = ["norm_path"]

    work = work[work["norm_path"].notna()]
    flagged = []
    for key, grp in work.groupby(group_cols):
        distinct_products = grp["canonical_id"].fillna("UNMATCHED").nunique()
        if len(grp) > 1 and distinct_products > 1:
            flagged.append({
                "path": key if not host_names else key[-1],
                "host": key[0] if host_names else None,
                "rows_sharing_path": len(grp),
                "distinct_products_assigned": distinct_products,
                "raw_inputs": " | ".join(grp["raw_input"].astype(str)),
                "products_assigned": " | ".join(grp["product_family"].fillna("(none)").astype(str).unique()),
            })
    return pd.DataFrame(flagged)
