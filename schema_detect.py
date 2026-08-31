"""
schema_detect.py
Auto-detect the shape of ANY software inventory/deployment export - Flexera,
ServiceNow SAM, Snow, SCCM, a raw script dump, or a one-off spreadsheet
someone hand-built.

The problem this solves: every source names its columns differently.
  Flexera:     "Publisher", "Product Title", "Product Version"
  ServiceNow:  "vendor", "display_name", "version"
  SCCM:        "Publisher0", "DisplayName0", "DisplayVersion0"
  Raw script:  "Name", "Vendor", "Version", "Install Location"
  Some export: "software_publisher", "app_name", "ver"

Rather than hardcoding any one schema (or making a human map columns every
single time), score each column against known naming patterns AND against the
actual data in it, and pick the best candidate for each role.

Always returns confidence per field, and the app should always show the
detected mapping for confirmation - auto-detection that silently picks the
wrong column is worse than asking.
"""

import re
import pandas as pd

# Column-name patterns per role, most-specific first. Matched case-insensitively
# against a normalized (alphanumeric-only) version of the column name.
NAME_PATTERNS = {
    "product": [
        r"^producttitle$", r"^softwaretitle$", r"^applicationname$", r"^appname$",
        r"^displayname\d*$", r"^productname$", r"^softwarename$", r"^title$",
        r"^product$", r"^software$", r"^application$", r"^name\d*$", r"^app$",
    ],
    "vendor": [
        r"^publisher\d*$", r"^vendor\d*$", r"^manufacturer\d*$",
        r"^softwarepublisher$", r"^softwarevendor$", r"^company$",
    ],
    "version": [
        r"^productversion$", r"^displayversion\d*$", r"^softwareversion$",
        r"^version\d*$", r"^ver$", r"^release$",
    ],
    "edition": [
        r"^edition\d*$", r"^productedition$", r"^softwareedition$", r"^sku$",
    ],
    "path": [
        r"^installlocation\d*$", r"^installpath$", r"^installdir\d*$",
        r"^path$", r"^location$", r"^installsource$", r"^executablepath$",
        r"^filepath$", r"^directory$",
    ],
    "host": [
        r"^hostname$", r"^host$", r"^computername\d*$", r"^devicename$",
        r"^machinename$", r"^device$", r"^computer$", r"^asset$", r"^servername$",
        r"^systemname$", r"^resourcename$",
    ],
    "quantity": [
        r"^quantity$", r"^qty$", r"^count$", r"^installs$", r"^installcount$",
        r"^licensecount$", r"^seats$", r"^installations$",
    ],
}

# Known publisher tokens - used for CONTENT-based detection (a column full of
# these is a vendor column even if it's named something unhelpful like "col3").
COMMON_PUBLISHERS = {
    "microsoft", "oracle", "ibm", "sap", "adobe", "vmware", "citrix", "autodesk",
    "salesforce", "servicenow", "atlassian", "google", "apple", "amazon", "aws",
    "red hat", "redhat", "symantec", "broadcom", "mcafee", "trend micro", "cisco",
    "hp", "hewlett", "dell", "intel", "nvidia", "sas", "mathworks", "ansys",
    "siemens", "ptc", "dassault", "veritas", "veeam", "splunk", "tableau",
    "zoom", "slack", "dropbox", "box", "docusign", "workday", "sage", "intuit",
    "jetbrains", "gitlab", "github", "hashicorp", "elastic", "mongodb",
    "postgresql", "mysql", "teradata", "informatica", "talend", "qlik",
    "micro focus", "opentext", "nuance", "kofax", "solarwinds", "nagios",
    "paloalto", "palo alto", "fortinet", "checkpoint", "check point", "sophos",
    "kaspersky", "bitdefender", "eset", "malwarebytes", "crowdstrike",
}

_VERSION_RE = re.compile(r"^\d+(\.\d+){1,4}$|^\d{1,2}(\.\d+)*[a-z]?$")
_PATH_RE = re.compile(r"([a-zA-Z]:[\\/])|(^[\\/]{2})|([\\/].+[\\/])")


def _norm_colname(col: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(col).lower())


def _name_score(col: str, role: str) -> float:
    """Score 0-100 based on how well the COLUMN NAME matches a role's patterns.
    Earlier patterns in the list score higher (more specific = more confident)."""
    norm = _norm_colname(col)
    patterns = NAME_PATTERNS.get(role, [])
    for i, pat in enumerate(patterns):
        if re.match(pat, norm):
            # first pattern = 100, decaying slightly for later/looser patterns
            return max(70.0, 100.0 - i * 3.0)
    return 0.0


def _content_score(series: pd.Series, role: str, sample_size: int = 60) -> float:
    """Score 0-100 based on what the DATA in the column actually looks like.
    This is what lets detection work on badly-named columns."""
    values = [str(v).strip() for v in series.dropna().head(sample_size) if str(v).strip()]
    if not values:
        return 0.0
    n = len(values)

    if role == "vendor":
        # A vendor column contains the publisher name and LITTLE ELSE.
        # Merely CONTAINING a publisher token is not enough - a product column
        # full of "Microsoft SQL Server 2019 Standard" contains "microsoft"
        # too, and would otherwise steal this role and leave no product column.
        # So require the publisher token to DOMINATE the value: short strings,
        # few words, and low cardinality across the column.
        strong_hits = 0
        for v in values:
            vl = v.lower()
            matched = next((p for p in COMMON_PUBLISHERS if p in vl), None)
            if not matched:
                continue
            # publisher must be most of the value, not a fragment of a long name
            if len(matched) / max(len(vl), 1) >= 0.35 or len(vl.split()) <= 4:
                strong_hits += 1
        base = (strong_hits / n) * 100
        distinct_ratio = len(set(values)) / n
        # vendor columns repeat heavily; product columns rarely do
        if distinct_ratio > 0.6:
            base *= 0.35
        elif distinct_ratio <= 0.3:
            base = min(100.0, base + 15)
        return base

    if role == "version":
        hits = sum(1 for v in values if _VERSION_RE.match(v))
        return (hits / n) * 100

    if role == "path":
        hits = sum(1 for v in values if _PATH_RE.search(v))
        return (hits / n) * 100

    if role == "quantity":
        hits = sum(1 for v in values if re.match(r"^\d+$", v))
        return (hits / n) * 100 if hits == n else 0.0

    if role == "product":
        # Product names: mostly multi-word text, high cardinality, not paths,
        # not pure version numbers.
        non_path = sum(1 for v in values if not _PATH_RE.search(v))
        non_version = sum(1 for v in values if not _VERSION_RE.match(v))
        has_letters = sum(1 for v in values if re.search(r"[A-Za-z]{3,}", v))
        cardinality = len(set(values)) / n
        base = (min(non_path, non_version, has_letters) / n) * 70
        return min(100.0, base + cardinality * 30)

    if role == "host":
        # Hostnames: high cardinality, no spaces, alphanumeric+dashes
        no_space = sum(1 for v in values if " " not in v)
        pattern_ok = sum(1 for v in values if re.match(r"^[A-Za-z0-9\-_.]+$", v))
        cardinality = len(set(values)) / n
        return min(100.0, (min(no_space, pattern_ok) / n) * 60 + cardinality * 40)

    return 0.0


def detect_schema(df: pd.DataFrame) -> dict:
    """
    Returns {role: {"column": name|None, "confidence": 0-100, "basis": str}}
    for each role in NAME_PATTERNS.

    Combines column-name matching and content inspection. Name matches are
    weighted higher when present (an explicitly-named "Publisher" column is
    strong evidence), but content alone can carry a detection when names are
    unhelpful.
    """
    detected = {}
    used_columns = set()

    # Resolve roles in order of how reliably they can be identified, AND with
    # product ahead of vendor: product is the one role the engine cannot work
    # without, so it should claim its column before a weaker signal takes it.
    role_order = ["path", "version", "host", "quantity", "edition", "product", "vendor"]

    for role in role_order:
        best_col, best_score, best_basis = None, 0.0, ""
        for col in df.columns:
            if col in used_columns:
                continue
            name_s = _name_score(col, role)
            content_s = _content_score(df[col], role)

            if name_s > 0:
                combined = name_s * 0.7 + content_s * 0.3
                basis = f"column name + content"
            else:
                combined = content_s * 0.75  # content-only is less certain
                basis = "content pattern only"

            if combined > best_score:
                best_score, best_col, best_basis = combined, col, basis

        # Require a real signal, not just "least bad option"
        threshold = 45 if role in ("product", "vendor") else 50
        if best_score >= threshold:
            detected[role] = {"column": best_col, "confidence": round(best_score, 1), "basis": best_basis}
            used_columns.add(best_col)
        else:
            detected[role] = {"column": None, "confidence": 0.0, "basis": "not detected"}

    # Path-only files: some discovery exports contain nothing but a device
    # identifier and a discovered executable/install path - no product-name
    # column exists at all. The path IS the product signal in that case, so
    # point the product role at it rather than reporting "no product column"
    # and refusing to process an otherwise perfectly usable file.
    if detected["product"]["column"] is None and detected["path"]["column"] is not None:
        detected["product"] = {
            "column": detected["path"]["column"],
            "confidence": detected["path"]["confidence"],
            "basis": "path column used as product source (no product-name column found)",
        }

    return detected


def sniff_and_load(file_path: str) -> pd.DataFrame:
    """
    Load a file without knowing its delimiter. Tries tab, comma, semicolon,
    pipe, and Excel - picks whichever yields the most sensible column split.
    """
    if str(file_path).lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(file_path)

    best_df, best_cols = None, 0
    for sep in ["\t", ",", ";", "|"]:
        try:
            df = pd.read_csv(file_path, sep=sep, engine="python", on_bad_lines="skip")
            if len(df.columns) > best_cols:
                best_df, best_cols = df, len(df.columns)
        except Exception:
            continue

    if best_df is None or best_cols <= 1:
        # Last resort: whitespace-delimited (lossy for multi-word fields)
        try:
            return pd.read_csv(file_path, sep=r"\s{2,}", engine="python", on_bad_lines="skip")
        except Exception:
            return pd.read_csv(file_path, engine="python", on_bad_lines="skip")

    return best_df
