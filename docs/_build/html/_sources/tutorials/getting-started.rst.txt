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

.. code-block:: python

   from maskme.strategies import noop

   value = "US-CA"
   result = noop.apply(value)
   # result: "US-CA"

Strategy: Drop
~~~~~~~~~~~~~~

**Removes the field entirely.**

Use when: The field is a direct identifier (PII) that could lead to re-identification, or if the field is unnecessary for the final dataset.

Example: Names, email addresses, phone numbers, social security numbers.

.. code-block:: python

   from maskme.strategies import drop

   value = 12345
   result = drop.apply(value)
   # result: "__DROP__"  (signals the engine to remove this field)

Strategy: Hash
~~~~~~~~~~~~~~

**Converts the value into a fixed-length hexadecimal digest.**

Use when: You need a consistent, one-way transformation (cannot be reversed).

Common use: Usernames, customer IDs when consistency is important.

Parameters:

- ``algo``: Hashing algorithm (default: ``sha256``). Can be ``sha512``, ``blake2b``, etc.
- ``salt``: Optional string mixed into the hash for extra security.

.. code-block:: python

   from maskme.strategies import hashing

   # Basic hash
   result = hashing.apply("alice@example.com")
   # result: "d6d5d09f12b3f0f1a8a2c1e3b5e7d9f2"

   # Hash with algorithm
   result = hashing.apply(
       "alice@example.com",
       algo="sha512"
   )

   # Hash with salt (recommended for production)
   result = hashing.apply(
       "alice@example.com",
       salt="my-secret-key-2026"
   )

**Important**: Same input + same salt = same output (useful for linking records), but different salt = different hash.

Strategy: Redact
~~~~~~~~~~~~~~~~

**Replaces characters with a placeholder, preserving length.**

Use when: You need to keep some information (partial numbers, patterns) while hiding the rest.

Common use: Phone numbers, credit card numbers, postal codes.

Parameters:

- ``char``: Placeholder character (default: ``*``).
- ``keep_start``: Number of characters to show at the beginning.
- ``keep_end``: Number of characters to show at the end.

.. code-block:: python

   from maskme.strategies import redaction

   # Complete redaction
   result = redaction.apply("555-0101")
   # result: "********"

   # Keep last 4 digits (credit card pattern)
   result = redaction.apply(
       "4532123456789012",
       char="X",
       keep_end=4
   )
   # result: "XXXXXXXXXXXX9012"

   # Keep first and last
   result = redaction.apply(
       "alice@example.com",
       char="*",
       keep_start=1,
       keep_end=3
   )
   # result: "a*****m.com"

Strategy: Noise
~~~~~~~~~~~~~~~

**Adds statistical noise while preserving overall distributions.**

Use when: You need to keep numbers but make individual values unrecognizable.

Common use: Purchase amounts, ages, salaries, temperatures.

Two approaches:

**Gaussian Noise** (simple noise control):

.. code-block:: python

   from maskme.strategies import noise

   # Add Gaussian noise with fixed sigma
   result = noise.apply(42, sigma=5)
   # result: 38 (or another value near 42)

**Differential Privacy (strong privacy guarantees)**:

.. code-block:: python

   # Use Gaussian mechanism for differential privacy
   result = noise.apply(
       42,
       epsilon=0.5,      # Privacy budget (smaller = more private)
       sensitivity=10,   # Max change when one person's data changes
       delta=1e-5        # Probability of breach (default)
   )
   # Adds noise calibrated to (ε, δ)-differential privacy

**When to use each**:

- **Direct sigma**: Simple noise for exploratory analysis.
- **Differential Privacy**: Strong, formal privacy guarantees (GDPR-friendly).

Strategy: Generalization
~~~~~~~~~~~~~~~~~~~~~~~~~

**Coarsens data to broader categories.**

Use when: You want to keep categories but hide specifics.

Common use: Dates (year only), locations (state instead of city), ages (age groups).

.. code-block:: python

   from maskme.strategies import generalization

   # Generalize date to year
   result = generalization.apply(
       "2024-03-15",
       method="date_year"
   )
   # result: "2024"

   # Generalize age to bracket with custom bins
   result = generalization.apply(
       28,
       bins=[0, 18, 30, 50, 100],
       method="range"
   )
   # result: "18-30"

Choosing the Right Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use this decision tree:

.. code-block:: text

   Is this field sensitive?
   ├─ No → keep
   ├─ Yes, and I need to link records → hash
   ├─ Yes, and I need some pattern → redact
   ├─ Yes, and it's numeric → noise (or generalization)
   ├─ Yes, and I don't need it → drop
   └─ Yes, and it's categorical → generalization

Part 3: Measuring Privacy and Utility
====================================


Part 4: Real-World Example
===========================

Let's put it all together with a realistic scenario:

**Scenario**: Healthcare organization wants to share patient visit data for research while protecting privacy.

**Data fields**:

- ``patient_id``: Unique identifier → ``drop``
- ``age``: Sensitive, numeric → ``generalize`` (to age brackets)
- ``postal_code``: Quasi-identifier → ``generalize`` (to state)
- ``diagnosis``: Sensitive → ``hash`` (preserve patterns for linkage)
- ``visit_date``: Quasi-identifier → ``generalize`` (year only)
- ``medication``: Not sensitive → ``keep``

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
