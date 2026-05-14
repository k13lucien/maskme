Introduction to MaskMe
======================

MaskMe is a framework for data anonymization that lets you transform sensitive datasets into privacy-compliant versions while maintaining data utility for analysis.

The Challenge
--------------

Organizations today face a critical challenge: how to unlock the value of data while protecting individual privacy. Regulations like GDPR and HIPAA demand anonymization, yet traditional approaches often destroy data utility entirely.

MaskMe solves this by providing:

- Multiple anonymization strategies to balance privacy and utility
- Support for CSV, JSON, and JSONL formats
- Privacy metrics to measure residual risk
- Production-ready CLI and Python API

Key Capabilities
----------------

Flexible Strategies
   Six built-in methods: hashing, redaction, noise injection, generalization, drop, and no-op. Mix and match per field.

Multi-Format Support
   CSV, JSON, JSONL with streaming architecture for large datasets.

Extensible
   Register custom strategies for domain-specific anonymization logic.

Privacy Analytics
   K-anonymity, L-diversity, T-closeness, and information loss metrics to quantify privacy-utility trade-offs.

Use Cases
---------

- **Healthcare**: Anonymize patient records for research while preserving clinical patterns
- **Finance**: De-identify transactions for fraud detection models
- **E-Commerce**: Mask user data in analytics while maintaining purchase trends
- **Government**: Publish open datasets with privacy guarantees
- **Machine Learning**: Create privacy-safe training datasets

Installation
------------

Install MaskMe using pip:

.. code-block:: bash

   pip install maskme

For development:

.. code-block:: bash

   git clone https://github.com/yourusername/maskme.git
   cd maskme
   pip install -e .

Quick Start
-----------

**Basic anonymization from the command line:**

.. code-block:: bash

   # Anonymize a CSV file using a configuration
   maskme --rules rules.json --input data.csv --output masked.csv

**In Python:**

.. code-block:: python

   from maskme.core.engine import MaskMe
   
   # Define anonymization rules using strategy names
   rules = {
       "email": "hash",
       "phone": "redact",
       "name": "redact"
   }
   
   # Initialize and run
   masker = MaskMe(rules, salt="my-secret-salt")
   anonymized_data = masker.mask(sensitive_data)

Next Steps
----------

* :doc:`../tutorials/getting-started` — Complete tutorial with examples
* :doc:`../how-to/custom-strategy` — Build custom anonymization logic
* :doc:`../reference/api` — Full API reference
* :doc:`../explanation/architecture` — Understand the design philosophy
