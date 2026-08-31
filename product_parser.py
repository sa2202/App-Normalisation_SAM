"""
product_parser.py
Structural decomposition of a product string into its parts, WITHOUT requiring
the product to exist in the canonical library.

Why this exists (the core design insight):
A curated canonical library can never cover "n publishers x n products" - there
are millions of software titles, and any real client environment will contain
things nobody thought to add. If the ONLY path to a result is "match an entry
in the library," then everything unknown dies at UNRESOLVED and a human has to
classify it from scratch - which is the manual work we're trying to remove.

So instead of only asking "which library entry is this?", also ask
"what are the PARTS of this string?" - publisher, product name, edition,
version - which can be extracted from the string's own structure using
patterns that generalize across publishers.

That gives a useful, structured answer even for a product the library has
never seen:
    "Autodesk AutoCAD 2024 Professional"
    -> publisher=Autodesk, product=AutoCAD, edition=Professional, version=2024
       (not in library, but fully parsed and ready to ADD to the library)

The two approaches complement each other:
  - library match  -> authoritative, includes the license metric (what you
                      actually need for ELP work)
  - structural parse -> always available, no metric, but tells you what the
                      thing IS and gives a ready-made candidate library entry
"""

import re

# Edition/tier tokens that appear across many publishers. Order matters -
# longer/more specific phrases must be checked before their substrings
# (e.g. "Enterprise Plus" before "Enterprise", "Standard Edition 2" before
# "Standard").
EDITION_TOKENS = [
    "advanced enterprise server edition", "advanced workgroup server edition",
    "standard edition 2", "enterprise edition", "standard edition",
    "network deployment", "professional plus", "enterprise plus",
    "business premium", "business standard", "business basic",
    "datacenter", "enterprise", "professional", "standard", "advanced",
    "community", "premium", "ultimate", "essentials", "express", "basic",
    "starter", "developer", "education", "personal", "home", "pro", "lite",
    "suite", "plus", "core", "free", "trial", "evaluation",
]

# Version patterns, most specific first.
VERSION_PATTERNS = [
    r"\b([Rr]\d{4}[a-z]?)\b",              # MathWorks-style release: R2023b
    r"\b(\d{4}\s*[Rr]\d)\b",               # ANSYS-style: 2024 R1
    # Dotted versions MUST be checked before the bare-year pattern, otherwise
    # "2023.1" gets greedily read as year 2023 and leaves an orphaned ".1"
    # stuck in the product name.
    r"\bv?(\d+\.\d+(?:\.\d+){0,3})\b",     # dotted: 15.0.2000.5, 1.8.0, 2023.1
    r"\b(\d{4})\b",                        # year-style: 2019, 2022, 2024
    r"\b(\d+[a-z])\b",                     # Oracle-style: 19c, 21c, 23ai
    r"\bversion\s+(\d+)\b",                # "version 11"
    r"\bv(\d+)\b",                          # v11
]

# Publisher-ish suffixes to strip when a vendor string is verbose.
VENDOR_SUFFIXES = [
    "systems incorporated", "systems inc", "corporation", "incorporated",
    "technologies", "software", "solutions", "limited", "company",
    "corp", "inc", "ltd", "llc", "gmbh", "plc", "co", "sa", "se", "ag", "bv", "nv",
    "s r o", "sro", "spa", "srl", "oyj", "aps", "kk", "pty", "pte", "pvt",
]

# Components/helpers that are NOT separately licensable products. Catching
# these matters: they inflate product counts and clutter review queues.
NON_LICENSABLE_MARKERS = [
    "language pack", "font pack", "runtime", "redistributable", "redist",
    "update", "updater", "refresh manager", "hotfix", "patch", "service pack",
    "driver", "plugin", "plug-in", "add-in", "addin", "extension", "helper",
    "prerequisite", "sdk", "toolkit", "sample", "documentation", "readme",
    "uninstaller", "installer", "setup", "bootstrapper", "component",
    "shared", "common files", "visual c++", "dotnet", ".net framework",
]


# Publisher aliases: maps how a vendor may appear in discovery/ITAM data to
# the canonical publisher name used in the library. Without this, the vendor
# cross-check produces false mismatches - e.g. an SCCM export reporting
# "Broadcom Inc" for a VMware product would look like a mismatch against the
# library's "VMware (Broadcom)", discarding a perfectly good match.
PUBLISHER_ALIASES = {
    "vmware": ["vmware", "broadcom", "vmware inc", "vmware by broadcom"],
    "red hat": ["red hat", "redhat", "red hat inc"],
    "microsoft": ["microsoft", "microsoft corporation", "msft"],
    "oracle": ["oracle", "oracle corporation", "oracle america", "sun microsystems"],
    "ibm": ["ibm", "international business machines", "ibm corp"],
    "adobe": ["adobe", "adobe systems", "adobe systems incorporated", "adobe inc"],
    "sap": ["sap", "sap se", "sap ag", "sap america"],
}


def publisher_pattern_match(pattern: str, vendor: str) -> bool:
    """
    Match a vendor string against a SQL-style wildcard pattern, the way
    Flexera's ARL installer-evidence rules do.

    Real ARL rules don't store literal publisher names - they store patterns:
        IBM%       matches 'IBM', 'IBM Corporation', 'IBM Corp.'
        ibm.com%   matches 'ibm.com', 'ibm.com Inc'
        %Adobe%    matches 'Adobe Systems Incorporated'

    That single convention absorbs an enormous amount of vendor-string
    variation without needing an alias for every legal-entity spelling,
    which is why Flexera's recognition generalizes so well. Supporting the
    same syntax lets the library express rules the same way.

    % = any sequence of characters (including none)
    _ = exactly one character
    Matching is case-insensitive, as in Flexera.
    """
    if not pattern or not vendor:
        return False
    p = str(pattern).strip().lower()
    v = str(vendor).strip().lower()
    if "%" not in p and "_" not in p:
        return p == v          # literal pattern - exact match
    # Translate SQL wildcards to a regex. Build it character by character
    # rather than escape-then-replace: modern Python's re.escape() leaves
    # '%' untouched, so a replace of r"\%" silently matches nothing.
    out = []
    for ch in p:
        if ch == "%":
            out.append(".*")
        elif ch == "_":
            out.append(".")
        else:
            out.append(re.escape(ch))
    return re.fullmatch("".join(out), v) is not None


def publishers_match(library_publisher: str, source_vendor: str) -> bool:
    """Do a library publisher and a source-file vendor string refer to the same
    company? Handles verbose forms, parenthetical suffixes, and acquisitions."""
    if not library_publisher or not source_vendor:
        return False

    # If the library value is a wildcard pattern (Flexera ARL style, e.g.
    # 'IBM%'), evaluate it as a pattern before any normalization - stripping
    # punctuation first would destroy the % and _ metacharacters.
    if "%" in str(library_publisher) or "_" in str(library_publisher):
        return publisher_pattern_match(library_publisher, source_vendor)

    lib = re.sub(r"\(.*?\)", " ", str(library_publisher)).lower()
    lib = re.sub(r"[^a-z0-9 ]", " ", lib)
    lib = re.sub(r"\s+", " ", lib).strip()

    src = re.sub(r"[^a-z0-9 ]", " ", str(source_vendor).lower())
    src = re.sub(r"\s+", " ", src).strip()

    if not lib or not src:
        return False
    if lib in src or src in lib:
        return True

    # Check both against the alias groups
    for canonical, aliases in PUBLISHER_ALIASES.items():
        lib_hit = any(a in lib or lib in a for a in aliases)
        src_hit = any(a in src or src in a for a in aliases)
        if lib_hit and src_hit:
            return True

    return False


def clean_vendor(vendor: str) -> str:
    """Normalize a verbose vendor string to a short publisher name.
    'Adobe Systems Incorporated' -> 'Adobe'
    'Microsoft Corporation'      -> 'Microsoft'
    """
    if not vendor or not isinstance(vendor, str):
        return ""
    text = vendor.strip()
    text = re.sub(r"[.,]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    lower = text.lower()
    for suffix in sorted(VENDOR_SUFFIXES, key=len, reverse=True):
        if lower.endswith(" " + suffix):
            text = text[: -(len(suffix) + 1)].strip()
            lower = text.lower()
    return text.strip()


def is_non_licensable(product_name: str) -> tuple:
    """Does this look like a component/helper rather than a licensable product?
    Returns (bool, matched_marker|None)."""
    if not product_name or not isinstance(product_name, str):
        return False, None
    lower = product_name.lower()
    for marker in NON_LICENSABLE_MARKERS:
        if marker in lower:
            return True, marker
    return False, None


def extract_version(text: str) -> tuple:
    """Extract a version from a product string.
    Returns (version|None, text_with_version_removed)."""
    if not text or not isinstance(text, str):
        return None, text or ""
    for pattern in VERSION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            version = m.group(1)
            residual = (text[: m.start()] + " " + text[m.end():]).strip()
            residual = re.sub(r"\s+", " ", residual)
            return version, residual
    return None, text


def extract_edition(text: str, protect_last_word: bool = True) -> tuple:
    """Extract an edition/tier token from a product string.
    Returns (edition|None, text_with_edition_removed).

    protect_last_word: if stripping the edition would leave NOTHING behind
    (e.g. "Splunk Enterprise" where "Splunk" was already taken as the
    publisher), don't strip it - for some products the tier word IS part of
    the product's actual name. Losing the product name entirely is a worse
    outcome than not identifying the edition.
    """
    if not text or not isinstance(text, str):
        return None, text or ""
    lower = text.lower()
    for token in EDITION_TOKENS:  # already ordered longest-first by construction
        pattern = r"\b" + re.escape(token) + r"\b"
        m = re.search(pattern, lower)
        if m:
            edition = text[m.start():m.end()]
            residual = (text[: m.start()] + " " + text[m.end():]).strip()
            residual = re.sub(r"\s+", " ", residual)
            if protect_last_word and not residual.strip():
                # Stripping would erase the product name - keep the text intact
                # and report no edition rather than returning an empty product.
                return None, text
            return edition.title(), residual
    return None, text


def parse_product(raw_name: str, vendor_hint: str = "") -> dict:
    """
    Decompose a product string into structured parts. Works with or without a
    vendor hint from a separate column.

    Returns:
      publisher, product, edition, version   - the extracted parts
      non_licensable, non_licensable_reason  - component/helper detection
      parse_quality                          - "full" (publisher+product+something)
                                               "partial" (product only)
                                               "poor" (couldn't extract much)
    """
    original = raw_name or ""
    text = str(original).strip()

    non_lic, marker = is_non_licensable(text)

    publisher = clean_vendor(vendor_hint) if vendor_hint else ""

    # If no vendor column, try to pull a known publisher off the front of the string.
    if not publisher and text:
        from schema_detect import COMMON_PUBLISHERS
        lower = text.lower()
        for pub in sorted(COMMON_PUBLISHERS, key=len, reverse=True):
            if lower.startswith(pub + " "):
                publisher = text[: len(pub)].strip()
                text = text[len(pub):].strip()
                break

    # If a vendor hint WAS given and the product string redundantly repeats it,
    # strip the repetition so it doesn't pollute the product name.
    if publisher and text.lower().startswith(publisher.lower() + " "):
        text = text[len(publisher):].strip()

    version, text = extract_version(text)
    edition, text = extract_edition(text)

    product = re.sub(r"[\-–,]+$", "", text).strip()
    product = re.sub(r"\s+", " ", product)

    if publisher and product and (edition or version):
        quality = "full"
    elif product:
        quality = "partial"
    else:
        quality = "poor"

    return {
        "publisher": publisher or None,
        "product": product or None,
        "edition": edition,
        "version": version,
        "non_licensable": non_lic,
        "non_licensable_reason": marker,
        "parse_quality": quality,
    }
