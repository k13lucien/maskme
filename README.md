<p align="center">
  <img src="banner.png" /><br>
  <strong>The Open Data Framework for privacy compliance</strong>
</p>

<div align="center">

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
[![Documentation](https://img.shields.io/badge/Docs-ReadTheDocs-blue?style=flat-square&logo=readthedocs)](https://maskme.readthedocs.io/en/latest/)
[![Website](https://img.shields.io/badge/Website-k13lucien.github.io%2Fmaskme-2997ff?style=flat-square)](https://k13lucien.github.io/maskme)

</div>

---

## Overview

MaskMe is a lightweight, modular Python library designed to anonymize and pseudonymize data while measuring its residual statistical utility.

In an era where data privacy is paramount (GDPR, HIPAA, Law 010), MaskMe provides a bridge between security and analytics. It allows developers to protect sensitive information across various data formats without destroying the underlying patterns needed for Data Science and Machine Learning.

---

## Architecture & Philosophy

MaskMe is built on the principle of **Format Agnosticism**. The transformation logic is fully decoupled from file I/O, keeping the library lightweight and infinitely adaptable.

```
┌─────────────────────────────────────────────────────────┐
│                        CLI                              │
│           maskme --input data.csv --rules rules.json    │
└──────────────┬──────────────────────────┬───────────────┘
               │                          │
    ┌──────────▼──────────┐   ┌───────────▼────────────┐
    │       io/           │   │       core/engine       │
    │  csv · json · jsonl │   │   MaskMe (agnostic)     │
    │  (streaming I/O)    │   │   mask(data_iterator)   │
    └─────────────────────┘   └───────────┬─────────────┘
                                          │
                              ┌───────────▼─────────────┐
                              │      strategies/         │
                              │  hash · redact · noise  │
                              │  generalize · keep · drop│
                              └─────────────────────────┘

┌─────────────────────┐       ┌─────────────────────────┐
│    analytics/       │       │       utility/           │
│  k-anonymity        │       │  Field Retention         │
│  l-diversity        │       │  Statistical Fidelity    │
│  t-closeness        │       │  Information Loss Index  │
│  → risk_report.html │       │  → utility_report.html  │
└─────────────────────┘       └─────────────────────────┘
```

### The Core Dilemma: Privacy vs. Utility

Every masking decision involves a fundamental trade-off: **the stronger the anonymization, the less useful the data becomes**. MaskMe exposes this trade-off explicitly through its strategy system, letting you choose the right balance per field.

```
High Privacy  ◄─────────────────────────────► High Utility
   drop     hash    redact    noise    generalize    keep
```

---

## Key Features

- **Format Agnostic Core:** Processes standard Python dicts — completely decoupled from file format.
- **Universal Support:** Designed for Structured (tables), Semi-Structured (nested JSON), and Unstructured (raw text) data.
- **6 Anonymization Strategies:** From full suppression to calibrated Differential Privacy noise.
- **Dot Notation:** Target any nested field with `user.address.city`.
- **Streaming I/O:** Process multi-gigabyte datasets in constant memory (CSV, JSON, JSONL).
- **Re-identification Risk Analytics:** k-anonymity, l-diversity, and t-closeness with HTML reports.
- **Data Utility Measurement:** Field retention, statistical fidelity, and Information Loss Index.
- **Differential Privacy:** Calibrated Gaussian noise via the formal (ε, δ)-DP Gaussian mechanism.
- **Extensible by Design:** Adding a new strategy, I/O format, analytic, or utility metric requires one file and one registry entry — nothing else changes.

---

## Masking Strategies

| Strategy | Parameters | Best for |
|---|---|---|
| `hash` | `algo`, `salt` | IDs, usernames, keys (deterministic) |
| `redact` | `char`, `keep_start`, `keep_end` | Emails, names, PII |
| `noise` | `sigma`, `min_val`, `max_val`, `precision`, `seed`, `epsilon`, `sensitivity`, `delta` | Salaries, ages, metrics (supports Differential Privacy) |
| `generalize` | `step`, `bins`, `depth`, `method`, `default` | Ages (`20-30`), dates (`2003`), locations |
| `keep` | — | Analytical payloads (symptoms, labels) |
| `drop` | — | Direct identifiers |

---

## Getting Started

### Installation

```bash
git clone https://github.com/k13lucien/maskme
cd maskme
pip install -e .
```

### Library Usage

```python
from maskme import MaskMe

rules = {
    "user.id":            {"strategy": "hash", "algo": "sha512"},
    "user.email":         "redact",
    "user.phone":         {"strategy": "redact", "keep_end": 4},
    "metrics.salary":     {"strategy": "noise", "sigma": 500, "precision": 2},
    "metrics.salary_dp":  {
        "strategy":    "noise",
        "epsilon":     1.0,       # ε — privacy budget
        "sensitivity": 1000.0,   # Δf — L2 sensitivity
        "delta":       1e-5,      # δ — breach probability
        "precision":   0,
    },
    "age":                {"strategy": "generalize", "step": 10},
    "birth_date":         {"strategy": "generalize", "method": "date_year"},
    "location":           {"strategy": "generalize", "depth": 1},
    "symptom":            "keep",
    "ssn":                "drop",
}

data = [
    {
        "user":    {"id": "USR-123", "email": "dev@maskme.io", "phone": "0612345678"},
        "metrics": {"salary": 5000},
        "age":     28,
        "birth_date": "1996-04-15",
        "location": "Ouagadougou, Kadiogo, Centre",
        "symptom": "Flu",
        "ssn":     "290066312345678",
    }
]

engine = MaskMe(rules, salt="secret_pepper")
masked = list(engine.mask(data))
```

### CLI Usage

```bash
# File to file (format inferred from extension)
maskme --rules rules.json --input data.csv --output clean.csv

# Streaming via pipes (explicit format required)
cat data.jsonl | maskme --rules rules.json --format jsonl > clean.jsonl

# Dry-run on first 100 records
maskme --rules rules.json --input data.csv --limit 100

# With a global salt and verbose logging
maskme --rules rules.json --input data.csv --output clean.csv --salt my-secret --verbose

# Salt from environment variable
export MASKME_SALT=my-secret
maskme --rules rules.json --input data.csv --output clean.csv
```

---

## Re-identification Risk Analytics

Validate that anonymization is sufficient to prevent re-identification using three mathematically proven models.

```python
from maskme.analytics import run, report

# Run all three models
results = run(
    records=masked_records,
    quasi_identifiers=["age", "zip_code", "gender"],
    sensitive_attr="diagnosis",
    k_threshold=3,    # every record indistinguishable from ≥ 2 others
    l_threshold=2,    # ≥ 2 distinct sensitive values per equivalence class
    t_threshold=0.2,  # EMD ≤ 0.2 between class and global distribution
)

# Generate self-contained HTML report with SVG charts
report.generate(
    results=results,
    output_path="risk_report.html",
    dataset_info={"records": len(masked_records), "source": "patients.csv"},
)
```

| Model | Reference | What it measures |
|---|---|---|
| **k-anonymity** | Samarati & Sweeney (1998) | Every record is indistinguishable from ≥ k−1 others on quasi-identifiers |
| **l-diversity** | Machanavajjhala et al. (2007) | Every equivalence class has ≥ l distinct sensitive values |
| **t-closeness** | Li, Li & Venkatasubramanian (2007) | Sensitive attribute distribution per class is within EMD ≤ t of global |

---

## Data Utility Measurement

Quantify how much analytical value is preserved after anonymization by comparing original and masked datasets.

```python
from maskme.utility import run, report

results = run(
    original=original_records,
    anonymised=masked_records,
    numerical_fields=["age", "salary"],
    categorical_fields=["gender", "zip_code", "diagnosis"],
    field_retention_threshold=0.6,
    statistical_fidelity_threshold=0.7,
    information_loss_threshold=0.5,
)

report.generate(
    results=results,
    output_path="utility_report.html",
    dataset_info={"records": len(original_records), "source": "patients.csv"},
)
```

| Metric | Score range | What it measures |
|---|---|---|
| **Field Retention** | 0 – 1 | Fraction of values unchanged, modified, or dropped per field |
| **Statistical Fidelity** | 0 – 1 | Δmean, Δstd, Spearman ρ (numerical) · TVD (categorical) |
| **Information Loss Index** | 0 – 1 (lower = better) | NMAE (numerical) · proportion changed (categorical) |

The utility score across all metrics follows the convention `score = 1 − ILI`, where `1.0` means the anonymised data is statistically identical to the original.

---

## Extending MaskMe

MaskMe is designed so that adding capabilities requires **one file and one registry entry** — no other files change.

### Add a new anonymization strategy

```python
# src/maskme/strategies/faker_name.py
from typing import Any

def apply(value: Any, **kwargs) -> str:
    """Replace a name with a realistic fake one."""
    ...
```

```python
# src/maskme/strategies/__init__.py
from maskme.strategies.faker_name import apply as _faker_name
STRATEGIES["faker_name"] = _faker_name
```

### Add a new I/O format

```python
# src/maskme/io/parquet_handler.py
class ParquetHandler:
    def read(self, stream) -> Iterable[Dict]: ...
    def write(self, records, stream) -> None: ...
```

```python
# src/maskme/io/__init__.py
IO_HANDLERS["parquet"] = ParquetHandler
```

### Add a new risk analytic or utility metric

Implement the `Analytic` / `Metric` Protocol in a new file under `analytics/metrics/` or `utility/metrics/`, then register it in the corresponding `__init__.py`. Reports and charts adapt automatically.

---

## Roadmap

- [ ] **Adapters:** Native support for S3, SQL databases, and Parquet files.
- [ ] **Faker Integration:** Replace real names with realistic synthetic data.
- [ ] **Advanced NLP:** Named Entity Recognition (NER) for automated PII detection in raw text.
- [ ] **δ-Presence:** Additional re-identification risk model.
- [ ] **ML Utility:** Measure the impact of anonymization on model performance.
- [ ] **Web UI:** Visual dashboard to configure rules and preview utility reports.
- [ ] **Parallel Processing:** `mask_parallel()` via `concurrent.futures.ProcessPoolExecutor` for large-scale datasets.

---

## Citation

If you use MaskMe in your research, please cite it as:

**BibTeX:**
```bibtex
@software{kiemde2026maskme,
  author  = {Kiemde, Lucien},
  title   = {MaskMe: Agnostic Python library for data anonymization},
  year    = {2026},
  url     = {https://github.com/k13lucien/maskme},
  note    = {Source code: https://github.com/k13lucien/maskme},
  version = {0.1.0},
  address = {Ouagadougou, Burkina Faso}
}
```

**Vancouver:**
```
Kiemde L. MaskMe: Agnostic Python library for data anonymization [Computer software]. Version 0.1.0. Ouagadougou: 2026. Available from: https://github.com/k13lucien/maskme
```

**APA:**
```
Kiemde, L. (2026). MaskMe: Agnostic Python library for data anonymization (Version 0.1.0) [Computer software]. https://github.com/k13lucien/maskme
```

**MLA:**
```
Kiemde, Lucien. "MaskMe: Agnostic Python library for data anonymization." Version 0.1.0, 2026, https://github.com/k13lucien/maskme.
```

---
## Scientific References

The architecture of **MaskMe** and its anonymization strategies are built upon established theoretical pillars in data privacy and cybersecurity research.

### 1. Core Literature
The development of the **MaskMe** was guided by the following foundational publications:

*  **Sweeney, L. (2002)**: *"k-anonymity: A model for protecting privacy"*. International Journal of Uncertainty, Fuzziness and Knowledge-Based Systems. (Foundational research for quasi-identifier generalization).
*  **Dwork, C. (2006)**: *"Differential Privacy"*. ICALP. (The theoretical basis for our Gaussian and Laplacian noise injection strategies).
*  **Machanavajjhala, A., et al. (2007)**: *"l-diversity: Privacy beyond k-anonymity"*. ACM Transactions on Knowledge Discovery from Data (TKDD).

### 2. Legal & Compliance Frameworks
**MaskMe** is engineered to help organizations align with major international and local data protection standards:

*   **Law N°010-2004/AN (Burkina Faso)**: Specifically regarding the protection of personal data within the national context.
*   **GDPR (EU 2016/679)**: Supporting principles of *Privacy by Design* and pseudonymization for cross-border data utility.
*   **HIPAA**: Standards for the de-identification of health data (Safe Harbor Method) to enable secure medical research.
---

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

*Created by **Lucien KIEMDE** — Empowering Data Privacy through Open Source.*

---

## Contributors

Thanks to everyone who has contributed to MaskMe.

<a href="https://github.com/k13lucien/maskme/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=k13lucien/maskme" alt="Contributors to k13lucien/maskme" />
</a>
