"""
file_evidence.py
Processes FILE EVIDENCE data - the raw layer beneath product recognition,
as produced by Flexera's file scanner (FileEvidence.csv) and similar tools.

File evidence looks like:
    Name                Version         Path
    zsawdrv.sys         14.2.0          C:\\Program Files\\Zscaler\\ZSAWFPDriver\\arm64\\
    zapprd.sys          3.6.0.0         C:\\Program Files\\Zscaler\\ZSAFilterDriver\\win10\\arm64\\
    ZEPService.exe      23.11.6.1       C:\\Program Files\\Zscaler\\ZEP\\
    zepprotect.sys      23.11.5.1       C:\\Program Files\\Zscaler\\ZEP\\

Four things make this fundamentally different from product-level inventory,
and getting any of them wrong produces a badly wrong deployment count:

1. ROWS ARE FILES, NOT PRODUCTS.
   The four rows above are ONE product (Zscaler), not four. Without
   deduplication, a single Zscaler install looks like a dozen deployments.

2. MOST ROWS ARE NOT LICENSABLE.
   Drivers (.sys), helper services, and bundled components are evidence that
   a product is present - they are never separately licensable themselves.

3. MANY PATHS ARE NOT REAL INSTALLATIONS.
   $Recycle.Bin, Windows.old, DriverStore\\FileRepository, Downloads folders,
   and SystemRepair snapshot backups all contain executables that are NOT
   installed software. Counting them overstates deployment - the single most
   common way an automated file-evidence count goes wrong.

4. VERSION IS FILE VERSION, NOT PRODUCT VERSION.
   zsawdrv.sys 14.2.0 does not mean "Zscaler 14.2.0". File versions are
   reported for transparency but never asserted as product versions.

The output is one row per (device, product) - the deduplicated, licensable
deployment picture - plus a full audit trail of which file evidence supported
each conclusion.
"""

import re
import os
import pandas as pd


# ---------------------------------------------------------------------------
# PATH EXCLUSIONS - locations whose contents are not installed software
# ---------------------------------------------------------------------------
EXCLUDED_PATH_PATTERNS = [
    (r"\$recycle\.bin", "recycle bin"),
    (r"\\windows\.old\\", "previous Windows installation"),
    (r"driverstore\\filerepository", "Windows driver store (staged, not installed)"),
    (r"\\downloads\\", "user Downloads folder"),
    (r"\\temp\\", "temp folder"),
    (r"\\tmp\\", "temp folder"),
    (r"systemrepair\\snapshots", "system repair snapshot"),
    (r"\\backup\\", "backup folder"),
    (r"\\\$windows\.~", "Windows upgrade staging"),
    (r"\\softwaredistribution\\", "Windows Update cache"),
    (r"\\winsxs\\", "Windows component store"),
    (r"\\installer\\\$patchcache", "installer patch cache"),
    (r"\\package cache\\", "installer package cache"),
    (r"\\prefetch\\", "prefetch"),
    (r"\\recycler\\", "recycler"),
    (r"\\system volume information", "system volume information"),
    (r"\\\.git\\", "source control working copy"),
    (r"\\node_modules\\", "package dependency tree"),
]
_EXCL = [(re.compile(p, re.IGNORECASE), why) for p, why in EXCLUDED_PATH_PATTERNS]


# ---------------------------------------------------------------------------
# FILE-NAME NOISE - names that carry no product signal
# ---------------------------------------------------------------------------
NOISE_FILENAME_PATTERNS = [
    (r"^[0-9A-F]{32,}\.", "GUID/hash-named file"),
    (r"^\$[A-Z0-9]+\.", "recycle-bin renamed file"),
    (r"^~", "temporary file"),
    (r"^setup\d*\.", "installer"),
    (r"^install\d*\.", "installer"),
    (r"^uninstall\d*\.", "uninstaller"),
    (r"^unins\d+\.", "uninstaller"),
    (r"^vcredist", "Visual C++ redistributable installer"),
    (r"^dotnetfx", ".NET installer"),
]
_NOISE = [(re.compile(p, re.IGNORECASE), why) for p, why in NOISE_FILENAME_PATTERNS]


# ---------------------------------------------------------------------------
# FILE SIGNATURES - filename (or filename+path token) -> product family
#
# This is the file-evidence equivalent of the canonical library, and the same
# principle applies: it compounds in value. Every signature confirmed during a
# real engagement should be added here.
#
# Format: (filename_pattern, path_token_or_None, product_family, publisher, licensable)
#   licensable=False means "this file proves the product is present, but this
#   FILE is a driver/helper and is never itself a licensable item".
# ---------------------------------------------------------------------------
FILE_SIGNATURES = [
    # --- Zscaler (the example from real FileEvidence data) ---
    (r"^zepservice\.exe$", None, "Zscaler Client Connector", "Zscaler", True),
    (r"^zsatray\.exe$", None, "Zscaler Client Connector", "Zscaler", True),
    (r"^zsatunnel\.exe$", None, "Zscaler Client Connector", "Zscaler", True),
    (r"^zep\w*\.(sys|exe)$", "zscaler", "Zscaler Client Connector", "Zscaler", False),
    (r"^zsa\w*\.(sys|exe)$", "zscaler", "Zscaler Client Connector", "Zscaler", False),
    (r"^zapprd\.sys$", "zscaler", "Zscaler Client Connector", "Zscaler", False),

    # --- Microsoft ---
    (r"^sqlservr\.exe$", None, "SQL Server", "Microsoft", True),
    (r"^ssms\.exe$", None, "SQL Server Management Studio", "Microsoft", True),
    (r"^winword\.exe$", None, "Office", "Microsoft", True),
    (r"^excel\.exe$", None, "Office", "Microsoft", True),
    (r"^powerpnt\.exe$", None, "Office", "Microsoft", True),
    (r"^outlook\.exe$", None, "Office", "Microsoft", True),
    (r"^msaccess\.exe$", None, "Office", "Microsoft", True),
    (r"^onenote\.exe$", None, "Office", "Microsoft", True),
    (r"^winproj\.exe$", None, "Project", "Microsoft", True),
    (r"^visio\.exe$", None, "Visio", "Microsoft", True),
    (r"^devenv\.exe$", None, "Visual Studio", "Microsoft", True),
    (r"^code\.exe$", None, "Visual Studio Code", "Microsoft", True),
    (r"^w3wp\.exe$", None, "Internet Information Services", "Microsoft", False),
    (r"^msedge\.exe$", None, "Microsoft Edge", "Microsoft", True),
    (r"^teams\.exe$", None, "Microsoft Teams", "Microsoft", True),
    (r"^onedrive\.exe$", None, "OneDrive", "Microsoft", True),

    # --- Oracle ---
    (r"^oracle\.exe$", None, "Database", "Oracle", True),
    (r"^tnslsnr\.exe$", None, "Database", "Oracle", False),
    (r"^sqlplus\.exe$", None, "Database", "Oracle", False),
    (r"^oradim\.exe$", None, "Database", "Oracle", False),
    (r"^java\.exe$", "weblogic", "WebLogic Server", "Oracle", True),
    (r"^virtualbox\.exe$", None, "VM VirtualBox", "Oracle", True),

    # --- IBM ---
    (r"^db2syscs\.exe$", None, "Db2", "IBM", True),
    (r"^db2sysc$", None, "Db2", "IBM", True),
    (r"^db2fmcd\.exe$", None, "Db2", "IBM", False),
    (r"^wsadmin\.(bat|sh|exe)$", None, "WebSphere Application Server", "IBM", True),
    (r"^amqzxma0\.exe$", None, "MQ", "IBM", True),
    (r"^besclient\.exe$", None, "BigFix", "IBM", True),
    (r"^stats\.exe$", "spss", "SPSS Statistics", "IBM", True),

    # --- VMware ---
    (r"^vmtoolsd\.exe$", None, "VMware Tools", "VMware (Broadcom)", False),
    (r"^vmware\.exe$", None, "Workstation Pro", "VMware (Broadcom)", True),
    (r"^vmware-vmx\.exe$", None, "Workstation Pro", "VMware (Broadcom)", False),
    (r"^vmware-view\.exe$", None, "Horizon", "VMware (Broadcom)", True),
    (r"^vpxd\.exe$", None, "vCenter Server", "VMware (Broadcom)", True),

    # --- Adobe ---
    (r"^acrobat\.exe$", None, "Acrobat", "Adobe", True),
    (r"^acrord32\.exe$", None, "Adobe Acrobat Reader", "(Freeware)", True),
    (r"^photoshop\.exe$", None, "Creative Cloud", "Adobe", True),
    (r"^illustrator\.exe$", None, "Creative Cloud", "Adobe", True),
    (r"^indesign\.exe$", None, "Creative Cloud", "Adobe", True),
    (r"^adobe premiere pro\.exe$", None, "Creative Cloud", "Adobe", True),
    (r"^afterfx\.exe$", None, "Creative Cloud", "Adobe", True),
    (r"^adobearm\.exe$", None, "Adobe Acrobat/Reader Update Component", "(Component)", False),
    (r"^armsvc\.exe$", None, "Adobe Acrobat/Reader Update Component", "(Component)", False),
    (r"^adobegcclient\.exe$", None, "Adobe Genuine Software Integrity Service", "(Component)", False),

    # --- SAP ---
    (r"^saplogon\.exe$", None, "SAP GUI", "(Component)", False),
    (r"^sapgui\.exe$", None, "SAP GUI", "(Component)", False),

    # --- Citrix ---
    (r"^wfica32\.exe$", None, "Citrix Workspace App", "(Component)", False),
    (r"^cdviewer\.exe$", None, "Citrix Workspace App", "(Component)", False),
    (r"^receiver\.exe$", None, "Citrix Workspace App", "(Component)", False),

    # --- Veritas ---
    (r"^bpcd\.exe$", None, "NetBackup", "Veritas (Cohesity)", True),
    (r"^nbwin\.exe$", None, "NetBackup", "Veritas (Cohesity)", True),
    (r"^beserver\.exe$", None, "Backup Exec", "Veritas (Cohesity)", True),

    # --- Common third-party seen in the sample evidence ---
    (r"^winzip\d*\.exe$", None, "WinZip", "WinZip (Alludo)", True),
    (r"^wzqkpick\.exe$", "winzip", "WinZip", "WinZip (Alludo)", False),
    (r"^wzpreviewer\d*\.exe$", "winzip", "WinZip", "WinZip (Alludo)", False),
    (r"^w2msg\.exe$", "winzip", "WinZip", "WinZip (Alludo)", False),
    (r"^wpaexporter\.exe$", "windows kits", "Windows Performance Toolkit", "(Component)", False),
    (r"^wpa\.exe$", "windows kits", "Windows Performance Toolkit", "(Component)", False),
    (r"^brcow_\w+\.sys$", "sure click", "HP Sure Click", "HP", False),
    (r"^hpsureclick\w*\.exe$", None, "HP Sure Click", "HP", True),
    (r"^hpworkwell\w*\.exe$", None, "HP Work Well", "HP", True),
    (r"^zohomeeting\.exe$", None, "Zoho Meeting", "Zoho", True),
    (r"^toolsiq\.exe$", "zohomeeting", "Zoho Meeting", "Zoho", False),
    (r"^chrome\.exe$", None, "Google Chrome", "(Freeware)", True),
    (r"^firefox\.exe$", None, "Mozilla Firefox", "(Freeware)", True),
    (r"^7zfm\.exe$", None, "7-Zip", "(Freeware)", True),
    (r"^7z\.exe$", None, "7-Zip", "(Freeware)", False),
    (r"^notepad\+\+\.exe$", None, "Notepad++", "(Freeware)", True),
    (r"^putty\.exe$", None, "PuTTY", "(Freeware)", True),
    (r"^winscp\.exe$", None, "WinSCP", "(Freeware)", True),
    (r"^vlc\.exe$", None, "VLC Media Player", "(Freeware)", True),
    (r"^wireshark\.exe$", None, "Wireshark", "(Freeware)", True),
]
_SIGS = [(re.compile(p, re.IGNORECASE), tok, fam, pub, lic) for p, tok, fam, pub, lic in FILE_SIGNATURES]


# Install-directory tokens that identify a vendor even with no file signature.
# Used as a weaker fallback than a file signature - reported as lower confidence.
VENDOR_DIR_HINTS = {
    "zscaler": ("Zscaler Client Connector", "Zscaler"),
    "winzip": ("WinZip", "WinZip (Alludo)"),
    "zohomeeting": ("Zoho Meeting", "Zoho"),
    "sure click": ("HP Sure Click", "HP"),
    "windows kits": ("Windows SDK / Performance Toolkit", "(Component)"),
    "microsoft sql server": ("SQL Server", "Microsoft"),
    "microsoft office": ("Office", "Microsoft"),
    "adobe": ("Adobe product (unspecified)", "Adobe"),
    "vmware": ("VMware product (unspecified)", "VMware (Broadcom)"),
    "oracle": ("Oracle product (unspecified)", "Oracle"),
    "ibm": ("IBM product (unspecified)", "IBM"),
}


def looks_like_file_evidence(df: pd.DataFrame) -> bool:
    """Does this dataframe look like file evidence (filenames + paths) rather
    than product-level inventory?"""
    cols = {str(c).strip().lower() for c in df.columns}
    if not ({"name", "path"} <= cols or {"file name", "path"} <= cols):
        return False
    name_col = next((c for c in df.columns if str(c).strip().lower() in ("name", "file name", "filename")), None)
    if name_col is None:
        return False
    sample = df[name_col].dropna().astype(str).head(50)
    if sample.empty:
        return False
    # File evidence: values are filenames with executable/library extensions
    ext_hits = sample.str.contains(r"\.(?:exe|sys|dll|so|jar|bat|cmd|sh|msi|ocx)$", case=False, regex=True).mean()
    return ext_hits >= 0.5


def path_excluded(path: str):
    """Is this path a location whose contents are not installed software?
    Returns (excluded: bool, reason: str|None)."""
    if not isinstance(path, str) or not path.strip():
        return False, None
    for rx, why in _EXCL:
        if rx.search(path):
            return True, why
    return False, None


def filename_is_noise(name: str):
    """Returns (is_noise: bool, reason: str|None)."""
    if not isinstance(name, str) or not name.strip():
        return True, "blank filename"
    base = os.path.basename(name.strip())
    for rx, why in _NOISE:
        if rx.search(base):
            return True, why
    return False, None


def match_file_signature(name: str, path: str):
    """Match a filename (optionally constrained by a path token) to a product.
    Returns dict or None."""
    if not isinstance(name, str):
        return None
    base = os.path.basename(name.strip()).lower()
    path_l = (path or "").lower()
    for rx, tok, fam, pub, lic in _SIGS:
        if rx.match(base):
            if tok and tok not in path_l:
                continue
            return {"product_family": fam, "publisher": pub,
                    "licensable_file": lic, "evidence": "file signature"}
    return None


def match_vendor_dir(path: str):
    """Weaker fallback: identify a vendor from the install directory alone."""
    if not isinstance(path, str):
        return None
    p = path.lower()
    for token, (fam, pub) in VENDOR_DIR_HINTS.items():
        if token in p:
            return {"product_family": fam, "publisher": pub,
                    "licensable_file": False, "evidence": "install directory"}
    return None


def process_file_evidence(df: pd.DataFrame, name_col="Name", version_col="Version",
                          path_col="Path", device_col=None) -> dict:
    """
    Process raw file evidence into a deduplicated product-level view.

    Returns dict with:
      detail   - every input row, annotated (full audit trail)
      products - one row per (device, product): the deployment picture
      stats    - counts for reporting
    """
    rows = []
    for _, r in df.iterrows():
        name = str(r.get(name_col, "") or "")
        version = str(r.get(version_col, "") or "")
        path = str(r.get(path_col, "") or "")
        device = str(r.get(device_col, "") or "") if device_col else ""

        excluded, excl_reason = path_excluded(path)
        noise, noise_reason = filename_is_noise(name)

        rec = {
            "device": device, "file_name": name, "file_version": version, "path": path,
            "excluded": excluded, "exclusion_reason": excl_reason,
            "noise": noise, "noise_reason": noise_reason,
            "product_family": None, "publisher": None,
            "licensable_file": False, "evidence": None, "status": None,
        }

        if excluded:
            rec["status"] = f"EXCLUDED - {excl_reason}"
            rows.append(rec)
            continue
        if noise:
            rec["status"] = f"NOISE - {noise_reason}"
            rows.append(rec)
            continue

        hit = match_file_signature(name, path) or match_vendor_dir(path)
        if hit:
            rec.update(hit)
            rec["status"] = "IDENTIFIED"
        else:
            rec["status"] = "UNIDENTIFIED"
        rows.append(rec)

    detail = pd.DataFrame(rows)

    # ---- Deduplicate to one row per (device, product) ----
    ident = detail[detail["status"] == "IDENTIFIED"].copy()
    if len(ident):
        grouped = ident.groupby(["device", "publisher", "product_family"], dropna=False)
        products = grouped.agg(
            supporting_files=("file_name", "count"),
            licensable_evidence=("licensable_file", "any"),
            file_versions=("file_version", lambda s: "; ".join(sorted({v for v in s if v})[:5])),
            example_path=("path", "first"),
            evidence_types=("evidence", lambda s: "; ".join(sorted(set(s)))),
        ).reset_index()
        # A product supported ONLY by driver/helper files is present but the
        # files themselves are not licensable items - flag rather than assume.
        products["confidence"] = products["licensable_evidence"].map(
            {True: "product executable found", False: "supporting files only - confirm install"})
        products = products.drop(columns=["licensable_evidence"])
    else:
        products = pd.DataFrame(columns=["device", "publisher", "product_family", "supporting_files",
                                          "file_versions", "example_path", "evidence_types", "confidence"])

    stats = {
        "input_rows": len(detail),
        "excluded_paths": int(detail["excluded"].sum()),
        "noise_files": int(detail["noise"].sum()),
        "identified_rows": int((detail["status"] == "IDENTIFIED").sum()),
        "unidentified_rows": int((detail["status"] == "UNIDENTIFIED").sum()),
        "distinct_products": len(products),
        "dedup_ratio": (len(products) / max(int((detail["status"] == "IDENTIFIED").sum()), 1)),
    }

    return {"detail": detail, "products": products, "stats": stats}
