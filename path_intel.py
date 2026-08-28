"""
path_intel.py
Deployment-data intelligence: SCCM / discovery-tool exports frequently give you
an install path or executable path instead of a clean product name, e.g.:

  C:\\Program Files\\Microsoft SQL Server\\MSSQL15.MSSQLSERVER\\MSSQL\\Binn\\sqlservr.exe
  C:\\Program Files (x86)\\IBM\\WebSphere\\AppServer\\bin\\WASX7\\wsadmin.exe

This is DEPLOYMENT data (what's actually installed in the client's environment),
not entitlement data - it never carries qty/purchase info, only "this got found
on a machine". It needs the same normalization treatment, just with an extra
pre-processing pass to strip path noise before the text reaches the matching
cascade in normalizer.py.
"""

import re

# Path segments that carry no product signal - drive letters, generic OS/install
# folders, architecture markers, and bare version-number folders.
PATH_STOPWORDS = {
    "c", "d", "e",  # drive letters (already split off separately, kept as a safety net)
    "program files", "program files (x86)", "programdata", "windows",
    "system32", "syswow64", "users", "appdata", "local", "locallow", "roaming",
    "bin", "binn", "tools", "redist", "common files", "shared", "msocache",
    "x86", "x64", "win32", "win64", "amd64", "application",
}

# Known executable basenames -> a text hint fed into the normal matching
# pipeline. This does NOT resolve to a specific edition/version by itself
# (an exe name alone can't tell Standard from Enterprise) - it just gives the
# fuzzy matcher a strong nudge toward the right product family. Extend this
# table over time; like the canonical library, it compounds in value.
KNOWN_EXECUTABLES = {
    "sqlservr": "sql server database engine",
    "ssms": "sql server management studio",
    "oracle": "oracle database",
    "sqlplus": "oracle database sql plus",
    "db2syscs": "db2 database",
    "db2fmcd": "db2 database",
    "wsadmin": "websphere application server",
    "startserver": "weblogic server",
    "stopserver": "weblogic server",
    "w3wp": "iis windows internet information services",
    "httpd": "apache http server",
    "nginx": "nginx web server",
    "java": "java runtime",
    "javaw": "java runtime",
    "acrobat": "adobe acrobat",
    "acrord32": "adobe acrobat reader",
    "photoshop": "adobe photoshop",
    "illustrator": "adobe illustrator",
    "premiere": "adobe premiere pro",
    "excel": "microsoft office excel",
    "winword": "microsoft office word",
    "powerpnt": "microsoft office powerpoint",
    "outlook": "microsoft office outlook",
    "visio": "microsoft visio",
    "winproj": "microsoft project",
    "devenv": "visual studio",
    "code": "visual studio code",
    "chrome": "google chrome",
    "notepad++": "notepad++",
    "7zfm": "7 zip",
    "vlc": "vlc media player",
}

# Additional noise patterns for internal vendor instance/install-folder naming
# conventions that carry no product signal (regex, matched case-insensitively
# against the whole segment).
NOISE_SEGMENT_PATTERNS = [
    r"^mssql\d*(\..*)?$",       # SQL Server instance folders: MSSQL15.MSSQLSERVER, MSSQL
    r"^dbhome(_\d+)?$",          # Oracle: dbhome_1
    r"^root$",                   # Office: root\Office16
    r"^office\d+$",              # Office16, Office15 - version-coded, not product signal on its own
]

# Mid-path folder names that ARE meaningful product signal even though they're
# not the final executable - e.g. an Oracle WebLogic install nearly always has
# a 'wlserver' folder somewhere in the path regardless of which .exe/.cmd is
# discovered. Same idea as KNOWN_EXECUTABLES, just for folder segments.
FOLDER_HINTS = {
    "wlserver": "weblogic server",
    "oracle_home": "oracle database",
    "sqllib": "db2 database",
    "websphere": "websphere application server",
    "middleware": "",  # too generic alone; not a hint by itself, just don't drop it as noise
}

_NOISE_RE = [re.compile(p, re.IGNORECASE) for p in NOISE_SEGMENT_PATTERNS]

_PATH_SEP_RE = re.compile(r"[\\/]+")
_DRIVE_RE = re.compile(r"^[a-zA-Z]:$")
_UNC_RE = re.compile(r"^\\\\[^\\]+\\[^\\]+")  # \\server\share
_VERSION_FOLDER_RE = re.compile(r"^v?\d+([._]\d+)*$")  # "130", "15.0", "v14_0"


def looks_like_path(text: str) -> bool:
    """Heuristic: does this raw string look like a filesystem path rather than
    a plain product name?"""
    if not isinstance(text, str) or not text.strip():
        return False
    return bool(
        "\\" in text
        or (text.count("/") >= 2)
        or re.match(r"^[a-zA-Z]:[\\/]", text.strip())
        or text.strip().lower().startswith(r"\\")
    )


def extract_candidate_from_path(raw: str):
    """
    Turn a raw install/executable path into a short candidate string suitable
    for feeding into the normal normalization cascade, plus metadata about
    what was stripped (kept for audit-trail transparency - never silently
    swap the text without showing what was extracted).

    Returns: dict with keys:
      candidate_text   - cleaned string to run through classify()
      exe_hint         - text hint if a known executable was recognized, else None
      dropped_segments - list of path segments that were filtered out (for review)
    """
    text = raw.strip()
    text = _UNC_RE.sub("", text)

    segments = [s for s in _PATH_SEP_RE.split(text) if s]

    kept, dropped = [], []
    exe_hint = None
    folder_hint = None

    for i, seg in enumerate(segments):
        seg_clean = seg.strip()
        seg_lower = seg_clean.lower()
        is_last = (i == len(segments) - 1)

        if _DRIVE_RE.match(seg_clean):
            dropped.append(seg_clean)
            continue

        if is_last and "." in seg_clean:
            # Final segment with an extension = the executable/file itself.
            basename = seg_clean.rsplit(".", 1)[0].lower()
            if basename in KNOWN_EXECUTABLES:
                exe_hint = KNOWN_EXECUTABLES[basename]
            else:
                dropped.append(seg_clean)
            continue

        if seg_lower in PATH_STOPWORDS:
            dropped.append(seg_clean)
            continue

        if any(pat.match(seg_clean) for pat in _NOISE_RE):
            dropped.append(seg_clean)
            continue

        if _VERSION_FOLDER_RE.match(seg_clean):
            dropped.append(seg_clean)
            continue

        if seg_lower in FOLDER_HINTS:
            hint = FOLDER_HINTS[seg_lower]
            if hint and not folder_hint:
                folder_hint = hint
            dropped.append(seg_clean)  # the raw folder name itself isn't useful text, the hint is
            continue

        kept.append(seg_clean)

    # Prefer the executable hint (most specific signal) over a folder hint;
    # fall back to the folder hint only if no exe was recognized.
    final_hint = exe_hint or folder_hint

    candidate_text = " ".join(kept)
    if final_hint:
        candidate_text = (candidate_text + " " + final_hint).strip()

    return {
        "candidate_text": candidate_text,
        "exe_hint": final_hint,
        "dropped_segments": dropped,
    }
