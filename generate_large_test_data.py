"""
generate_large_test_data.py
Generates ~500 rows per input-format type, WITH ground-truth labels where
they can be stated honestly, so accuracy can be measured rather than guessed.

Design notes on honesty:
  - Ground truth is only recorded where it is genuinely knowable. A row derived
    from an executable path (sqlservr.exe) has a knowable product FAMILY but
    NOT a knowable edition - so its ground truth records family only, and
    scoring must not penalise the engine for failing to invent an edition.
  - "expected_resolvable" marks rows that SHOULD produce some answer. Deliberate
    junk rows are marked False - an engine that "resolves" them is wrong, not
    good. Measuring only the hit rate without this would reward over-matching.

Run: python3 generate_large_test_data.py
"""
import os
import random
import csv
import pandas as pd

random.seed(20260827)  # deterministic - reruns give identical data

OUT = "test_datasets_large"
os.makedirs(OUT, exist_ok=True)

lib = pd.read_csv("canonical_library.csv").fillna("")
real = lib[~lib["publisher"].str.startswith("(")]
N = 500

VENDOR_FORMS = {
    "Microsoft": ["Microsoft", "Microsoft Corporation", "Microsoft Corp.", "MICROSOFT CORPORATION", "Microsoft Inc"],
    "Oracle": ["Oracle", "Oracle Corporation", "Oracle America, Inc.", "ORACLE CORP", "Oracle Corp."],
    "IBM": ["IBM", "IBM Corporation", "International Business Machines", "IBM Corp.", "INTERNATIONAL BUSINESS MACHINES CORP"],
    "VMware (Broadcom)": ["VMware, Inc.", "VMware Inc", "Broadcom Inc", "Broadcom", "VMware by Broadcom", "VMWARE INC"],
    "Red Hat": ["Red Hat", "Red Hat, Inc.", "Red Hat Inc", "RedHat", "RED HAT INC"],
    "Adobe": ["Adobe", "Adobe Inc.", "Adobe Systems Incorporated", "Adobe Systems Inc", "ADOBE SYSTEMS INCORPORATED"],
    "SAP": ["SAP", "SAP SE", "SAP AG", "SAP America, Inc."],
    "Veritas (Cohesity)": ["Veritas", "Veritas Technologies LLC", "Cohesity", "Veritas Technologies"],
    "Citrix (Cloud Software Group)": ["Citrix", "Citrix Systems, Inc.", "Cloud Software Group", "Citrix Systems"],
}

ABBREV = [("Server", "Svr"), ("Standard", "Std"), ("Enterprise", "Ent"), ("Professional", "Prof"),
          ("Professional", "Pro"), ("Edition", "Ed"), ("Datacenter", "DC"), ("Database", "DB"),
          ("Microsoft", "MS"), ("Windows", "Win"), ("Subscription", "Subscrp"), ("Advanced", "Adv")]

JUNK = ["asdkjaslkdj123", "zzz-test-9999", "TEMP DELETE ME", "xxxxx", "1234567890", "!@#$%^&*()",
        "UNKNOWN - see notes", "TBD", "n/a", "REMOVED", "---", "test test test"]


def vendor_for(pub):
    return random.choice(VENDOR_FORMS.get(pub, [pub]))


def full_name(row):
    parts = [row["product_family"]]
    if row["edition"]:
        parts.append(row["edition"])
    if row["version"]:
        parts.append(str(row["version"]))
    return " ".join(str(p) for p in parts if p).strip()


def mangle(text, level):
    """level 0=clean 1=light 2=heavy"""
    if level == 0:
        return text
    out = text
    if level >= 1:
        for full, ab in random.sample(ABBREV, k=random.randint(1, 3)):
            out = out.replace(full, ab)
    if level >= 2:
        r = random.random()
        if r < 0.25:
            out = out.upper()
        elif r < 0.45:
            out = out.lower()
        elif r < 0.6:
            out = out.replace(" ", "")
        elif r < 0.75:
            out = "  " + out.replace(" ", "   ") + "  "
        elif r < 0.9:
            out = out + random.choice([" (x64)", " - DO NOT USE", " [DECOMMISSIONED]", " v2", " (2 CPU)", " - 2 Core Pack"])
    return out


def sample_rows(n):
    return [real.iloc[random.randint(0, len(real) - 1)] for _ in range(n)]


# ---------- 1. FLEXERA STYLE (clean, split columns) ----------
rows = []
for r in sample_rows(N - 20):
    rows.append([r["publisher"], r["product_family"], r["version"], r["edition"],
                 r["metric_type"], random.randint(1, 500), r["canonical_id"], True])
for _ in range(20):
    j = random.choice(JUNK)
    rows.append(["", j, "", "", "", random.randint(1, 5), "", False])
random.shuffle(rows)
pd.DataFrame(rows, columns=["Publisher", "Product Title", "Product Version", "Edition",
                            "License Metric", "Install Count", "_truth_canonical_id", "_expected_resolvable"]
             ).to_csv(f"{OUT}/L01_flexera_500.csv", index=False)


# ---------- 2. SERVICENOW STYLE ----------
rows = []
for i, r in enumerate(sample_rows(N - 20)):
    rows.append([f"host-{i:04d}", vendor_for(r["publisher"]),
                 f"{r['publisher']} {full_name(r)}".strip(),
                 r["version"] or f"{random.randint(1,20)}.{random.randint(0,9)}.{random.randint(0,99)}",
                 r["canonical_id"], True])
for i in range(20):
    rows.append([f"host-j{i:03d}", "Unknown Vendor", random.choice(JUNK), "1.0", "", False])
random.shuffle(rows)
pd.DataFrame(rows, columns=["display_name", "vendor", "software_name", "version",
                            "_truth_canonical_id", "_expected_resolvable"]
             ).to_csv(f"{OUT}/L02_servicenow_500.csv", index=False)


# ---------- 3. SCCM STYLE ----------
rows = []
for i, r in enumerate(sample_rows(N - 30)):
    nm = mangle(f"{r['publisher']} {full_name(r)}".strip(), random.choice([0, 0, 1]))
    rows.append([f"WKS-{i:05d}", vendor_for(r["publisher"]), nm,
                 f"{random.randint(1,25)}.{random.randint(0,9)}.{random.randint(1000,9999)}",
                 r["canonical_id"], True])
comps = lib[lib["publisher"] == "(Component)"]
for i in range(30):
    c = comps.iloc[random.randint(0, len(comps) - 1)]
    rows.append([f"WKS-C{i:04d}", "Microsoft Corporation", c["product_family"], "1.0", c["canonical_id"], True])
random.shuffle(rows)
pd.DataFrame(rows, columns=["ResourceName", "Publisher0", "DisplayName0", "DisplayVersion0",
                            "_truth_canonical_id", "_expected_resolvable"]
             ).to_csv(f"{OUT}/L03_sccm_500.csv", index=False)


# ---------- 4. RAW SCRIPT DUMP (tab separated) ----------
with open(f"{OUT}/L04_raw_script_500.txt", "w") as f:
    f.write("Host Name\tSerial\tIP Address\tName\tVendor\tVersion\tInstall Date\tInstall Location\t_truth_canonical_id\t_expected_resolvable\n")
    rows = []
    for i, r in enumerate(sample_rows(N)):
        nm = mangle(f"{r['publisher']} {full_name(r)}".strip(), random.choice([0, 0, 1, 2]))
        nm = nm.replace("\t", " ")
        rows.append([f"IN{i:08d}", f"S{i:07d}", f"10.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}",
                     nm, vendor_for(r["publisher"]), str(r["version"] or "1.0"),
                     f"2025{random.randint(10,12)}{random.randint(10,28)}",
                     f"C:\\Program Files\\{str(r['publisher']).split()[0]}\\", r["canonical_id"], "True"])
    random.shuffle(rows)
    for row in rows:
        f.write("\t".join(row) + "\n")


# ---------- 5. PATHS ONLY ----------
# Ground truth here is FAMILY-level only - an exe path cannot reveal edition.
EXE_MAP = [
    (r"C:\Program Files\Microsoft SQL Server\MSSQL{v}.MSSQLSERVER\MSSQL\Binn\sqlservr.exe", "SQL Server"),
    (r"C:\Program Files\Microsoft Office\root\Office16\{app}.EXE", "Office"),
    (r"C:\Program Files\Oracle\product\{v}.0.0\dbhome_1\bin\oracle.exe", "Database"),
    (r"C:\Program Files\Oracle\Middleware\Oracle_Home\wlserver\common\bin\startServer.cmd", "WebLogic Server"),
    (r"C:\Program Files (x86)\IBM\WebSphere\AppServer\bin\wsadmin.exe", "WebSphere Application Server"),
    (r"C:\Program Files\IBM\SQLLIB\BIN\db2syscs.exe", "Db2"),
    (r"C:\Program Files\Adobe\Acrobat DC\Acrobat\Acrobat.exe", "Acrobat"),
    (r"C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe", "Adobe Acrobat Reader"),
    (r"C:\Program Files\VMware\VMware Tools\vmtoolsd.exe", "VMware Tools"),
    (r"C:\Program Files\7-Zip\7zFM.exe", "7-Zip"),
    (r"C:\Program Files\Notepad++\notepad++.exe", "Notepad++"),
    (r"C:\Program Files\Google\Chrome\Application\chrome.exe", "Google Chrome"),
    (r"C:\Program Files\Microsoft Visual Studio\{y}\Professional\Common7\IDE\devenv.exe", "Visual Studio"),
    (r"/opt/oracle/product/19c/dbhome_1/bin/sqlplus", "Database"),
    (r"/opt/IBM/WebSphere/AppServer/bin/wsadmin.sh", "WebSphere Application Server"),
    (r"/usr/lib/jvm/java-11-openjdk/bin/java", "Java Runtime Environment"),
]
rows = []
for i in range(N - 15):
    tpl, fam = random.choice(EXE_MAP)
    p = tpl.format(v=random.choice([13, 14, 15, 16]), app=random.choice(["EXCEL", "WINWORD", "POWERPNT", "OUTLOOK"]),
                   y=random.choice([2019, 2022]))
    rows.append([f"SRV-{i:05d}", p, fam, True])
for i in range(15):
    rows.append([f"SRV-X{i:04d}", random.choice([r"C:\temp\unknown.exe", r"D:\stuff\app.exe", r"/tmp/x"]), "", False])
random.shuffle(rows)
pd.DataFrame(rows, columns=["Device", "Discovered Path", "_truth_family", "_expected_resolvable"]
             ).to_csv(f"{OUT}/L05_paths_500.csv", index=False)


# ---------- 6. UGLY MESSY (heavy mangling) ----------
rows = []
for r in sample_rows(N - 40):
    nm = mangle(f"{r['publisher']} {full_name(r)}".strip(), 2)
    rows.append([nm, random.randint(1, 900), r["canonical_id"], True])
for _ in range(40):
    rows.append([random.choice(JUNK + ["", " "]), random.randint(0, 3), "", False])
random.shuffle(rows)
pd.DataFrame(rows, columns=["raw_product_name", "qty", "_truth_canonical_id", "_expected_resolvable"]
             ).to_csv(f"{OUT}/L06_ugly_500.csv", index=False)


# ---------- 7. UNKNOWN PUBLISHERS (not in library - tests structural parse) ----------
UNKNOWN = [
    ("Bloomberg Terminal", "Bloomberg LP"), ("Refinitiv Eikon", "Refinitiv"),
    ("Epicor ERP 11", "Epicor Software"), ("Infor CloudSuite", "Infor"),
    ("Sage X3 Version 12", "Sage Group"), ("Blackbaud Raiser's Edge NXT", "Blackbaud"),
    ("Nuance Dragon Professional 16", "Nuance Communications"), ("Kofax Power PDF Advanced 5", "Tungsten Automation"),
    ("Bentley MicroStation 2023", "Bentley Systems"), ("Trimble SketchUp Pro 2024", "Trimble"),
    ("Unity Pro 2023.2", "Unity Technologies"), ("Unreal Engine 5.3", "Epic Games"),
    ("Rhino 7", "Robert McNeel & Associates"), ("Vectorworks Architect 2024", "Vectorworks Inc"),
    ("LabVIEW Professional 2024", "National Instruments"), ("Origin Pro 2024", "OriginLab"),
    ("Minitab Statistical Software 22", "Minitab LLC"), ("Stata SE 18", "StataCorp"),
    ("GraphPad Prism 10", "Dotmatics"), ("EndNote 21", "Clarivate"),
]
rows = []
for i in range(N):
    nm, vd = random.choice(UNKNOWN)
    rows.append([f"WKS-{i:05d}", mangle(nm, random.choice([0, 0, 1])), vd, "", True])
pd.DataFrame(rows, columns=["Host Name", "Name", "Vendor", "_truth_canonical_id", "_expected_resolvable"]
             ).to_csv(f"{OUT}/L07_unknown_pub_500.csv", index=False)


# ---------- 8. BAD COLUMN NAMES ----------
rows = []
for i, r in enumerate(sample_rows(N)):
    rows.append([f"n{i:05d}", str(r["publisher"]).split(" (")[0], f"{r['publisher']} {full_name(r)}".strip(),
                 str(r["version"] or "1.0"), r["canonical_id"], True])
pd.DataFrame(rows, columns=["col_a", "col_b", "col_c", "col_d", "_truth_canonical_id", "_expected_resolvable"]
             ).to_csv(f"{OUT}/L08_badcols_500.csv", index=False)


# ---------- 9. SEMICOLON DELIMITED ----------
with open(f"{OUT}/L09_semicolon_500.csv", "w") as f:
    f.write("Hostname;Hersteller;Softwarename;Version;_truth_canonical_id;_expected_resolvable\n")
    for i, r in enumerate(sample_rows(N)):
        nm = f"{r['publisher']} {full_name(r)}".strip().replace(";", ",")
        f.write(f"SRV-DE-{i:05d};{vendor_for(r['publisher'])};{nm};{r['version'] or '1.0'};{r['canonical_id']};True\n")


# ---------- 10. TIER-1 PUBLISHERS ONLY ----------
TIER1 = ["Microsoft", "Oracle", "IBM", "VMware (Broadcom)", "Red Hat", "Adobe", "Veritas (Cohesity)"]
t1 = lib[lib["publisher"].isin(TIER1)]
rows = []
for i in range(N):
    r = t1.iloc[random.randint(0, len(t1) - 1)]
    nm = mangle(f"{r['publisher']} {full_name(r)}".strip(), random.choice([0, 0, 0, 1]))
    rows.append([f"SRV-{i:05d}", nm, vendor_for(r["publisher"]), str(r["version"] or ""), r["canonical_id"], True])
pd.DataFrame(rows, columns=["Host Name", "Name", "Vendor", "Version", "_truth_canonical_id", "_expected_resolvable"]
             ).to_csv(f"{OUT}/L10_tier1_500.csv", index=False)


# ---------- 11. EXCEL ----------
pd.read_csv(f"{OUT}/L10_tier1_500.csv").to_excel(f"{OUT}/L11_excel_500.xlsx", index=False, sheet_name="Deployments")


# ---------- 12. EDGE CASES ----------
rows = []
base = sample_rows(N // 2)
for i, r in enumerate(base):
    nm = f"{r['publisher']} {full_name(r)}".strip()
    variants = [nm, nm.upper(), nm.lower(), "   " + nm.replace(" ", "   ") + "   ",
                nm + " (Español)", nm + " " * 20, nm.replace(" ", "\u00a0")]
    rows.append([f"E-{i:05d}", random.choice(variants), vendor_for(r["publisher"]), r["canonical_id"], True])
for i in range(60):
    rows.append([f"E-J{i:04d}", random.choice(JUNK), "Vendor", "", False])
for i in range(40):
    rows.append([f"E-B{i:04d}", "", vendor_for("Microsoft"), "", False])
for i in range(20):
    rows.append([f"E-L{i:04d}", "A" * random.randint(200, 400), "Unknown", "", False])
dupe = rows[0]
for _ in range(30):
    rows.append(list(dupe))
random.shuffle(rows)
pd.DataFrame(rows, columns=["Host", "Name", "Vendor", "_truth_canonical_id", "_expected_resolvable"]
             ).to_csv(f"{OUT}/L12_edge_500.csv", index=False)


print(f"Generated large test datasets in ./{OUT}/\n")
total = 0
for fn in sorted(os.listdir(OUT)):
    path = os.path.join(OUT, fn)
    try:
        n = len(pd.read_excel(path)) if fn.endswith("xlsx") else sum(1 for _ in open(path)) - 1
    except Exception:
        n = "?"
    total += n if isinstance(n, int) else 0
    print(f"  {fn:<32} {n:>5} rows")
print(f"\n  TOTAL: {total} rows")
