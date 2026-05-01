<p align="center">
  <img src="banner.png" />
</p>

---
 
## Overview
 
MaskMe is a lightweight, modular Python library designed to anonymize and pseudonymize data while maintaining its statistical utility.
 
In an era where data privacy is paramount (GDPR, HIPAA, Law 010), MaskMe provides a bridge between security and analytics. It allows developers to protect sensitive information across various data formats without destroying the underlying patterns needed for Data Science and Machine Learning.

---
 
## Architecture & Philosophy
 
MaskMe is built on the principle of **Format Agnosticism**. By decoupling the transformation logic from the file I/O, we ensure the library remains lightweight and infinitely adaptable.
 
- **MaskMe Core (Current):** A pure Python engine that processes standard primitives (Dictionaries, Lists).
- **MaskMe CLI (Upcoming):** A high-performance interface for bulk file processing (CSV, JSONL, Parquet) with streaming support for multi-gigabyte datasets.

---

### The Core Dilemma: Privacy vs. Utility
 
Every masking decision involves a fundamental trade-off: **the stronger the anonymization, the less useful the data becomes**. MaskMe exposes this trade-off explicitly through its strategy system, letting you choose the right balance per field.
 
```
High Privacy  ◄─────────────────────────────► High Utility
   drop     hash    redact    noise    generalize    keep
```

---
 
## Key Features
 
- **Universal Support:** Designed for Structured (tables), Semi-Structured (nested JSON), and Unstructured (raw text) data.
- **Privacy by Design:** 4 core strategies to balance anonymization and utility.
- **Context Aware:** Use the `keep` strategy to maintain sensitive analytical payloads (e.g., medical symptoms) while masking identities.
- **Dot Notation:** Easily target nested fields (e.g., `user.internal.id`).
- **Validation Suite:** Built-in analytics to measure MAE, Variance, and distribution shifts (Q-Q Plots).

---
 
## What Data Can Be Masked?
 
MaskMe is designed to protect all major categories of sensitive data defined by international privacy regulations.
 
| Category | Description | Examples |
|---|---|---|
| **PII** | Personally Identifiable Information | Name, Address, Email, SSN, Phone, Birth Date |
| **PHI** | Protected Health Information (HIPAA) | Medical Record Numbers, Diagnoses, IP Addresses, Biometrics |
| **PAN** | Primary Account Numbers (PCI DSS) | 14–16 digit credit/debit card numbers |
| **Trade Secrets** | Confidential business or military data | Formulas, Codes, Internal IDs |
 
> Privacy laws (GDPR, HIPAA, CCPA, FERPA) require that **direct identifiers** be encrypted or redacted, and **quasi-identifiers** be anonymized to prevent re-identification by combination.

---

## Masking Strategies
 
| Strategy | Action | Best for... |
|---|---|---|
| `hash` | Deterministic SHA-256 + Salt | IDs, Usernames, Keys |
| `redact` | Partial masking (`L****n`) | Emails, Names, PII |
| `noise` | Gaussian Noise addition | Salaries, Ages, Metrics |
| `generalize` | Bucketing & Hierarchies | Ages (`20-30`), Locations |
| `keep` | (Explicit Identity) | Analytical Payloads (Symptoms) |


## Getting Started
 
### Installation
 
```bash
# Clone the repository
git clone https://github.com/yourusername/maskme.git
cd maskme
pip install -e .
```

### Library Usage Example
 
MaskMe handles nested structures and preserves non-configured fields by default.
 
```python
from maskme import MaskMe
 
# 1. Define your multi-type rules
rules = {
    "user.id":       "hash",
    "user.email":    "redact",
    "metrics.salary": "noise",
    "age":           "generalize",
    "symptom":       "keep"  # Explicitly preserve important data
}
 
# 2. Your data (Structured & Semi-Structured)
data = {
    "user": {"id": "USR-123", "email": "dev@maskme.io"},
    "metrics": {"salary": 5000},
    "age": 28,
    "symptom": "Flu",
    "metadata": "system_info"  # Implicitly kept
}
 
# 3. Apply Masking
engine = MaskMe(rules)
masked = engine.mask(data)
```

**Output:**
```python
{
    "user": {"id": "a3f5c...", "email": "d**@m******.io"},
    "metrics": {"salary": 5003.7},
    "age": "20-30",
    "symptom": "Flu",          # Unchanged — keep strategy
    "metadata": "system_info"  # Unchanged — implicit passthrough
}
```
 
---
 
## Analytics & Validation
 
Don't take our word for it. MaskMe includes a validation module to ensure your masked data still makes sense for your Data Scientists.
 
```python
from maskme.analytics import plot_utility_report
 
# Generate Q-Q Plots and Variance analysis
plot_utility_report(original_df, masked_df, column="salary")
```

---
 
## Roadmap & Planned Features
 
We are actively working on expanding MaskMe into a full-scale Data Governance tool:
 
- [ ] **CLI Module:** `maskme --input data.csv --rules rules.json --output clean.csv`
- [ ] **Adapters:** Native support for S3, SQL Databases, and Parquet files.
- [ ] **Faker Integration:** Replace real names with realistic fake names.
- [ ] **Streaming I/O:** Process massive datasets with constant memory usage.
- [ ] **Format-Preserving Encryption (FPE):** Maintain string formats after encryption.

## License
 
Distributed under the MIT License. See `LICENSE` for more information.
 
---
 
*Created by **Lucien KIEMDE** — Empowering Data Privacy through Open Source.*
