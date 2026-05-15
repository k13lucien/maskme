Getting Started with MaskMe
============================

In this tutorial, you'll learn how to anonymize datasets using MaskMe. Whether you prefer a command-line tool or a Python API for custom applications, you'll see both approaches in action.

By the end, you'll understand:

- The two ways to use MaskMe (CLI vs Python API)
- How each anonymization strategy works
- How to choose the right strategy for your data
- How to measure re-identification risk and data utility

Prerequisites
-------------

MaskMe requires Python 3.9+. Install it now:

.. code-block:: bash

   pip install maskme

Verify the installation:

.. code-block:: bash

   maskme --help

Part 1: Your First Anonymization
=================================

Let's start with a simple example. Imagine you have customer data you want to anonymize:

**Sample data** (``customers.csv``):

.. code-block:: csv

   id,name,email,phone,region,purchase_count
   1,Alice Johnson,alice@example.com,555-0101,US-CA,42
   2,Bob Smith,bob@example.com,555-0102,US-NY,15
   3,Carol White,carol@example.com,555-0103,US-TX,87

Using the CLI
~~~~~~~~~~~~~

Define a rules file that specifies which strategy to apply to each field:

**Rules file** (``rules.json``):

.. code-block:: json

   {
     "id": "hash",
     "name": "drop",
     "email": "drop",
     "phone": {"strategy": "redact", "char": "X", "keep_start": 0, "keep_end": 4},
     "region": "keep",
     "purchase_count": "keep"
   }

Now run MaskMe from the command line:

.. code-block:: bash

   maskme --rules rules.json --input customers.csv --output customers_masked.csv

Inspect the result:

.. code-block:: bash

   cat customers_masked.csv

**Output:**

.. code-block:: csv

    id,phone,region,purchase_count
    6b86b273ff34fce19d6b804eff5a3f5747ada4eaa22f1d49c01e52ddb7875b4b,XXXX0101,US-CA,42
    d4735e3a265e16eee03f59718b9b5d03019c07d8b6c51f90da3a666eec13ab35,XXXX0102,US-NY,15
    4e07408562bedb8b60ce05c1decfe3ad16b72230967de01f640b7e4729b49fce,XXXX0103,US-TX,87

What happened:

- **id**: Hashed (unreadable, but consistent for the same input)
- **name**: Removed entirely (``drop``)
- **email**: Removed entirely (``drop``)
- **phone**: Last 4 digits kept, rest redacted (``keep_end: 4``)
- **region** and **purchase_count**: Left unchanged (``keep``)

Using Python API
~~~~~~~~~~~~~~~~

For developers building applications on top of MaskMe, use the Python API:

.. code-block:: python

   import csv
   from maskme import MaskMe

   # Define rules (same as the JSON file)
   rules = {
       "id": "hash",
       "name": "drop",
       "email": "drop",
       "phone": {"strategy": "redact", "char": "X", "keep_start": 0, "keep_end": 4},
       "region": "keep",
       "purchase_count": "keep"
   }

   # Load data
   with open("customers.csv", "r") as f:
       reader = csv.DictReader(f)
       records = list(reader)

   # Initialize engine
   engine = MaskMe(rules)

   # Process records
   masked_records = list(engine.mask(records))

   # Save results
   with open("customers_masked.csv", "w") as f:
       writer = csv.DictWriter(f, fieldnames=masked_records[0].keys())
       writer.writeheader()
       writer.writerows(masked_records)

**Key advantage**: You can integrate MaskMe directly into your Python applications — pipelines, data processing scripts, ML workflows, etc.

Part 2: Understanding Strategies
=================================

MaskMe provides six strategies. Each solves different privacy vs. utility trade-offs. Let's explore when to use each.

Strategy: Keep
~~~~~~~~~~~~~~

**Keeps the original value unchanged.**

Use when: The field is already public, non-sensitive, or represent key analytical dimensions.

Example: Geographic region, product category, or timestamp.

In rules file:

.. code-block:: json

   {
     "region": "keep",
     "category": "keep"
   }

**Input data:**

.. code-block:: json

   {
     "region": "US-West",
     "category": "Electronics"
   }

**Output data:**

.. code-block:: json

   {
     "region": "US-West",
     "category": "Electronics"
   }

Strategy: Drop
~~~~~~~~~~~~~~

**Removes the field entirely.**

Use when: The field is a direct identifier (PII) that could lead to re-identification, or if the field is unnecessary for the final dataset.

Example: Names, email addresses, phone numbers, social security numbers.

In rules file:

.. code-block:: json

   {
     "user_id": "drop",
     "internal_ref": "drop"
   }

**Input data:**

.. code-block:: json

   {
     "user_id": "USR-12345",
     "internal_ref": "REF-999",
     "email": "john@example.com"
   }

**Output data:**

.. code-block:: json

   {
     "email": "john@example.com"
   }

Strategy: Hash
~~~~~~~~~~~~~~

**Converts the value into a fixed-length hexadecimal digest.**

Use when: You need a consistent, one-way transformation (cannot be reversed).

Common use: Email addresses, usernames, customer IDs when consistency matters for record linking.

**Parameters:**

- ``algo``: Hashing algorithm — ``sha256`` (default), ``sha512``, ``blake2b``, etc.
- ``salt``: Recommended. Salt string for extra security. Same input + same salt = same output.

**In rules file:**

.. code-block:: json

   {
     "email": "hash",
     "customer_id": {
       "strategy": "hash",
       "salt": "my-org-secret-2026"
     },
     "diagnosis_code": {
       "strategy": "hash",
       "algo": "sha512",
       "salt": "healthcare-key"
     }
   }

**Input data:**

.. code-block:: json

   {
     "email": "alice@example.com",
     "customer_id": "CUST-5678",
     "diagnosis_code": "E11.9"
   }

**Output data:**

.. code-block:: json

   {
     "email": "2a7f8e9c3b1d5f4a6e8c9b1d3f5a7e8c",
     "customer_id": "f4d8b7a9c1e3f5d9b2a4c6e8f1a3d5b7",
     "diagnosis_code": "9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4ca1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"
   }

.. note::

   Same input + same salt = same output. This is useful for linking records across datasets.

Strategy: Redact
~~~~~~~~~~~~~~~~

**Replaces characters with a placeholder, preserving length.**

Use when: You need some visible information (like last 4 digits) while hiding the rest.

Common use: Phone numbers, credit cards, partially-visible IDs.

**Parameters:**

- ``char``: Placeholder character (default: ``*``)
- ``keep_start``: Characters to show at the beginning (default: 0)
- ``keep_end``: Characters to show at the end (default: 0)

**In rules file:**

.. code-block:: json

   {
     "phone": {
       "strategy": "redact",
       "keep_end": 4
     },
     "credit_card": {
       "strategy": "redact",
       "char": "X",
       "keep_end": 4
     },
     "email": {
       "strategy": "redact",
       "keep_start": 1,
       "keep_end": 3,
       "char": "*"
     },
     "name": "redact"
   }

**Input data:**

.. code-block:: json

   {
     "phone": "555-0101",
     "credit_card": "4532-1234-5678-90",
     "email": "alice@example.com",
     "name": "John Doe"
   }

**Output data:**

.. code-block:: json

   {
     "phone": "****0101",
     "credit_card": "XXXXXXXXXXXX90",
     "email": "a*****m.com",
     "name": "********"
   }

Strategy: Noise
~~~~~~~~~~~~~~~

**Adds statistical noise to numeric values.**

Use when: You need to keep numbers but make individual values unrecognizable while preserving statistical distributions.

Common use: Ages, salaries, purchase amounts, measurements.

**Two modes:**

1. **Direct sigma** — Simple noise with fixed standard deviation
2. **Differential Privacy** — Noise calibrated for formal privacy guarantees

**Direct Sigma Mode (simpler):**

.. code-block:: json

   {
     "age": {
       "strategy": "noise",
       "sigma": 2,
       "seed": "reproducible-2026"
     },
     "salary": {
       "strategy": "noise",
       "sigma": 5000,
       "precision": 0,
       "min_val": 20000,
       "max_val": 500000,
       "seed": "reproducible-2026"
     }
   }

**Differential Privacy Mode (stronger):**

.. code-block:: json

   {
     "salary": {
       "strategy": "noise",
       "epsilon": 1.0,
       "sensitivity": 10000,
       "delta": 1e-5,
       "min_val": 20000,
       "max_val": 500000,
       "seed": "reproducible-2026"
     }
   }

**Parameters explained:**

- ``sigma``: Standard deviation of noise. Larger = more noise = more privacy.
- ``seed``: Optional. Use the same seed to reproduce identical noise (useful for consistent anonymization across datasets).
- ``min_val``: Minimum value after noise (clip lower bound).
- ``max_val``: Maximum value after noise (clip upper bound).
- ``precision``: Round to N decimal places (0 = integer).
- ``epsilon``: Privacy budget (smaller = stronger privacy).
- ``sensitivity``: Maximum change in output when one person's data changes.
- ``delta``: Probability of privacy breach (default: 1e-5).

**Example 1: Direct Sigma Mode**

*Rules:*

.. code-block:: json

   {
     "age": {
       "strategy": "noise",
       "sigma": 2,
       "seed": "reproducible-2026"
     }
   }

*Input data:*

.. code-block:: json

   {
     "age": 45,
     "visitor_id": "V-001"
   }

*Output data (example):*

.. code-block:: json

   {
     "age": 42,
     "visitor_id": "V-001"
   }

.. note::

   Noise is random, so the same input produces different output each run. Larger ``sigma`` = more privacy but more data distortion.

**Example 2: With Clipping Bounds**

*Rules:*

.. code-block:: json

   {
     "salary": {
       "strategy": "noise",
       "sigma": 5000,
       "min_val": 20000,
       "max_val": 150000,
       "seed": "reproducible-2026"
     }
   }

*Input data:*

.. code-block:: json

   {
     "salary": 95000,
     "dept": "Engineering"
   }

*Output data (example):*

.. code-block:: json

   {
     "salary": 98234,
     "dept": "Engineering"
   }

Strategy: Generalization
~~~~~~~~~~~~~~~~~~~~~~~~~

**Coarsens data to broader categories.**

Use when: You want to keep the type of information but remove specificity.

Common use: Dates (year only), locations (state instead of city), ages (brackets).

**For numeric data (ages, scores, amounts):**

.. code-block:: json

   {
     "age": {
       "strategy": "generalize",
       "step": 10,
       "method": "range"
     },
     "score": {
       "strategy": "generalize",
       "bins": [0, 50, 70, 90, 100],
       "method": "range"
     }
   }

**For dates:**

.. code-block:: json

   {
     "birth_date": {
       "strategy": "generalize",
       "method": "date_year"
     },
     "visit_month": {
       "strategy": "generalize",
       "method": "date_month"
     }
   }

**For locations (comma-separated):**

.. code-block:: json

   {
     "full_address": {
       "strategy": "generalize",
       "depth": 1
     }
   }

**Parameters:**

- ``step``: Fixed bracket size (e.g., 10 for ages 0-10, 10-20, etc.)
- ``bins``: Custom brackets [0, 18, 30, 50, 100] → "0-18", "18-30", etc.
- ``method``: ``"range"`` (shows bracket), ``"floor"`` (lower bound only), ``"date_year"``, ``"date_month"``
- ``depth``: For locations, number of leading parts to remove

**Example 1: Numeric with Step**

*Rules:*

.. code-block:: json

   {
     "age": {
       "strategy": "generalize",
       "step": 10,
       "method": "range"
     }
   }

*Input data:*

.. code-block:: json

   {
     "age": 27,
     "name": "Alice"
   }

*Output data:*

.. code-block:: json

   {
     "age": "20-30",
     "name": "Alice"
   }

**Example 2: Custom Bins**

*Rules:*

.. code-block:: json

   {
     "score": {
       "strategy": "generalize",
       "bins": [0, 50, 70, 90, 100],
       "method": "range"
     }
   }

*Input data:*

.. code-block:: json

   {
     "score": 87,
     "student_id": "S-456"
   }

*Output data:*

.. code-block:: json

   {
     "score": "70-90",
     "student_id": "S-456"
   }

**Example 3: Dates**

*Rules:*

.. code-block:: json

   {
     "birth_date": {
       "strategy": "generalize",
       "method": "date_year"
     },
     "visit_date": {
       "strategy": "generalize",
       "method": "date_month"
     }
   }

*Input data:*

.. code-block:: json

   {
     "birth_date": "1995-06-15",
     "visit_date": "2024-03-15"
   }

*Output data:*

.. code-block:: json

   {
     "birth_date": "1995",
     "visit_date": "2024-03"
   }

**Example 4: Locations**

*Rules:*

.. code-block:: json

   {
     "full_address": {
       "strategy": "generalize",
       "depth": 1
     }
   }

*Input data:*

.. code-block:: json

   {
     "full_address": "New York,USA,Home"
   }

*Output data:*

.. code-block:: json

   {
     "full_address": "USA,Home"
   }

Choosing the Right Strategy: A Privacy-Compliance Approach
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Privacy regulations like HIPAA require a structured approach to data anonymization:**

.. code-block:: text

   STEP 1: Remove Direct Identifiers (HIPAA Requirement)
   ├─ Is it a direct identifier? (name, SSN, medical record ID, etc.)
   │  └─ YES → drop
   │  └─ NO → go to STEP 2

   STEP 2: Handle Quasi-Identifiers (Latanya Sweeney's Research)
   │
   │  Note: Deletion alone is not sufficient.
   │  Quasi-identifiers can be re-linked to external data.
   │  Example: Birthdate + zipcode can re-identify in 87% of US population
   │
   ├─ Is it a quasi-identifier? (age, zipcode, birthdate, etc.)
   │  ├─ Age/Income/Numeric → generalize (brackets) or noise
   │  ├─ Date → generalize (year/month only)
   │  ├─ Location → generalize (depth)
   │  └─ NO → go to STEP 3

   STEP 3: Preserve Analytical Payloads
   ├─ Is it analysis-critical? (medical codes, procedures, measurements)
   │  ├─ Sensitive + Need Linkage → hash (consistent transformation)
   │  ├─ Sensitive + Need Pattern → redact (partial visibility)
   │  ├─ Sensitive + Numeric → noise (with bounds)
   |  └─ Needed information → keep
   │  └─ NO → go to STEP 4

   STEP 4: Non-Sensitive Data
   └─ Not sensitive, not quasi-identifier → keep

Part 3: Measuring Privacy and Utility
====================================


Part 4: Real-World Example
===========================

Let's put it all together with a realistic scenario:

**Scenario**: Healthcare organization wants to share patient visit data for research while protecting privacy and meeting HIPAA compliance requirements.

**Field classification** (using privacy-compliance decision tree):

- ``patient_id``: Direct identifier → ``drop`` (STEP 1: Remove direct identifiers per HIPAA)
- ``age``: Quasi-identifier → ``generalize`` (STEP 2: Protect quasi-identifiers as per Latanya Sweeney's research)
- ``postal_code``: Quasi-identifier → ``generalize`` (STEP 2: Postal code + age can re-identify individuals)
- ``diagnosis``: Analytical payload → ``hash`` (STEP 3: Preserve for research while protecting identity)
- ``visit_date``: Quasi-identifier → ``generalize`` (STEP 2: Protect date information)
- ``medication``: Non-sensitive → ``keep`` (STEP 4: Analytical value without privacy risk)

**Rules file** (``healthcare_rules.json``):

.. code-block:: json

   {
     "patient_id": "drop",
     "age": {
       "strategy": "generalize",
       "step": 5,
       "method": "range"
     },
     "postal_code": {
       "strategy": "generalize",
       "depth": 2
     },
     "diagnosis": {"strategy": "hash", "salt": "healthcare-2026"},
     "visit_date": {
       "strategy": "generalize",
       "method": "date_year"
     },
     "medication": "keep"
   }

**Run anonymization**:

.. code-block:: bash

   maskme --rules healthcare_rules.json --input visits.csv --output visits_masked.csv


Next Steps
==========

Now that you understand the basics:

- **Need to build a custom strategy?** See :doc:`../how-to/custom-strategy`
- **Want to know more about each strategy?** See :doc:`../reference/strategies`
- **Building an application with MaskMe?** See :doc:`../reference/api`
- **Curious about the architecture?** See :doc:`../explanation/architecture`

Tips for Success
~~~~~~~~~~~~~~~~

1. **Start with the least-destructive strategy**: Keep > Generalize > Redact > Hash > Noise > Drop
2. **Test with a small sample first**: Verify behavior before running on production data
3. **Always measure privacy**: Don't anonymize without understanding the privacy-utility trade-off
4. **Use salt for hashing**: Makes hashes unique to your organization
5. **Document your choices**: Track which strategies you chose and why for compliance
