"""
benchmark.py
Scores the normalizer against ground-truth labels across ~5,900 rows.

This is what turns "it seems to work" into a defensible reliability claim.

METRICS - and why each one matters:
  Coverage    - % of rows that produced ANY answer (not UNRESOLVED).
                High coverage alone is NOT good: an engine that matches
                everything to something scores 100% here while being useless.
  Precision   - of rows that got a LIBRARY match, % where that match was the
                CORRECT canonical_id. This is the number that matters most for
                ELP work: a wrong confident match is worse than no match.
  False-match - % of deliberate junk rows that got a library match anyway.
                Should be near zero. This is the check that stops the engine
                from being rewarded for over-matching.
  By tier     - precision broken out by EXACT/HIGH/REVIEW/PARSED so you can
                state, defensibly, which tiers a reviewer can trust.

Run: python3 benchmark.py
"""
import os
import warnings
import pandas as pd

warnings.filterwarnings("ignore")

from normalizer import ProductNormalizer, BACKEND
from schema_detect import sniff_and_load, detect_schema
from inventory_import import classify_inventory

DATA_DIR = "test_datasets_large"
TRUTH_ID = "_truth_canonical_id"
TRUTH_FAM = "_truth_family"
EXPECTED = "_expected_resolvable"


def evaluate(fn, norm):
    path = os.path.join(DATA_DIR, fn)
    df = sniff_and_load(path)

    truth_id = df[TRUTH_ID].fillna("").astype(str) if TRUTH_ID in df.columns else None
    truth_fam = df[TRUTH_FAM].fillna("").astype(str) if TRUTH_FAM in df.columns else None
    expected = df[EXPECTED].astype(str).str.lower().isin(["true", "1"]) if EXPECTED in df.columns else None

    work = df[[c for c in df.columns if not c.startswith("_")]]
    schema = detect_schema(work)
    pcol = schema["product"]["column"]
    if not pcol:
        return {"file": fn, "rows": len(df), "error": "no product column detected"}

    res = classify_inventory(
        work, norm,
        name_col=pcol,
        vendor_col=schema["vendor"]["column"] or pcol,
        version_col=schema["version"]["column"] or pcol,
        host_col=schema["host"]["column"] or pcol,
        edition_col=schema["edition"]["column"],
    )

    n = len(res)
    tier = res["confidence_tier"]
    got_answer = tier != "UNRESOLVED"
    got_library = res["canonical_id"].notna() & (res["canonical_id"].astype(str) != "")

    out = {
        "file": fn, "rows": n,
        "coverage": got_answer.mean() * 100,
        "library_matched": got_library.mean() * 100,
    }

    # ---- Precision against ground truth ----
    if truth_id is not None:
        has_truth = truth_id != ""
        scoreable = has_truth & got_library
        if scoreable.sum() > 0:
            correct = (res.loc[scoreable, "canonical_id"].astype(str).values == truth_id[scoreable].values)
            out["precision"] = correct.mean() * 100
            out["scored_n"] = int(scoreable.sum())
            # precision per tier
            for t in ["EXACT", "HIGH", "REVIEW"]:
                m = scoreable & (tier == t)
                if m.sum() > 0:
                    c = (res.loc[m, "canonical_id"].astype(str).values == truth_id[m].values)
                    out[f"prec_{t}"] = c.mean() * 100
                    out[f"n_{t}"] = int(m.sum())

    elif truth_fam is not None:
        has_truth = truth_fam != ""
        m = has_truth & res["product_family"].notna()
        if m.sum() > 0:
            got = res.loc[m, "product_family"].astype(str).str.lower()
            want = truth_fam[m].str.lower()
            out["precision"] = (got.values == want.values).mean() * 100
            out["scored_n"] = int(m.sum())

    # ---- False-match rate on deliberate junk ----
    if expected is not None and (~expected).sum() > 0:
        junk = ~expected
        out["junk_n"] = int(junk.sum())
        out["false_match"] = (got_library & junk).mean() / junk.mean() * 100

    return out


def main():
    norm = ProductNormalizer("canonical_library.csv")
    print(f"Library: {len(norm.lib)} products, {norm.lib['publisher'].nunique()} publishers")
    print(f"Backend: {BACKEND}\n")

    files = sorted(f for f in os.listdir(DATA_DIR) if not f.startswith("."))
    results = [evaluate(f, norm) for f in files]

    print(f'{"FILE":<28} {"ROWS":>5} {"COVER":>7} {"LIB%":>7} {"PREC":>7} {"FALSE+":>7}')
    print("-" * 70)
    for r in results:
        if "error" in r:
            print(f'{r["file"]:<28} {r["rows"]:>5}   ERROR: {r["error"]}')
            continue
        prec = f'{r["precision"]:.1f}%' if "precision" in r else "n/a"
        fm = f'{r["false_match"]:.1f}%' if "false_match" in r else "n/a"
        print(f'{r["file"]:<28} {r["rows"]:>5} {r["coverage"]:>6.1f}% {r["library_matched"]:>6.1f}% {prec:>7} {fm:>7}')

    print("\n" + "=" * 70)
    print("PRECISION BY CONFIDENCE TIER (across all files with ground truth)")
    print("=" * 70)
    for t in ["EXACT", "HIGH", "REVIEW"]:
        tot_n = sum(r.get(f"n_{t}", 0) for r in results)
        if tot_n:
            weighted = sum(r.get(f"prec_{t}", 0) * r.get(f"n_{t}", 0) for r in results) / tot_n
            print(f"  {t:<8} {weighted:>6.1f}% correct   (n={tot_n})")

    tot_rows = sum(r.get("rows", 0) for r in results)
    tot_scored = sum(r.get("scored_n", 0) for r in results)
    if tot_scored:
        wp = sum(r.get("precision", 0) * r.get("scored_n", 0) for r in results) / tot_scored
        print(f"\n  OVERALL PRECISION: {wp:.1f}% (n={tot_scored} scoreable rows of {tot_rows} total)")

    tot_junk = sum(r.get("junk_n", 0) for r in results)
    if tot_junk:
        wf = sum(r.get("false_match", 0) * r.get("junk_n", 0) for r in results) / tot_junk
        print(f"  FALSE-MATCH ON JUNK: {wf:.1f}% (n={tot_junk} deliberate junk rows)")

    print("\nRead these together: coverage without precision means over-matching.")


if __name__ == "__main__":
    main()
