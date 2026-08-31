"""
run_tests.py
Benchmark the normalizer across every test dataset.

  python3 run_tests.py            # summary table
  python3 run_tests.py --detail   # per-row results for every file
  python3 run_tests.py 05         # detail for one file (matched by prefix)

Use this after ANY change to the matching logic or canonical library - it's
how you catch a regression (a change that improves one case while quietly
breaking another) before it reaches a client engagement.
"""
import os
import sys
import warnings
import pandas as pd

warnings.filterwarnings("ignore")

from normalizer import ProductNormalizer, BACKEND
from schema_detect import sniff_and_load, detect_schema
from inventory_import import classify_inventory

DATA_DIR = "test_datasets"
LIBRARY = "canonical_library.csv"


def run_one(path, normalizer):
    df = sniff_and_load(path)
    schema = detect_schema(df)
    pcol = schema["product"]["column"]
    if not pcol:
        return None, schema, "no product column detected"
    res = classify_inventory(
        df, normalizer,
        name_col=pcol,
        vendor_col=schema["vendor"]["column"] or pcol,
        version_col=schema["version"]["column"] or pcol,
        host_col=schema["host"]["column"] or pcol,
        edition_col=schema["edition"]["column"],
    )
    return res, schema, None


def main():
    args = [a for a in sys.argv[1:]]
    detail = "--detail" in args
    prefix = next((a for a in args if not a.startswith("--")), None)

    norm = ProductNormalizer(LIBRARY)
    print(f"Library: {len(norm.lib)} products  |  Matching backend: {BACKEND}\n")

    files = sorted(f for f in os.listdir(DATA_DIR) if not f.startswith("."))
    if prefix:
        files = [f for f in files if f.startswith(prefix)]
        detail = True

    tot_rows = tot_res = tot_strong = 0
    print(f'{"FILE":<32} {"ROWS":>5} {"RES%":>6} {"STRONG%":>8}  TIERS')
    print("-" * 104)

    for fn in files:
        res, schema, err = run_one(os.path.join(DATA_DIR, fn), norm)
        if err:
            print(f"{fn:<32} {'--':>5}  !! {err}")
            continue

        n_res = (res["confidence_tier"] != "UNRESOLVED").sum()
        n_strong = res["confidence_tier"].isin(["EXACT", "HIGH"]).sum()
        tot_rows += len(res)
        tot_res += n_res
        tot_strong += n_strong
        tiers = " ".join(f"{k}:{v}" for k, v in res["confidence_tier"].value_counts().items())
        print(f"{fn:<32} {len(res):>5} {n_res/len(res)*100:>5.0f}% {n_strong/len(res)*100:>7.0f}%  {tiers}")

        if detail:
            print("\n  Detected schema:")
            for role, info in schema.items():
                if info["column"]:
                    print(f"    {role:9} -> {info['column']:22} ({info['confidence']}% via {info['basis']})")
            print()
            pd.set_option("display.max_colwidth", 40)
            pd.set_option("display.width", 220)
            cols = ["raw_input", "confidence_tier", "match_score", "publisher",
                    "product_family", "edition", "version", "metric_type"]
            cols = [c for c in cols if c in res.columns]
            print(res[cols].to_string(index=False))
            print("\n" + "=" * 104 + "\n")

    if not detail and tot_rows:
        print("-" * 104)
        print(f"OVERALL: {tot_res}/{tot_rows} resolved ({tot_res/tot_rows*100:.1f}%)  |  "
              f"{tot_strong} strong EXACT/HIGH ({tot_strong/tot_rows*100:.1f}%)")
        print("\nTiers: EXACT/HIGH = trust it | REVIEW = confirm it | "
              "PARSED = identified but not in library (no license metric) | UNRESOLVED = classify manually")


if __name__ == "__main__":
    main()
