# SAM Application Normalization Accelerator

**Version 1.0 · August 2026**

Ingests software deployment data in *any* format and maps every row to a
canonical product identity with an explicit confidence tier.

Benchmark (5,900 labelled rows across 12 input formats):
- **EXACT / HIGH precision: 100%** · REVIEW precision: 92.6% · Overall: 97.9%
- **False-match rate on deliberate junk: 0.0%**

---

## Quick start

```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the app
streamlit run app.py
```

Open `http://localhost:8501` in your browser.

---

## Project structure

```
sam_normalizer/
├── app.py                    ← Streamlit UI
├── normalizer.py             ← Core matching engine (5-stage cascade)
├── schema_detect.py          ← Auto-detects delimiter + column roles
├── inventory_import.py       ← Product-level inventory classifier
├── file_evidence.py          ← File evidence processor (FileEvidence.csv)
├── path_intel.py             ← Install path / executable path parser
├── product_parser.py         ← Structural decomposition (publisher/product/edition/version)
├── bulk_import.py            ← Grow library from ITAM tool exports
├── llm_classifier.py         ← Optional Groq LLM tier for unresolved rows
├── build_library.py          ← Regenerates canonical_library.csv
├── canonical_library.csv     ← 345 products · 46 publishers
├── benchmark.py              ← Accuracy benchmark (run after any change)
├── run_tests.py              ← Quick test runner
├── generate_large_test_data.py ← Generates 5,900 labelled test rows
├── RELIABILITY_REPORT.md     ← Client-facing accuracy documentation
├── AGENT_INSTRUCTIONS.md     ← Paste into Claude Project for agent use
└── sample_data/
    ├── sample_file_evidence.csv      ← Flexera FileEvidence-style (Name/Version/Path)
    ├── sample_flexera_export.csv     ← Flexera product export
    ├── sample_inventory_export.txt   ← Raw script dump (tab-separated)
    ├── sample_tier1_inventory.txt    ← Tier-1 publishers with messy vendor names
    └── sample_messy_input_v2.csv     ← Heavily abbreviated / mangled names
```

---

## Input formats supported

The app auto-detects delimiter (tab / comma / semicolon / pipe / Excel) and
column roles (product name, vendor, version, host, path). No manual mapping
required for common formats.

| Format | Example | How it works |
|---|---|---|
| **Flexera export** | Publisher / Product Title / Edition / Version | Separate Edition/Version columns composed before matching |
| **ServiceNow SAM** | vendor / software_name / version | snake_case column names recognized |
| **SCCM** | Publisher0 / DisplayName0 / DisplayVersion0 | Suffixed column names recognized |
| **Raw script dump** | Host Name / Name / Vendor / Version / Path | Tab-separated; vendor cross-check applied |
| **File evidence** | Name / Version / Path (one row per FILE) | Separate mode: deduplicates, excludes non-installs, identifies products from file signatures |
| **Paths only** | Device / Discovered Path | Path intelligence extracts candidate text from exe/install paths |
| **Generic** | Any columns | Manual column mapping |

---

## The 5-stage matching cascade

Every row goes through these stages in order, stopping at the first result:

1. **Exact match** — raw cleaned text against known aliases (100% precision)
2. **Expanded exact** — abbreviation expansion (88 rules: Svr→Server, Std→Standard, EE→Enterprise Edition…) then exact match (100% precision)
3. **Fuzzy match** — token-sorted similarity scoring against full alias corpus; score ≥88 → HIGH, ≥70 → REVIEW
4. **Family-level fallback** — for path/exe-derived candidates that identify the product family but not the edition; always REVIEW
5. **Structural parse** — publisher + product + edition + version extracted from the string itself; returns PARSED even for products not in the library

**Confidence tiers:**

| Tier | Meaning | Precision | Action |
|---|---|---|---|
| `EXACT` | Verbatim alias match | 100% | Accept |
| `HIGH` | Matched after expansion or fuzzy ≥88 | 100% | Accept, spot-check |
| `REVIEW` | Fuzzy 70–88, or family-level | 92.6% | Human confirms |
| `PARSED` | Not in library; structurally decomposed | n/a | Human confirms; candidate to add to library |
| `UNRESOLVED` | No usable answer | — | Classify manually (optional LLM hint) |

---

## File evidence mode

Flexera's FileEvidence.csv (and similar raw file scanner output) gives one row
*per file*, not per product. Without special handling, a single Zscaler install
appears as 10+ rows, and many rows represent non-installed files.

This mode:
- **Excludes** rows in Recycle Bin, Windows.old, DriverStore\FileRepository, Downloads, backup snapshots, WinSxS
- **Discards** GUID/hash-named files, `$`-prefixed recycle-bin renames, setup/uninstall executables
- **Identifies** products from a library of ~85 file signatures (exe names, path tokens)
- **Deduplicates** to one row per (device, product)
- **Flags** "supporting files only" where only drivers/helpers were found, no product executable

Tested on a replica of real FileEvidence data: 39 file rows → 14 products.

---

## Growing the library

**From an ITAM tool (Flexera, Snow, ServiceNow SAM):** use the sidebar
import panel — map columns, preview, confirm. Verified ITAM data is better
than typing entries by hand.

**From a confirmed match in the review queue:** click "Confirm & teach
library" — the alias is saved immediately and matched automatically on the
next file.

**By hand:** edit `canonical_library.csv` directly, or run `build_library.py`
after adding entries there.

---

## Optional: LLM tier (free)

For rows still UNRESOLVED after all five stages, the app can ask an LLM for a
suggestion. Uses Groq's free API (llama-3.3-70b-versatile), batched 15 rows/call.

1. Get a free key at https://console.groq.com (no card required)
2. Either set `GROQ_API_KEY=your-key` in your environment, or paste it into
   the "Configure Groq" panel in the app
3. Every suggestion lands as a hint in the review queue — never auto-accepted

---

## Benchmarking

Run after any change to matching logic or the library:

```bash
python3 generate_large_test_data.py   # 5,900 labelled rows (one-time)
python3 benchmark.py                  # score against ground truth
python3 run_tests.py                  # quick pass/fail across formats
python3 run_tests.py 05 --detail      # drill into one file
```

---

## Publisher coverage

Microsoft (104), Oracle (38), IBM (30), Adobe (21), Red Hat (18),
VMware/Broadcom (14), SAP (12), Veritas/Cohesity (10), Citrix (6),
Autodesk (7), SAS (4), MathWorks (2), ANSYS (2), Dassault Systèmes (2),
PTC (2), Siemens (2), Atlassian (4), Salesforce/Tableau (4), Veeam (2),
Commvault (1), plus security vendors, open-source, freeware, and components.

---

## Honest limitations

- **This is synthetic-data accuracy.** Expect real first-contact accuracy to
  be lower until the library has absorbed the client's actual naming conventions.
  Measure on a real sample before quoting numbers to a client.
- **`PARSED` rows have no licence metric.** Structural parsing identifies
  *what* a product is but not *how it's licensed*. Add to the library first.
- **Licence metrics need verification.** VMware, Oracle Java SE, and Red Hat
  Virtualization all changed models recently. Verify against current publisher
  documentation before relying commercially.
- **This is a deployment normalizer, not an ELP.** An Effective Licence
  Position requires deployment *minus* entitlement. Entitlement is out of scope.
- **File versions ≠ product versions.** Never assert a file version from
  FileEvidence as the installed product version.
