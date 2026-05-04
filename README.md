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
 
- **MaskMe Core:** A pure Python engine that processes standard primitives (Dictionaries, Lists).
- **MaskMe CLI:** A high-performance interface for bulk file processing (CSV, JSON, JSONL) with streaming support for large datasets.

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
- **Privacy by Design:** 6 core strategies to balance anonymization and utility.
- **Context Aware:** Use the `keep` strategy to maintain sensitive analytical payloads while masking identities.
- **Dot Notation:** Easily target nested fields (e.g., `user.internal.id`).
- **Validation Suite:** Built-in analytics to measure distribution shifts (Q-Q Plots).
- **Streaming I/O:** Process multi-gigabyte datasets with constant memory usage.

---

## Masking Strategies
 
| Strategy | Parameters | Best for... |
|---|---|---|
| `hash` | `algo`, `salt` | IDs, Usernames, Keys (Deterministic) |
| `redact` | `mask_char`, `visible_chars` | Emails, Names, PII |
| `noise` | `sigma`, `min_val`, `max_val`, `precision`, `seed` | Salaries, Ages, Metrics (Diff. Privacy) |
| `generalize` | `step`, `bins` | Ages (`20-30`), Locations |
| `keep` | - | Analytical Payloads (Symptoms) |
| `drop` | - | Irrelevant sensitive data |


## Getting Started
 
### Installation
 
```bash
# Clone the repository
git clone https://github.com/k13lucien/maskme
cd maskme
pip install -e .
```

### Library Usage Example
 
MaskMe handles nested structures and parameterized rules.
 
```python
from maskme import MaskMe
 
# 1. Define your multi-type rules with optional parameters
rules = {
    "user.id":       {"strategy": "hash", "algo": "sha512"},
    "user.email":    "redact",
    "metrics.salary": {"strategy": "noise", "sigma": 500, "precision": 2},
    "age":           {"strategy": "generalize", "step": 10},
    "symptom":       "keep"
}
 
# 2. Your data (Structured & Semi-Structured)
data = [
    {
        "user": {"id": "USR-123", "email": "dev@maskme.io"},
        "metrics": {"salary": 5000},
        "age": 28,
        "symptom": "Flu"
    }
]
 
# 3. Apply Masking with a global salt
engine = MaskMe(rules, salt="secret_pepper")
masked = list(engine.mask(data))
```

### CLI Usage Example

MaskMe includes a powerful CLI for bulk processing.

```bash
# Process a CSV file and output to another file
maskme --input data.csv --rules rules.json --format csv --output clean.csv

# Use piping for streaming processing
cat data.jsonl | maskme --rules rules.json --format jsonl > clean.jsonl
```

---
 
## Analytics & Validation
 
Ensure your masked data still makes sense for your Data Scientists.
 
```python
from maskme.analytics import plot_utility_report
 
# Generate Q-Q Plots and Variance analysis
plot_utility_report(original_df, masked_df, column="salary")
```

---
 
## Roadmap & Planned Features
 
We are actively working on expanding MaskMe:
 
- [ ] **Adapters:** Native support for S3, SQL Databases, and Parquet files.
- [ ] **Faker Integration:** Replace real names with realistic fake data.
- [ ] **Advanced NLP:** Entity recognition (NER) for automated PII detection in raw text.
- [ ] **Web UI:** A visual dashboard to configure rules and preview utility reports.

## Citation

If you use Maskme in your research, please cite it as:

**BibTeX:**


```bibtex
@software{kiemde2026maskme,
  author = {Kiemde, Lucien},
  title = {MaskMe: Agnostic Python library for data anonymization},
  year = {2026},
  url = {https://github.com/k13lucien/maskme},
  note = {Source code: https://github.com/k13lucien/maskme},
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


## License
 
Distributed under the MIT License. See `LICENSE` for more information.
 
---
 
*Created by **Lucien KIEMDE** — Empowering Data Privacy through Open Source.*
