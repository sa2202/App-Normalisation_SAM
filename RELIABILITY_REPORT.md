# Application Normalization Accelerator — Reliability Report

**Version:** 1.0
**Date:** August 2026
**Library:** 345 products across 46 publishers
**Benchmark:** 5,900 labelled rows across 12 input formats

---

## 1. Executive summary

The Application Normalization Accelerator ingests software deployment data in
arbitrary formats and maps each row to a canonical product identity with an
explicit confidence tier.

Measured against 5,900 ground-truth-labelled rows:

| Metric | Result |
|---|---|
| **Precision on library matches** | **97.9%** (n=5,075 scoreable rows) |
| **Precision — EXACT tier** | **100.0%** (n=2,126) |
| **Precision — HIGH tier** | **100.0%** (n=2,167) |
| **Precision — REVIEW tier** | 92.6% (n=297) |
| **False matches on deliberate junk** | **0.0%** (n=215 junk rows) |
| **Coverage (rows producing any answer)** | 96.6%–100% depending on format |

**What this means operationally:** rows tiered EXACT or HIGH did not produce a
single incorrect match across 4,293 scored rows. Rows tiered REVIEW require
human confirmation — which is what that tier exists to signal.

---

## 2. Why both precision and coverage are reported

A normalization engine can trivially achieve 100% coverage by matching every
row to *something*. That is worse than useless for licence-position work,
because a confident-looking wrong answer is likely to be accepted by a reviewer,
whereas an unresolved row is obviously flagged for attention.

This benchmark therefore reports three numbers together:

- **Coverage** — did the row get an answer at all?
- **Precision** — of the rows that got a library match, was it the *right* one?
- **False-match rate** — how often did deliberate junk (`asdkjaslkdj123`,
  `TBD`, empty strings, 400-character garbage) get matched to a real product?

The false-match rate of **0.0%** is the check that the coverage figure is
honest. The engine is not over-matching to inflate its hit rate.

---

## 3. Confidence tiers and how to use them

| Tier | Meaning | Measured precision | Recommended action |
|---|---|---|---|
| `EXACT` | Matched a known alias verbatim | 100.0% | Accept |
| `HIGH` | Matched after abbreviation expansion, or fuzzy score ≥88 | 100.0% | Accept, spot-check |
| `REVIEW` | Fuzzy 70–88, or family-level match (edition undetermined) | 92.6% | **Human confirms** |
| `PARSED` | Not in library; decomposed structurally into publisher/product/edition/version | n/a — no library match claimed | Human confirms; candidate to add to library |
| `UNRESOLVED` | No usable answer | n/a | Human classifies from scratch |

**Critical caveat on `PARSED`:** these rows identify *what the product is* but
carry **no licence metric**, because the product is not in the canonical
library. They cannot be used for licence-position calculation until the product
is added to the library and its metric confirmed.

---

## 4. Per-format results

| Input format | Rows | Coverage | Library match | Precision |
|---|---|---|---|---|
| Flexera-style export | 500 | 100.0% | 92.2% | 99.3% |
| ServiceNow-style export | 500 | 99.4% | 95.0% | 100.0% |
| SCCM-style export | 500 | 100.0% | 97.8% | 100.0% |
| Raw script dump (tab-separated) | 500 | 100.0% | 97.8% | 99.2% |
| Install/executable paths only | 500 | 100.0% | 85.6% | 82.9% |
| Heavily mangled/abbreviated names | 500 | 96.6% | 82.2% | 96.4% |
| Unknown publishers (not in library) | 500 | 100.0% | 0.0% | n/a (structural parse) |
| Unhelpful column names (`col_a`…) | 500 | 100.0% | 100.0% | 100.0% |
| Semicolon-delimited, German headers | 500 | 100.0% | 99.4% | 100.0% |
| Tier-1 publishers only | 500 | 100.0% | 98.8% | 100.0% |
| Excel (.xlsx) | 500 | 100.0% | 98.8% | 100.0% |
| Edge cases (blanks, dupes, unicode, junk) | 400 | 87.2% | 70.0% | 100.0% |

---

## 5. Known limitations — read before relying on this

These are real and should be stated to any client rather than discovered by
them.

### 5.1 Path-only data cannot determine edition
Precision on the paths-only dataset is 82.9%, materially lower than other
formats. This is **not primarily an engine defect** — an executable path such
as `...\MSSQL15.MSSQLSERVER\MSSQL\Binn\sqlservr.exe` identifies SQL Server but
contains no information about Standard vs Enterprise. Edition must come from
another source (registry keys, licence files, DBA confirmation). Rows derived
from paths alone are tiered `REVIEW` by design.

### 5.2 This benchmark uses synthetic data
The 5,900 rows are generated from the canonical library with realistic
mangling (abbreviations, case changes, whitespace, appended noise, verbose
vendor names). **This is not the same as validation against a real client
estate.** Real inventories contain in-house applications, bespoke naming
conventions, and regional variants not represented here. Expect measured
accuracy on first real client data to be **lower** than these figures until
the library has been extended with that client's actual products.

**Recommended before client delivery:** run the engine against a sample of the
client's real inventory, manually verify a random sample of 100+ rows, and
report *that* number alongside these.

### 5.3 The library covers common products, not all products
345 products across 46 publishers covers the mainstream enterprise estate.
It does not cover the long tail. Unknown products fall to the `PARSED` tier —
identified but without a licence metric. This is by design, but it means the
library must grow per engagement.

### 5.4 Licence metrics are identification aids, not calculations
The `metric_type` field records *how a product is licensed* (e.g. "PVU",
"Per Socket-Pair", "Per Core, 16-core minimum per CPU"). It does **not**
compute a licence requirement. Converting deployment counts to required
entitlements — Oracle core factor tables, IBM PVU tables, Microsoft core
minimums, VMware's 16-core floor, Red Hat's socket-pair and Virtual Datacenter
rules — is a separate layer that is **not built**.

### 5.5 Deployment only — this is not an ELP
The engine processes deployment/installation data. An Effective Licence
Position requires deployment **minus entitlement**. Entitlement data is out of
scope. Output should be described as a *normalized deployment inventory*, not
a compliance position.

### 5.6 Licensing terms change
Metrics recorded here reflect publisher terms as researched in August 2026.
Several are recent and volatile — VMware moved to per-core subscription under
Broadcom in 2024, Oracle Java SE moved to an employee-count metric, Red Hat
Virtualization reached end-of-life. **Verify metrics against current publisher
documentation before relying on them commercially.**

### 5.7 Fuzzy-matching backend
Benchmark figures were produced using Python's built-in `difflib` fallback
matcher. With `rapidfuzz` installed (see `requirements.txt`) results should be
equal or better, but that configuration has not been separately benchmarked.

---

## 6. Reproducing these results

```bash
pip install -r requirements.txt
python3 build_library.py              # regenerate canonical library
python3 generate_large_test_data.py   # regenerate 5,900 labelled rows
python3 benchmark.py                  # score against ground truth
```

Test data generation is seeded (`random.seed(20260827)`), so runs are
reproducible.

**Run `benchmark.py` after any change to matching logic or the library.**
During development, one change improved Flexera-format handling while silently
degrading tier-1 accuracy from 100% EXACT to a mix of HIGH/REVIEW; another
caused two entire formats to fail schema detection. Both were caught only by
re-running the benchmark. A change that helps one format while breaking another
is easy to ship unnoticed.

---

## 7. What to tell a client

**Defensible claims:**
- Ingests arbitrary inventory formats without manual column mapping
- 100% precision on high-confidence matches in controlled testing
- Zero false matches against deliberate junk in controlled testing
- Every row carries an explicit confidence tier and full audit trail
- Identifies non-licensable components (runtimes, drivers, language packs)
  that would otherwise inflate product counts

**Do not claim:**
- Any accuracy figure on the client's own data before measuring it
- That output constitutes an Effective Licence Position
- That licence metrics are current without verification
- That the library is comprehensive
