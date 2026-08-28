"""
build_library.py
Generates the expanded canonical product library.

Kept as a SCRIPT rather than a hand-edited CSV so the library is reproducible,
reviewable in diffs, and easy to extend publisher-by-publisher.

Accuracy note: license metrics are recorded at the level of confidence that is
actually defensible. Where a publisher's metric is well documented and stable
(IBM PVU, Oracle NUP/Processor, RHEL socket-pair) it is stated plainly. Where
a model changed recently or varies by contract, that is stated in the metric
text rather than silently simplified - a metric field that looks precise but
isn't is worse than one that names its own uncertainty.

Run: python3 build_library.py
"""
import csv

# (canonical_id, publisher, family, edition, version, metric, aliases[list])
P = []


def add(cid, pub, fam, ed, ver, metric, aliases):
    P.append((cid, pub, fam, ed, ver, metric, "|".join(aliases)))


# ============================== MICROSOFT ==============================
MS_CORE = "Per Core (2-core pack; 8 core/proc & 16 core/server min)"
for yr in ["2012", "2012 R2", "2016", "2019", "2022", "2025"]:
    slug = yr.replace(" ", "").upper()
    add(f"MS-WINSVR-STD-{slug}", "Microsoft", "Windows Server", "Standard", yr, MS_CORE,
        [f"Windows Server {yr} Standard", f"Windows Server Std {yr}", f"Win Svr Std {yr}", f"WINSVRSTD{slug}"])
    add(f"MS-WINSVR-DC-{slug}", "Microsoft", "Windows Server", "Datacenter", yr,
        "Per Core (2-core pack; unlimited virtualization rights)",
        [f"Windows Server {yr} Datacenter", f"Windows Server DC {yr}", f"Win Svr DC {yr}", f"WINSVRDC{slug}"])

for yr in ["2012", "2014", "2016", "2017", "2019", "2022"]:
    add(f"MS-SQL-STD-{yr}", "Microsoft", "SQL Server", "Standard", yr,
        "Per Core (2-core pack) or Server+CAL",
        [f"SQL Server {yr} Standard", f"SQL Svr Std {yr}", f"Microsoft SQL Server {yr} Standard Edition", f"SQLSVRSTD{yr}"])
    add(f"MS-SQL-ENT-{yr}", "Microsoft", "SQL Server", "Enterprise", yr,
        "Per Core (2-core pack only)",
        [f"SQL Server {yr} Enterprise", f"SQL Svr Ent {yr}", f"Microsoft SQL Server {yr} Enterprise Edition", f"SQLSVRENT{yr}"])
add("MS-SQL-WEB", "Microsoft", "SQL Server", "Web", "", "Per Core (hosting only)", ["SQL Server Web Edition", "SQL Svr Web"])
add("MS-SQL-DEV", "Microsoft", "SQL Server", "Developer", "", "Free (non-production use only)", ["SQL Server Developer Edition", "SQL Svr Dev"])
add("MS-SQL-EXPRESS", "Microsoft", "SQL Server", "Express", "", "Free (no license required)", ["SQL Server Express", "SQLEXPRESS", "SQL Svr Express"])
add("MS-SQL-CAL", "Microsoft", "SQL Server", "Client Access License", "", "Per User or Per Device", ["SQL Server CAL", "SQL CAL"])

for w in ["7", "8.1", "10", "11"]:
    add(f"MS-WIN{w.replace('.','')}-PRO", "Microsoft", f"Windows {w}", "Pro", "", "Per Device (OEM or Volume License)",
        [f"Windows {w} Pro", f"Windows {w} Professional", f"Win{w} Pro"])
    add(f"MS-WIN{w.replace('.','')}-ENT", "Microsoft", f"Windows {w}", "Enterprise", "", "Per Device (VL or M365 entitlement)",
        [f"Windows {w} Enterprise", f"Win{w} Ent"])

for tier in ["E1", "E3", "E5", "F1", "F3"]:
    add(f"MS-M365-{tier}", "Microsoft", "Microsoft 365", tier, "", "Per User Subscription",
        [f"Microsoft 365 {tier}", f"M365 {tier}", f"O365 {tier}", f"Office 365 {tier}"])
for tier in ["Business Basic", "Business Standard", "Business Premium", "Apps for enterprise", "Apps for business"]:
    slug = tier.upper().replace(" ", "-")
    add(f"MS-M365-{slug}", "Microsoft", "Microsoft 365", tier, "", "Per User Subscription",
        [f"Microsoft 365 {tier}", f"M365 {tier}"])

for yr in ["2013", "2016", "2019", "2021", "2024"]:
    add(f"MS-OFFICE-STD-{yr}", "Microsoft", "Office", "Standard", yr, "Per Device", [f"Office Standard {yr}", f"Office Std {yr}", f"OFFSTD{yr}"])
    add(f"MS-OFFICE-PROPLUS-{yr}", "Microsoft", "Office", "Professional Plus", yr, "Per Device",
        [f"Office Professional Plus {yr}", f"Office Pro Plus {yr}", f"OFFPROPLUS{yr}"])
add("MS-OFFICE-LTSC-2021", "Microsoft", "Office", "LTSC Standard", "2021", "Per Device", ["Office LTSC 2021", "Office LTSC Standard 2021"])
add("MS-OFFICE-LTSC-2024", "Microsoft", "Office", "LTSC Standard", "2024", "Per Device", ["Office LTSC 2024", "Office LTSC Standard 2024"])

add("MS-EXCH-STD", "Microsoft", "Exchange Server", "Standard", "", "Server + CAL", ["Exchange Server Standard", "Exch Svr Std", "EXCHSVRSTD"])
add("MS-EXCH-ENT", "Microsoft", "Exchange Server", "Enterprise", "", "Server + CAL", ["Exchange Server Enterprise", "Exch Svr Ent", "EXCHSVRENT"])
add("MS-EXCH-CAL-STD", "Microsoft", "Exchange Server", "Standard CAL", "", "Per User or Per Device", ["Exchange Standard CAL", "Exch Std CAL"])
add("MS-EXCH-CAL-ENT", "Microsoft", "Exchange Server", "Enterprise CAL", "", "Per User or Per Device (additive to Standard CAL)", ["Exchange Enterprise CAL", "Exch Ent CAL"])
add("MS-SP-STD", "Microsoft", "SharePoint Server", "Standard", "", "Server + CAL", ["SharePoint Server Standard", "SP Svr Std"])
add("MS-SP-ENT", "Microsoft", "SharePoint Server", "Enterprise", "", "Server + CAL", ["SharePoint Server Enterprise", "SP Svr Ent"])
add("MS-SKYPE-SVR", "Microsoft", "Skype for Business Server", "", "", "Server + CAL", ["Skype for Business Server", "Lync Server"])
add("MS-PROJECT-STD", "Microsoft", "Project", "Standard", "", "Per Device", ["Project Standard", "MS Project Standard", "Project Std"])
add("MS-PROJECT-PRO", "Microsoft", "Project", "Professional", "", "Per Device or Per User Subscription", ["Project Professional", "MS Project Professional", "Project Pro"])
add("MS-PROJECT-P1", "Microsoft", "Project", "Plan 1", "", "Per User Subscription", ["Project Plan 1", "Project Online Essentials"])
add("MS-PROJECT-P3", "Microsoft", "Project", "Plan 3", "", "Per User Subscription", ["Project Plan 3", "Project Online Professional"])
add("MS-PROJECT-P5", "Microsoft", "Project", "Plan 5", "", "Per User Subscription", ["Project Plan 5", "Project Online Premium"])
add("MS-VISIO-STD", "Microsoft", "Visio", "Standard", "", "Per Device", ["Visio Standard", "MS Visio Standard", "Visio Std"])
add("MS-VISIO-PRO", "Microsoft", "Visio", "Professional", "", "Per Device", ["Visio Professional", "MS Visio Professional", "Visio Pro"])
add("MS-VISIO-P1", "Microsoft", "Visio", "Plan 1", "", "Per User Subscription", ["Visio Plan 1"])
add("MS-VISIO-P2", "Microsoft", "Visio", "Plan 2", "", "Per User Subscription", ["Visio Plan 2"])

for prod, met in [("Sales Professional", "Per User Subscription"), ("Sales Enterprise", "Per User Subscription"),
                  ("Customer Service Professional", "Per User Subscription"), ("Customer Service Enterprise", "Per User Subscription"),
                  ("Field Service", "Per User Subscription"), ("Finance", "Per User Subscription"),
                  ("Supply Chain Management", "Per User Subscription"), ("Business Central Essentials", "Per User Subscription"),
                  ("Business Central Premium", "Per User Subscription"), ("Project Operations", "Per User Subscription")]:
    slug = prod.upper().replace(" ", "-")
    add(f"MS-DYN365-{slug}", "Microsoft", "Dynamics 365", prod, "", met, [f"Dynamics 365 {prod}", f"Dyn365 {prod}"])

add("MS-PBI-PRO", "Microsoft", "Power BI", "Pro", "", "Per User Subscription", ["Power BI Pro", "PBI Pro"])
add("MS-PBI-PPU", "Microsoft", "Power BI", "Premium Per User", "", "Per User Subscription", ["Power BI Premium Per User", "PBI PPU"])
add("MS-PBI-CAPACITY", "Microsoft", "Power BI", "Premium Capacity", "", "Per Capacity (P/F SKU) Subscription", ["Power BI Premium", "Power BI Premium Capacity"])
add("MS-POWERAPPS", "Microsoft", "Power Apps", "", "", "Per User or Per App Subscription", ["Power Apps", "PowerApps", "Microsoft Power Apps"])
add("MS-POWERAUTOMATE", "Microsoft", "Power Automate", "", "", "Per User or Per Flow Subscription", ["Power Automate", "Microsoft Flow"])
add("MS-VS-PRO", "Microsoft", "Visual Studio", "Professional", "", "Per User Subscription", ["Visual Studio Professional", "VS Professional"])
add("MS-VS-ENT", "Microsoft", "Visual Studio", "Enterprise", "", "Per User Subscription", ["Visual Studio Enterprise", "VS Enterprise"])
add("MS-VSCODE", "Microsoft", "Visual Studio Code", "", "", "Free (no license required)", ["Visual Studio Code", "VS Code", "VSCode"])
add("MS-SYSCTR-STD", "Microsoft", "System Center", "Standard", "", "Per Core (2-core pack)", ["System Center Standard", "SysCtr Std"])
add("MS-SYSCTR-DC", "Microsoft", "System Center", "Datacenter", "", "Per Core (2-core pack)", ["System Center Datacenter", "SysCtr DC"])
add("MS-BIZTALK-STD", "Microsoft", "BizTalk Server", "Standard", "", "Per Core (2-core pack)", ["BizTalk Server Standard", "BizTalk Std"])
add("MS-BIZTALK-ENT", "Microsoft", "BizTalk Server", "Enterprise", "", "Per Core (2-core pack)", ["BizTalk Server Enterprise", "BizTalk Ent"])
add("MS-AZURE-DEVOPS", "Microsoft", "Azure DevOps Server", "", "", "Server + CAL or Per User Subscription", ["Azure DevOps Server", "Team Foundation Server", "TFS"])
add("MS-DEFENDER-EP", "Microsoft", "Defender for Endpoint", "", "", "Per User or Per Device Subscription", ["Defender for Endpoint", "Microsoft Defender for Endpoint", "MDE"])
add("MS-INTUNE", "Microsoft", "Intune", "", "", "Per User Subscription", ["Microsoft Intune", "Intune", "Endpoint Manager"])
add("MS-ENTRA-P1", "Microsoft", "Entra ID", "P1", "", "Per User Subscription", ["Entra ID P1", "Azure AD Premium P1", "Azure Active Directory Premium P1"])
add("MS-ENTRA-P2", "Microsoft", "Entra ID", "P2", "", "Per User Subscription", ["Entra ID P2", "Azure AD Premium P2"])
add("MS-COPILOT-M365", "Microsoft", "365 Copilot", "", "", "Per User Subscription (add-on)", ["Microsoft 365 Copilot", "M365 Copilot", "Copilot for Microsoft 365"])
add("MS-TEAMS-PHONE", "Microsoft", "Teams Phone", "", "", "Per User Subscription", ["Teams Phone", "Microsoft Teams Phone", "Phone System"])
add("MS-RDS-CAL", "Microsoft", "Remote Desktop Services", "CAL", "", "Per User or Per Device CAL", ["RDS CAL", "Remote Desktop Services CAL", "Terminal Server CAL"])

# ============================== ORACLE ==============================
ORA_DB = "Named User Plus (min 25 NUP/proc for EE) or Processor (core factor applies)"
for v in ["11g", "12c", "18c", "19c", "21c", "23ai"]:
    add(f"ORACLE-DB-EE-{v.upper()}", "Oracle", "Database", "Enterprise Edition", v, ORA_DB,
        [f"Oracle Database {v} Enterprise Edition", f"Oracle DB EE {v}", f"Oracle Database Enterprise Edition {v}"])
add("ORACLE-DB-SE2", "Oracle", "Database", "Standard Edition 2", "", "Named User Plus (min 10 NUP/server) or Socket (max 2 sockets)",
    ["Oracle Database Standard Edition 2", "Oracle DB SE2", "ORACLEDBSE2"])
add("ORACLE-DB-SE", "Oracle", "Database", "Standard Edition", "", "Named User Plus or Socket (legacy - superseded by SE2)",
    ["Oracle Database Standard Edition", "Oracle DB SE"])
add("ORACLE-DB-XE", "Oracle", "Database", "Express Edition", "", "Free (resource-limited; no license required)",
    ["Oracle Database Express Edition", "Oracle DB XE", "Oracle XE"])
add("ORACLE-DB-PERSONAL", "Oracle", "Database", "Personal Edition", "", "Named User Plus (single user)", ["Oracle Database Personal Edition"])

for opt, met in [("Real Application Clusters", ORA_DB), ("Partitioning", ORA_DB), ("Advanced Security", ORA_DB),
                 ("Advanced Compression", ORA_DB), ("Active Data Guard", ORA_DB), ("In-Memory Database", ORA_DB),
                 ("Multitenant", ORA_DB), ("Spatial and Graph", ORA_DB), ("OLAP", ORA_DB), ("Label Security", ORA_DB)]:
    slug = opt.upper().replace(" ", "-")
    add(f"ORACLE-OPT-{slug}", "Oracle", opt, "", "", met + " [EE option - requires Database EE]",
        [f"Oracle {opt}", opt])
for pack in ["Diagnostics Pack", "Tuning Pack", "Database Lifecycle Management Pack", "Data Masking and Subsetting Pack"]:
    slug = pack.upper().replace(" ", "-")
    add(f"ORACLE-PACK-{slug}", "Oracle", pack, "", "", ORA_DB + " [EE management pack]", [f"Oracle {pack}", pack])

add("ORACLE-WLS-STD", "Oracle", "WebLogic Server", "Standard Edition", "", "Socket (physical CPU sockets)",
    ["Oracle WebLogic Server Standard Edition", "WebLogic SE", "Oracle WebLogic SE"])
add("ORACLE-WLS-ENT", "Oracle", "WebLogic Server", "Enterprise Edition", "", "Processor (core factor applies) or Named User Plus",
    ["Oracle WebLogic Server Enterprise Edition", "WebLogic EE", "Oracle WebLogic EE"])
add("ORACLE-WLS-SUITE", "Oracle", "WebLogic Server", "Suite", "", "Processor (core factor applies)",
    ["Oracle WebLogic Suite", "WebLogic Suite"])
add("ORACLE-SOA", "Oracle", "SOA Suite", "", "", "Processor (core factor applies)", ["Oracle SOA Suite", "SOA Suite"])
add("ORACLE-JAVA-SE", "Oracle", "Java SE", "Universal Subscription", "", "Per Employee (total employee count, not installs)",
    ["Oracle Java SE Universal Subscription", "Java SE Subscription", "Oracle Java SE"])
add("ORACLE-JDK", "Oracle", "JDK", "", "", "Free under NFTC for recent versions; older versions may require subscription",
    ["Oracle JDK", "Java Development Kit", "Oracle Java Development Kit"])
add("ORACLE-EBS", "Oracle", "E-Business Suite", "", "", "Application User or Named User Plus", ["Oracle E-Business Suite", "Oracle EBS"])
add("ORACLE-PRIMAVERA", "Oracle", "Primavera P6", "", "", "Named User Plus or Application User", ["Oracle Primavera P6", "Primavera P6", "Primavera"])
add("ORACLE-PEOPLESOFT", "Oracle", "PeopleSoft", "", "", "Application User or Employee metric", ["Oracle PeopleSoft", "PeopleSoft"])
add("ORACLE-SIEBEL", "Oracle", "Siebel CRM", "", "", "Application User", ["Oracle Siebel", "Siebel CRM", "Siebel"])
add("ORACLE-GOLDENGATE", "Oracle", "GoldenGate", "", "", "Processor (core factor applies) or Named User Plus", ["Oracle GoldenGate", "GoldenGate"])
add("ORACLE-VIRTUALBOX", "Oracle", "VM VirtualBox", "", "", "Base package free; Extension Pack requires license for commercial use",
    ["Oracle VM VirtualBox", "VirtualBox", "Oracle VirtualBox"])
add("ORACLE-MYSQL-ENT", "Oracle", "MySQL", "Enterprise Edition", "", "Per Server Subscription", ["MySQL Enterprise Edition", "MySQL Enterprise"])
add("ORACLE-MYSQL-CE", "Oracle", "MySQL", "Community Edition", "", "Free (GPL; no license required)", ["MySQL Community Edition", "MySQL Community", "MySQL Server"])

# ============================== IBM ==============================
add("IBM-DB2-COMMUNITY", "IBM", "Db2", "Community Edition", "", "Free (resource-limited; no license required)", ["Db2 Community Edition", "IBM Db2 Community"])
add("IBM-DB2-STD", "IBM", "Db2", "Standard Edition", "", "PVU or Virtual Processor Core (VPC)", ["Db2 Standard Edition", "IBM Db2 Standard", "Db2 SE"])
add("IBM-DB2-AE", "IBM", "Db2", "Advanced Edition", "", "PVU or Virtual Processor Core (VPC)", ["Db2 Advanced Edition", "IBM Db2 Advanced", "Db2 AE"])
add("IBM-DB2-AESE", "IBM", "Db2", "Advanced Enterprise Server Edition", "", "PVU (sub-capacity requires ILMT)", ["Db2 AESE", "IBM Db2 Advanced Enterprise Server Edition"])
add("IBM-DB2-AWSE", "IBM", "Db2", "Advanced Workgroup Server Edition", "", "PVU (sub-capacity requires ILMT)", ["Db2 AWSE", "IBM Db2 Advanced Workgroup Server Edition"])
add("IBM-WAS-BASE", "IBM", "WebSphere Application Server", "Base", "", "PVU (sub-capacity requires ILMT)", ["WebSphere Application Server Base", "WAS Base", "IBM WebSphere Application Server"])
add("IBM-WAS-ND", "IBM", "WebSphere Application Server", "Network Deployment", "", "PVU (sub-capacity requires ILMT)", ["WebSphere ND", "WAS ND", "IBM WebSphere Application Server Network Deployment"])
add("IBM-WAS-LIBERTY", "IBM", "WebSphere Application Server", "Liberty", "", "PVU or VPC", ["WebSphere Liberty", "WAS Liberty", "Open Liberty"])
add("IBM-WAS-EXPRESS", "IBM", "WebSphere Application Server", "Express", "", "PVU", ["WebSphere Application Server Express", "WAS Express"])
add("IBM-MQ", "IBM", "MQ", "", "", "PVU or VPC", ["IBM MQ", "WebSphere MQ", "MQSeries"])
add("IBM-MQ-ADV", "IBM", "MQ", "Advanced", "", "PVU or VPC", ["IBM MQ Advanced", "MQ Advanced"])
add("IBM-INFORMIX", "IBM", "Informix", "", "", "PVU or Authorized User Single Install", ["IBM Informix", "Informix Dynamic Server", "Informix"])
add("IBM-SPSS-STATS", "IBM", "SPSS Statistics", "", "", "Authorized User or Concurrent User", ["IBM SPSS Statistics", "SPSS Statistics", "SPSS"])
add("IBM-SPSS-MODELER", "IBM", "SPSS Modeler", "", "", "Authorized User or Concurrent User", ["IBM SPSS Modeler", "SPSS Modeler"])
add("IBM-COGNOS", "IBM", "Cognos Analytics", "", "", "Authorized User, Concurrent User, or PVU", ["IBM Cognos Analytics", "Cognos Analytics", "Cognos"])
add("IBM-MAXIMO", "IBM", "Maximo", "", "", "Authorized User, Concurrent User, or App Points", ["IBM Maximo", "Maximo Asset Management", "Maximo"])
add("IBM-BIGFIX", "IBM", "BigFix", "", "", "Per Client Device or Managed Virtual Server", ["IBM BigFix", "BigFix Inventory", "BigFix Platform"])
add("IBM-ILMT", "IBM", "License Metric Tool", "", "", "No charge (required for IBM sub-capacity PVU licensing)", ["IBM License Metric Tool", "ILMT"])
add("IBM-TIVOLI-MON", "IBM", "Tivoli Monitoring", "", "", "PVU or Resource Value Unit (RVU)", ["IBM Tivoli Monitoring", "Tivoli Monitoring", "ITM"])
add("IBM-TIVOLI-STORAGE", "IBM", "Storage Protect (Tivoli Storage Manager)", "", "", "PVU, Terabyte, or Front-End capacity",
    ["IBM Storage Protect", "Tivoli Storage Manager", "TSM", "IBM Spectrum Protect"])
add("IBM-DATASTAGE", "IBM", "DataStage", "", "", "PVU or Virtual Processor Core", ["IBM DataStage", "InfoSphere DataStage", "DataStage"])
add("IBM-API-CONNECT", "IBM", "API Connect", "", "", "Virtual Processor Core (VPC)", ["IBM API Connect", "API Connect"])
add("IBM-DATAPOWER", "IBM", "DataPower Gateway", "", "", "PVU or Appliance", ["IBM DataPower", "DataPower Gateway", "DataPower"])
add("IBM-CONTROL-DESK", "IBM", "Control Desk", "", "", "Authorized User or Concurrent User", ["IBM Control Desk", "Control Desk"])
add("IBM-RATIONAL-CC", "IBM", "Rational ClearCase", "", "", "Authorized User or Floating User", ["IBM Rational ClearCase", "Rational ClearCase", "ClearCase"])
add("IBM-RATIONAL-DOORS", "IBM", "Rational DOORS", "", "", "Authorized User or Floating User", ["IBM Rational DOORS", "Rational DOORS", "DOORS"])
add("IBM-PLANNING-ANALYTICS", "IBM", "Planning Analytics", "", "", "Authorized User or PVU", ["IBM Planning Analytics", "Planning Analytics", "TM1"])
add("IBM-WATSONX", "IBM", "watsonx", "", "", "Resource Unit or Subscription", ["IBM watsonx", "watsonx.ai", "watsonx"])
add("IBM-AIX", "IBM", "AIX", "", "", "Per Processor Core (by machine tier)", ["IBM AIX", "AIX Operating System", "AIX"])
add("IBM-ZOS", "IBM", "z/OS", "", "", "MSU (Millions of Service Units) / MLC or OTC", ["IBM z/OS", "z/OS"])

# ============================== VMWARE (BROADCOM) ==============================
VMW_CORE = "Per Core Subscription (16-core minimum per CPU; subscription only since 2024)"
add("VMWARE-VCF", "VMware (Broadcom)", "Cloud Foundation (VCF)", "", "", VMW_CORE + " - full stack bundle incl. vSAN/NSX",
    ["VMware Cloud Foundation", "VCF", "VMware VCF", "Cloud Foundation"])
add("VMWARE-VVF", "VMware (Broadcom)", "vSphere Foundation (VVF)", "", "", VMW_CORE + " - being phased out per Broadcom roadmap",
    ["vSphere Foundation", "VVF", "VMware vSphere Foundation"])
add("VMWARE-VSPHERE-STD", "VMware (Broadcom)", "vSphere", "Standard", "", VMW_CORE, ["vSphere Standard", "VMware vSphere Standard", "VSPHERESTD"])
add("VMWARE-VSPHERE-ENTPLUS", "VMware (Broadcom)", "vSphere", "Enterprise Plus", "", VMW_CORE,
    ["vSphere Enterprise Plus", "VMware vSphere Enterprise Plus", "VSEP"])
add("VMWARE-VSPHERE-ESSPLUS", "VMware (Broadcom)", "vSphere", "Essentials Plus", "", "Legacy perpetual (discontinued; migrate to VVF/VCF)",
    ["vSphere Essentials Plus", "VMware vSphere Essentials Plus", "VVEP"])
add("VMWARE-VSAN", "VMware (Broadcom)", "vSAN", "", "", "Per TiB Capacity Subscription (0.25 TiB/core included with VCF)",
    ["VMware vSAN", "vSAN", "Virtual SAN"])
add("VMWARE-NSX", "VMware (Broadcom)", "NSX", "", "", "Per Core Subscription (bundled in VCF)", ["VMware NSX", "NSX-T", "NSX Data Center"])
add("VMWARE-ESXI", "VMware (Broadcom)", "ESXi Hypervisor", "", "", "Licensed via vSphere / VVF / VCF bundle", ["VMware ESXi", "ESXi", "ESX", "VMware ESX Server"])
add("VMWARE-VCENTER", "VMware (Broadcom)", "vCenter Server", "", "", "Licensed via vSphere / VVF / VCF bundle",
    ["VMware vCenter Server", "vCenter", "VCSA", "vCenter Server Appliance"])
add("VMWARE-HORIZON", "VMware (Broadcom)", "Horizon", "", "", "Per Named User or Concurrent User Subscription",
    ["VMware Horizon", "Horizon View", "Horizon Enterprise"])
add("VMWARE-WORKSTATION", "VMware (Broadcom)", "Workstation Pro", "", "", "Free for personal use since 2024; commercial requires subscription",
    ["VMware Workstation", "VMware Workstation Pro", "Workstation Pro"])
add("VMWARE-FUSION", "VMware (Broadcom)", "Fusion Pro", "", "", "Free for personal use since 2024; commercial requires subscription",
    ["VMware Fusion", "VMware Fusion Pro", "Fusion Pro"])
add("VMWARE-ARIA", "VMware (Broadcom)", "Aria (vRealize)", "", "", "Per Core or Per OSI Subscription",
    ["VMware Aria", "vRealize", "vRealize Operations", "Aria Operations", "vROps"])
add("VMWARE-TOOLS", "(Component)", "VMware Tools", "", "", "Not separately licensable (bundled guest agent)", ["VMware Tools"])
add("VMWARE-SRM", "VMware (Broadcom)", "Site Recovery Manager", "", "", "Per VM Subscription", ["VMware Site Recovery Manager", "SRM", "vCenter Site Recovery Manager"])

# ============================== RED HAT ==============================
RHEL_SP = "Per Socket-Pair Subscription (covers up to 2 sockets OR 2 virtual nodes)"
add("RHEL-SERVER-STD", "Red Hat", "Enterprise Linux Server", "Standard", "", RHEL_SP + "; Standard 8x5 support",
    ["Red Hat Enterprise Linux Server Standard", "RHEL Server Standard", "RHEL Standard"])
add("RHEL-SERVER-PREM", "Red Hat", "Enterprise Linux Server", "Premium", "", RHEL_SP + "; Premium 24x7 support",
    ["Red Hat Enterprise Linux Server Premium", "RHEL Server Premium", "RHEL Premium"])
add("RHEL-SERVER-SELF", "Red Hat", "Enterprise Linux Server", "Self-Support", "", RHEL_SP + "; no Red Hat support",
    ["Red Hat Enterprise Linux Self-Support", "RHEL Self Support"])
add("RHEL-VDC", "Red Hat", "Enterprise Linux for Virtual Datacenters", "", "", "Per Socket-Pair (UNLIMITED RHEL guests on subscribed host)",
    ["Red Hat Enterprise Linux for Virtual Datacenters", "RHEL Virtual Datacenter", "RHEL VDC"])
add("RHEL-SAP", "Red Hat", "Enterprise Linux for SAP Solutions", "", "", RHEL_SP,
    ["Red Hat Enterprise Linux for SAP Solutions", "RHEL for SAP", "RHEL SAP"])
add("RHEL-DEV", "Red Hat", "Enterprise Linux Developer Subscription", "", "", "Free (individual development use only; NOT production)",
    ["Red Hat Developer Subscription", "RHEL Developer"])
add("RHEL-HA", "Red Hat", "High Availability Add-On", "", "", "Per Socket-Pair Add-On", ["Red Hat High Availability", "RHEL HA Add-On"])
add("RHEL-RESILIENT-STORAGE", "Red Hat", "Resilient Storage Add-On", "", "", "Per Socket-Pair Add-On", ["Red Hat Resilient Storage", "Resilient Storage Add-On"])
add("RHEL-SMARTMGMT", "Red Hat", "Smart Management Add-On", "", "", "Per Managed System Add-On", ["Red Hat Smart Management", "Smart Management Add-On"])
add("RH-SATELLITE", "Red Hat", "Satellite", "", "", "Per Managed System Subscription", ["Red Hat Satellite", "Satellite Server"])
add("RH-OPENSHIFT-CORE", "Red Hat", "OpenShift Container Platform", "", "", "Per Core-Pair Subscription (Standard 8x5 or Premium 24x7)",
    ["Red Hat OpenShift", "OpenShift Container Platform", "OCP", "OpenShift"])
add("RH-OPENSHIFT-NODE", "Red Hat", "OpenShift (Bare-Metal Node)", "", "", "Per Physical Node (bare-metal only; no third-party hypervisor)",
    ["OpenShift Bare Metal Node", "OpenShift Virtualization Engine"])
add("RH-OPENSHIFT-PLATPLUS", "Red Hat", "OpenShift Platform Plus", "", "", "Per Core-Pair Subscription", ["OpenShift Platform Plus"])
add("RH-ANSIBLE", "Red Hat", "Ansible Automation Platform", "", "", "Per Managed Node Subscription",
    ["Red Hat Ansible Automation Platform", "Ansible Automation Platform", "AAP", "Ansible Tower"])
add("RH-JBOSS-EAP", "Red Hat", "JBoss Enterprise Application Platform", "", "", "Per Core-Pair or Per Socket-Pair Subscription",
    ["JBoss EAP", "Red Hat JBoss Enterprise Application Platform"])
add("RH-JBOSS-FUSE", "Red Hat", "JBoss Fuse", "", "", "Per Core-Pair Subscription", ["Red Hat JBoss Fuse", "JBoss Fuse"])
add("RH-CEPH", "Red Hat", "Ceph Storage", "", "", "Per Terabyte Subscription", ["Red Hat Ceph Storage", "Ceph Storage"])
add("RH-RHV", "Red Hat", "Virtualization (RHV)", "", "", "Per Socket-Pair Subscription (EOL 2024 - migrate to OpenShift Virtualization)",
    ["Red Hat Virtualization", "RHV", "RHEV"])

# ============================== ADOBE ==============================
for app in ["Photoshop", "Illustrator", "InDesign", "Premiere Pro", "After Effects", "Lightroom",
            "Lightroom Classic", "XD", "Animate", "Audition", "Dreamweaver", "Bridge", "Media Encoder", "Acrobat Distiller"]:
    slug = app.upper().replace(" ", "-")
    add(f"ADOBE-CC-{slug}", "Adobe", "Creative Cloud", f"{app} (Single App)", "", "Named User Subscription",
        [f"Adobe {app}", f"{app} CC", app])
add("ADOBE-CC-ALLAPPS", "Adobe", "Creative Cloud", "All Apps", "", "Named User Subscription",
    ["Adobe Creative Cloud All Apps", "Creative Cloud All Apps", "Adobe CC All Apps"])
add("ADOBE-ACROPRO-DC", "Adobe", "Acrobat", "Pro DC", "", "Named User Subscription", ["Adobe Acrobat Pro DC", "Acrobat Pro DC", "Adobe Acrobat Professional"])
add("ADOBE-ACROSTD-DC", "Adobe", "Acrobat", "Standard DC", "", "Named User Subscription", ["Adobe Acrobat Standard DC", "Acrobat Standard DC"])
add("ADOBE-ACROBAT-READER", "(Freeware)", "Adobe Acrobat Reader", "", "", "Free (no license required)",
    ["Adobe Acrobat Reader", "Acrobat Reader DC", "Adobe Acrobat Reader MUI", "Adobe Reader"])
add("ADOBE-AEM", "Adobe", "Experience Manager", "", "", "Enterprise Subscription (contract-specific)", ["Adobe Experience Manager", "AEM"])
add("ADOBE-CAPTIVATE", "Adobe", "Captivate", "", "", "Named User Subscription", ["Adobe Captivate", "Captivate"])
add("ADOBE-COLDFUSION", "Adobe", "ColdFusion", "", "", "Per Core or Per Server", ["Adobe ColdFusion", "ColdFusion"])
add("ADOBE-SIGN", "Adobe", "Acrobat Sign", "", "", "Per User or Per Transaction Subscription", ["Adobe Acrobat Sign", "Adobe Sign", "EchoSign"])
add("ADOBE-ARM", "(Component)", "Adobe Acrobat/Reader Update Component", "", "", "Not separately licensable (bundled updater)",
    ["Adobe Refresh Manager", "Adobe ARM", "Adobe Acrobat Update Service"])
add("ADOBE-LANGPACK", "(Component)", "Adobe Acrobat/Reader Language Pack", "", "", "Not separately licensable (bundled language/font component)",
    ["Extended Asian Language font pack for Adobe Acrobat Reader", "Adobe Acrobat Reader Language Pack", "Adobe Reader MUI Language Pack"])
add("ADOBE-GENUINE", "(Component)", "Adobe Genuine Software Integrity Service", "", "", "Not separately licensable (bundled service)",
    ["Adobe Genuine Software Integrity Service", "Adobe Genuine Service", "AGS"])

# ============================== SAP ==============================
for u in ["Professional User", "Limited Professional User", "Employee Self-Service User", "Developer User", "Logistics User"]:
    slug = u.upper().replace(" ", "-")
    add(f"SAP-USER-{slug}", "SAP", "ERP / S4HANA", u, "", "Named User (classification drives price - common audit gap)",
        [f"SAP {u}", f"SAP ERP {u}", f"SAP S/4HANA {u}"])
add("SAP-S4HANA-ONPREM", "SAP", "S/4HANA", "On-Premise", "", "Named User + Engine metrics", ["SAP S/4HANA", "S4HANA", "SAP S/4HANA On-Premise"])
add("SAP-S4HANA-CLOUD", "SAP", "S/4HANA Cloud", "", "", "Subscription / FUE (Full Use Equivalent)", ["SAP S/4HANA Cloud", "S4HANA Cloud"])
add("SAP-HANA-DB", "SAP", "HANA Database", "", "", "Per 64GB Memory Block or Runtime license", ["SAP HANA", "SAP HANA Database", "HANA DB"])
add("SAP-BUSINESSOBJECTS", "SAP", "BusinessObjects BI", "", "", "Named User or Concurrent Session", ["SAP BusinessObjects", "BusinessObjects BI", "SAP BO"])
add("SAP-SUCCESSFACTORS", "SAP", "SuccessFactors", "", "", "Per Employee Subscription", ["SAP SuccessFactors", "SuccessFactors"])
add("SAP-ARIBA", "SAP", "Ariba", "", "", "Subscription (spend-based or user-based)", ["SAP Ariba", "Ariba"])
add("SAP-CONCUR", "SAP", "Concur", "", "", "Per Expense Report or Per User Subscription", ["SAP Concur", "Concur"])
add("SAP-GUI", "(Component)", "SAP GUI", "", "", "Not separately licensable (client access component)", ["SAP GUI", "SAP Logon", "SAPGUI"])

# ============================== VERITAS / COHESITY ==============================
add("VERITAS-NBU-CAPACITY", "Veritas (Cohesity)", "NetBackup", "Capacity Edition", "", "Front-End Terabyte (FETB) - protected data, not backup copies",
    ["Veritas NetBackup Capacity Edition", "NetBackup Capacity Edition", "NBU Capacity"])
add("VERITAS-NBU-COMPLETE", "Veritas (Cohesity)", "NetBackup", "Complete Edition", "", "FETB Plus (workload multiplier applies)",
    ["Veritas NetBackup Complete Edition", "NetBackup Complete Edition"])
add("VERITAS-NBU-ENT", "Veritas (Cohesity)", "NetBackup", "Enterprise", "", "FETB Plus (all workloads)",
    ["Veritas NetBackup Enterprise", "NetBackup Enterprise"])
add("VERITAS-NBU-TRAD", "Veritas (Cohesity)", "NetBackup", "Traditional", "", "Per Client / Agent / Server (legacy meters)",
    ["Veritas NetBackup", "NetBackup", "NBU"])
add("VERITAS-BACKUPEXEC", "Veritas (Cohesity)", "Backup Exec", "", "", "Instance metering or Capacity metering",
    ["Veritas Backup Exec", "Backup Exec", "BE"])
add("VERITAS-INFOSCALE-STORAGE", "Veritas (Cohesity)", "InfoScale", "Storage", "", "Per Socket (physical or virtual server)",
    ["Veritas InfoScale Storage", "InfoScale Storage"])
add("VERITAS-INFOSCALE-AVAIL", "Veritas (Cohesity)", "InfoScale", "Availability", "", "Per Socket (physical or virtual server)",
    ["Veritas InfoScale Availability", "InfoScale Availability", "Veritas Cluster Server", "VCS"])
add("VERITAS-INFOSCALE-ENT", "Veritas (Cohesity)", "InfoScale", "Enterprise", "", "Per Socket (physical or virtual server)",
    ["Veritas InfoScale Enterprise", "InfoScale Enterprise", "Storage Foundation"])
add("VERITAS-ENTERPRISE-VAULT", "Veritas (Cohesity)", "Enterprise Vault", "", "", "Per User or Per Terabyte", ["Veritas Enterprise Vault", "Enterprise Vault"])
add("VERITAS-RESILIENCY", "Veritas (Cohesity)", "Resiliency Platform", "", "", "Per FETB, Per Core, or Per VM", ["Veritas Resiliency Platform", "Resiliency Platform"])

# ============================== CITRIX ==============================
add("CITRIX-CVAD-ADV", "Citrix (Cloud Software Group)", "Virtual Apps and Desktops", "Advanced", "", "Per User/Device or Concurrent User",
    ["Citrix Virtual Apps and Desktops Advanced", "CVAD Advanced", "XenApp Advanced"])
add("CITRIX-CVAD-PREM", "Citrix (Cloud Software Group)", "Virtual Apps and Desktops", "Premium", "", "Per User/Device or Concurrent User",
    ["Citrix Virtual Apps and Desktops Premium", "CVAD Premium", "XenDesktop Premium"])
add("CITRIX-DAAS", "Citrix (Cloud Software Group)", "DaaS", "", "", "Per User/Device Subscription", ["Citrix DaaS", "Citrix Cloud DaaS"])
add("CITRIX-ADC", "Citrix (Cloud Software Group)", "ADC (NetScaler)", "", "", "Per Appliance, vCPU, or Bandwidth",
    ["Citrix ADC", "NetScaler", "Citrix NetScaler", "NetScaler ADC"])
add("CITRIX-WORKSPACE-APP", "(Component)", "Citrix Workspace App", "", "", "Not separately licensable (client agent)",
    ["Citrix Workspace App", "Citrix Receiver"])
add("CITRIX-PROVISIONING", "Citrix (Cloud Software Group)", "Provisioning Services", "", "", "Per Device (included in CVAD editions)",
    ["Citrix Provisioning Services", "Citrix PVS"])

# ============================== OTHER MAJOR PUBLISHERS ==============================
add("AUTODESK-AUTOCAD", "Autodesk", "AutoCAD", "", "", "Named User Subscription (single-user or flex tokens)", ["Autodesk AutoCAD", "AutoCAD"])
add("AUTODESK-REVIT", "Autodesk", "Revit", "", "", "Named User Subscription", ["Autodesk Revit", "Revit"])
add("AUTODESK-INVENTOR", "Autodesk", "Inventor", "", "", "Named User Subscription", ["Autodesk Inventor", "Inventor Professional", "Inventor"])
add("AUTODESK-MAYA", "Autodesk", "Maya", "", "", "Named User Subscription", ["Autodesk Maya", "Maya"])
add("AUTODESK-3DSMAX", "Autodesk", "3ds Max", "", "", "Named User Subscription", ["Autodesk 3ds Max", "3ds Max"])
add("AUTODESK-CIVIL3D", "Autodesk", "Civil 3D", "", "", "Named User Subscription", ["Autodesk Civil 3D", "Civil 3D"])
add("AUTODESK-AEC", "Autodesk", "AEC Collection", "", "", "Named User Subscription (product bundle)", ["Autodesk AEC Collection", "AEC Collection", "Architecture Engineering Construction Collection"])

add("SAS-BASE", "SAS Institute", "SAS Base", "", "", "Per Core or Named User (annual license)", ["SAS Base", "Base SAS"])
add("SAS-ANALYTICS-PRO", "SAS Institute", "SAS Analytics Pro", "", "", "Per Core or Named User", ["SAS Analytics Pro"])
add("SAS-VIYA", "SAS Institute", "SAS Viya", "", "", "Per Core Subscription", ["SAS Viya", "Viya"])
add("SAS-EG", "SAS Institute", "SAS Enterprise Guide", "", "", "Included with SAS platform license", ["SAS Enterprise Guide", "Enterprise Guide"])

add("MATHWORKS-MATLAB", "MathWorks", "MATLAB", "", "", "Named User, Concurrent (network), or Campus-Wide", ["MathWorks MATLAB", "MATLAB"])
add("MATHWORKS-SIMULINK", "MathWorks", "Simulink", "", "", "Named User or Concurrent (network)", ["MathWorks Simulink", "Simulink"])

add("ANSYS-MECHANICAL", "ANSYS", "Mechanical", "", "", "Per Task (lease/paid-up) or HPC Pack", ["ANSYS Mechanical", "Ansys Mechanical"])
add("ANSYS-FLUENT", "ANSYS", "Fluent", "", "", "Per Task (lease/paid-up) or HPC Pack", ["ANSYS Fluent", "Ansys Fluent"])

add("DASSAULT-SOLIDWORKS", "Dassault Systèmes", "SOLIDWORKS", "", "", "Standalone (per seat) or Network (floating)", ["SOLIDWORKS", "SolidWorks"])
add("DASSAULT-CATIA", "Dassault Systèmes", "CATIA", "", "", "Per Seat or Token", ["CATIA", "Dassault CATIA"])

add("PTC-CREO", "PTC", "Creo", "", "", "Named User or Floating Subscription", ["PTC Creo", "Creo Parametric", "Creo"])
add("PTC-WINDCHILL", "PTC", "Windchill", "", "", "Named User Subscription", ["PTC Windchill", "Windchill"])

add("SIEMENS-NX", "Siemens", "NX", "", "", "Named User or Floating (token)", ["Siemens NX", "NX", "Unigraphics NX"])
add("SIEMENS-TEAMCENTER", "Siemens", "Teamcenter", "", "", "Named User Subscription", ["Siemens Teamcenter", "Teamcenter"])

add("ATLASSIAN-JIRA-DC", "Atlassian", "Jira Software", "Data Center", "", "Per User Tier Subscription", ["Jira Software Data Center", "Jira Data Center"])
add("ATLASSIAN-JIRA-CLOUD", "Atlassian", "Jira Software", "Cloud", "", "Per User Subscription", ["Jira Software Cloud", "Jira Software", "Jira"])
add("ATLASSIAN-CONFLUENCE-DC", "Atlassian", "Confluence", "Data Center", "", "Per User Tier Subscription", ["Confluence Data Center"])
add("ATLASSIAN-CONFLUENCE-CLOUD", "Atlassian", "Confluence", "Cloud", "", "Per User Subscription", ["Confluence Cloud", "Confluence"])
add("ATLASSIAN-BITBUCKET", "Atlassian", "Bitbucket", "", "", "Per User Subscription", ["Bitbucket", "Atlassian Bitbucket"])

add("SALESFORCE-SALES", "Salesforce", "Sales Cloud", "", "", "Per User Subscription (edition-tiered)", ["Salesforce Sales Cloud", "Sales Cloud"])
add("SALESFORCE-SERVICE", "Salesforce", "Service Cloud", "", "", "Per User Subscription (edition-tiered)", ["Salesforce Service Cloud", "Service Cloud"])
add("SERVICENOW-ITSM", "ServiceNow", "ITSM", "", "", "Per Fulfiller User Subscription", ["ServiceNow ITSM", "ServiceNow IT Service Management"])
add("SERVICENOW-SAM", "ServiceNow", "SAM Pro", "", "", "Per Managed Asset Subscription", ["ServiceNow SAM Pro", "ServiceNow Software Asset Management"])

add("SPLUNK-ENT", "Splunk (Cisco)", "Splunk Enterprise", "", "", "Per Daily Ingest Volume (GB/day) or Workload (SVC)", ["Splunk Enterprise", "Splunk"])
add("ELASTIC-ES", "Elastic", "Elasticsearch", "", "", "Per Node or Resource Unit Subscription", ["Elasticsearch", "Elastic Stack", "ELK"])
add("TABLEAU-DESKTOP", "Salesforce (Tableau)", "Tableau Desktop", "", "", "Creator Named User Subscription", ["Tableau Desktop", "Tableau"])
add("TABLEAU-SERVER", "Salesforce (Tableau)", "Tableau Server", "", "", "Creator/Explorer/Viewer Named User or Core", ["Tableau Server"])
add("QLIK-SENSE", "Qlik", "Qlik Sense", "", "", "Per User or Capacity Subscription", ["Qlik Sense", "QlikSense"])
add("ALTERYX-DESIGNER", "Alteryx", "Designer", "", "", "Named User Subscription", ["Alteryx Designer", "Alteryx"])

add("JETBRAINS-INTELLIJ", "JetBrains", "IntelliJ IDEA", "Ultimate", "", "Per User Subscription", ["IntelliJ IDEA Ultimate", "IntelliJ IDEA", "IntelliJ"])
add("JETBRAINS-PYCHARM", "JetBrains", "PyCharm", "Professional", "", "Per User Subscription", ["PyCharm Professional", "PyCharm"])
add("GITLAB-PREMIUM", "GitLab", "GitLab", "Premium", "", "Per User Subscription", ["GitLab Premium"])
add("GITLAB-ULTIMATE", "GitLab", "GitLab", "Ultimate", "", "Per User Subscription", ["GitLab Ultimate"])
add("GITHUB-ENT", "Microsoft (GitHub)", "GitHub Enterprise", "", "", "Per User Subscription", ["GitHub Enterprise", "GitHub Enterprise Server"])
add("HASHICORP-TERRAFORM", "HashiCorp (IBM)", "Terraform", "Enterprise", "", "Per Workspace or Resource Under Management", ["Terraform Enterprise", "HashiCorp Terraform"])
add("HASHICORP-VAULT", "HashiCorp (IBM)", "Vault", "Enterprise", "", "Per Client or Node Subscription", ["Vault Enterprise", "HashiCorp Vault"])

add("VEEAM-BR", "Veeam", "Backup & Replication", "", "", "Per Instance (VUL) or Per Socket (legacy)", ["Veeam Backup & Replication", "Veeam Backup and Replication", "VBR"])
add("VEEAM-ONE", "Veeam", "ONE", "", "", "Per Instance (VUL)", ["Veeam ONE"])
add("COMMVAULT-COMPLETE", "Commvault", "Complete Backup & Recovery", "", "", "Per Front-End Terabyte or Per VM", ["Commvault Complete", "Commvault Backup", "Commvault"])

add("SOPHOS-ENDPOINT", "Sophos", "Intercept X Endpoint", "", "", "Per User or Per Device Subscription", ["Sophos Intercept X", "Sophos Endpoint"])
add("CROWDSTRIKE-FALCON", "CrowdStrike", "Falcon", "", "", "Per Endpoint Subscription", ["CrowdStrike Falcon", "Falcon Sensor"])
add("TRENDMICRO-APEX", "Trend Micro", "Apex One", "", "", "Per User or Per Device Subscription", ["Trend Micro Apex One", "Apex One", "OfficeScan"])
add("SYMANTEC-SEP", "Broadcom (Symantec)", "Endpoint Protection", "", "", "Per Endpoint Subscription", ["Symantec Endpoint Protection", "SEP"])
add("MCAFEE-ENDPOINT", "Trellix (McAfee)", "Endpoint Security", "", "", "Per Node Subscription", ["McAfee Endpoint Security", "Trellix Endpoint Security", "McAfee ENS"])

add("SNOWFLAKE-DW", "Snowflake", "Data Cloud", "", "", "Consumption-based (credits)", ["Snowflake", "Snowflake Data Cloud"])
add("MONGODB-ENT", "MongoDB", "Enterprise Advanced", "", "", "Per Server or Per Core Subscription", ["MongoDB Enterprise Advanced", "MongoDB Enterprise"])
add("POSTGRESQL", "(Open Source)", "PostgreSQL", "", "", "Free (PostgreSQL License; no license required)", ["PostgreSQL", "Postgres"])
add("APACHE-TOMCAT", "(Open Source)", "Apache Tomcat", "", "", "Free (Apache License 2.0)", ["Apache Tomcat", "Tomcat"])
add("APACHE-HTTPD", "(Open Source)", "Apache HTTP Server", "", "", "Free (Apache License 2.0)", ["Apache HTTP Server", "Apache2", "httpd"])
add("NGINX-OSS", "(Open Source)", "nginx", "", "", "Free (BSD-2-Clause)", ["nginx", "nginx open source"])
add("NGINX-PLUS", "F5 (NGINX)", "NGINX Plus", "", "", "Per Instance Subscription", ["NGINX Plus", "F5 NGINX Plus"])

add("ZOOM-PRO", "Zoom", "Zoom Workplace", "Pro", "", "Per Host Subscription", ["Zoom Workplace Pro", "Zoom Pro", "Zoom Meetings"])
add("SLACK-BUSINESS", "Salesforce (Slack)", "Slack", "Business+", "", "Per Active User Subscription", ["Slack Business+", "Slack"])
add("DOCUSIGN-BUSINESS", "Docusign", "eSignature", "Business Pro", "", "Per User Subscription (envelope limits)", ["DocuSign eSignature", "DocuSign"])
add("DROPBOX-BUSINESS", "Dropbox", "Business", "", "", "Per User Subscription", ["Dropbox Business", "Dropbox"])
add("BOX-BUSINESS", "Box", "Business", "", "", "Per User Subscription", ["Box Business", "Box"])

# ============================== FREEWARE / COMPONENTS ==============================
for name, aliases in [
    ("7-Zip", ["7-Zip", "7Zip", "7z"]),
    ("Notepad++", ["Notepad++", "Notepad Plus Plus"]),
    ("Google Chrome", ["Google Chrome", "Chrome"]),
    ("Mozilla Firefox", ["Mozilla Firefox", "Firefox"]),
    ("Microsoft Edge", ["Microsoft Edge", "Edge"]),
    ("VLC Media Player", ["VLC Media Player", "VLC"]),
    ("PuTTY", ["PuTTY"]),
    ("WinSCP", ["WinSCP"]),
    ("FileZilla", ["FileZilla"]),
    ("Git", ["Git", "Git for Windows"]),
    ("Python", ["Python", "Python 3"]),
    ("Node.js", ["Node.js", "NodeJS"]),
    ("Wireshark", ["Wireshark"]),
    ("Audacity", ["Audacity"]),
    ("GIMP", ["GIMP"]),
]:
    slug = "".join(c for c in name.upper() if c.isalnum())
    add(f"FREE-{slug}", "(Freeware)", name, "", "", "Free (no license required)", aliases)

for name, aliases in [
    ("Microsoft Visual C++ Redistributable", ["Microsoft Visual C++ Redistributable", "Visual C++ Redistributable", "VC++ Redistributable"]),
    (".NET Framework", [".NET Framework", "Microsoft .NET Framework", "dotnet framework"]),
    (".NET Runtime", [".NET Runtime", "Microsoft .NET Runtime", "dotnet runtime"]),
    ("Java Runtime Environment", ["Java Runtime Environment", "JRE", "Java 8 Update"]),
    ("Microsoft Update Health Tools", ["Microsoft Update Health Tools", "Update Health Tools"]),
    ("Microsoft Edge WebView2 Runtime", ["Microsoft Edge WebView2 Runtime", "WebView2 Runtime"]),
    ("Intel Driver Package", ["Intel Driver", "Intel Chipset Device Software"]),
    ("NVIDIA Graphics Driver", ["NVIDIA Graphics Driver", "NVIDIA Display Driver"]),
]:
    slug = "".join(c for c in name.upper() if c.isalnum())[:20]
    add(f"COMP-{slug}", "(Component)", name, "", "", "Not separately licensable (runtime/driver/component)", aliases)


# ============================== WRITE ==============================
seen = set()
rows = []
for r in P:
    if r[0] in seen:
        raise SystemExit(f"DUPLICATE canonical_id: {r[0]}")
    seen.add(r[0])
    rows.append(r)

with open("canonical_library.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["canonical_id", "publisher", "product_family", "edition", "version", "metric_type", "aliases"])
    w.writerows(rows)

pubs = {}
for r in rows:
    pubs[r[1]] = pubs.get(r[1], 0) + 1

print(f"Wrote canonical_library.csv: {len(rows)} products, {len(pubs)} publishers\n")
for p, n in sorted(pubs.items(), key=lambda x: -x[1]):
    print(f"  {n:4}  {p}")
