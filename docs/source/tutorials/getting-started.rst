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

MaskMe requires Python 3.8+. Install it now:

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
     "id": "drop",
     "name": "redact",
     "email": "hash",
     "phone": {"strategy": "redact", "keep_start": 0, "keep_end": 4},
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

   name,email,phone,region,purchase_count
   ****,d6d5d09f12b3f0f1a8a2c1e3b5e7d9f2,*****0101,US-CA,42
   ****,5e6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e,*****0102,US-NY,15
   ****,1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p,*****0103,US-TX,87

What happened:

- **id**: Removed entirely (``drop``)
- **name**: Completely redacted with ``*`` (``redact``)
- **email**: Hashed (unreadable, but consistent for the same input)
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
       "id": "drop",
       "name": "redact",
       "email": "hash",
       "phone": {"strategy": "redact", "keep_start": 0, "keep_end": 4},
       "region": "keep",
       "purchase_count": "keep",
   }

   # Load data
   with open("customers.csv", "r") as f:
       reader = csv.DictReader(f)
       records = list(reader)

   # Initialize engine
   masker = MaskMe(rules)

   # Process records
   masked_records = list(masker.mask(records))

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

Use when: The field is already public, non-sensitive, or needed for analysis.

Example: Geographic region, product category, or timestamp.

.. code-block:: python

   from maskme.strategies import keep

   value = "US-CA"
   result = keep.apply(value)
   # result: "US-CA"

Strategy: Drop
~~~~~~~~~~~~~~

**Removes the field entirely.**

Use when: The field is unnecessary and removing it reduces re-identification risk. IDs, internal references, or identifiers.

.. code-block:: python

   from maskme.strategies import drop

   value = 12345
   result = drop.apply(value)
   # result: "__DROP__"  (signals the engine to remove this field)

Strategy: Hash
~~~~~~~~~~~~~~

**Converts the value into a fixed-length hexadecimal digest.**

Use when: You need a consistent, one-way transformation (cannot be reversed).

Common use: Email addresses, usernames, customer IDs when consistency is important.

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
       "4532-1234-5678-9012",
       keep_end=4
   )
   # result: "****-****-****-9012"

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

**Laplace Noise** (small adjustments):

.. code-block:: python

   from maskme.strategies import noise

   # Add Laplace noise with fixed scale
   result = noise.apply(42, scale=5)
   # result: 38 (or another value near 42)

**Differential Privacy (strong privacy guarantees)**:

.. code-block:: python

   # Use Gaussian mechanism for differential privacy
   result = noise.apply(
       42,
       epsilon=0.5,    # Privacy budget (smaller = more private)
       delta=1e-5,     # Probability of breach
       sensitivity=10  # Max change when one person's data changes
   )
   # Adds noise calibrated to (ε, δ)-differential privacy

**When to use each**:

- **Laplace**: Simple, intuitive noise for exploratory analysis.
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
       method="date",
       level="year"
   )
   # result: "2024"

   # Generalize age to bracket (you need to define your brackets)
   result = generalization.apply(
       28,
       method="numeric_range",
       ranges=[[0, 18], [18, 30], [30, 50], [50, 100]]
   )
   # result: [18, 30]  (28 falls in this bracket)

Strategy: No-op (Keep)
~~~~~~~~~~~~~~~~~~~~~~

**Does nothing — value passes through unchanged.**

Use as: Default behavior or explicit "don't touch this" marker.

.. code-block:: python

   from maskme.strategies import noop

   result = noop.apply("anything")
   # result: "anything"

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

Part 3: Analytics—Measuring Privacy
====================================

After anonymizing, you should verify the privacy-utility trade-off. MaskMe includes analytics to measure:

- **K-anonymity**: How many records are indistinguishable
- **L-diversity**: How diverse are quasi-identifiers
- **T-closeness**: How close is the distribution to the original
- **Information loss**: How much data utility is lost

Running Analytics
~~~~~~~~~~~~~~~~~

.. code-block:: python

   from maskme.analytics.metrics import kanonymity, linformationloss
   from maskme.analytics.report import generate

   # Original and masked datasets
   original_records = [...]  # Your original data
   masked_records = [...]    # Your masked data

   # Compute K-anonymity
   k = kanonymity.compute(
       masked_records,
       quasi_identifiers=["region", "purchase_count"]
   )
   print(f"K-anonymity: {k}")  # Higher is better (≥5 is good)

   # Compute information loss
   loss = linformationloss.compute(original_records, masked_records)
   print(f"Information loss: {loss:.2%}")

   # Generate HTML report
   from maskme.analytics.report import generate

   generate(
       results=[...],  # AnalyticResult objects
       output_path="privacy_report.html",
       dataset_info={
           "records": len(masked_records),
           "source": "customers.csv"
       }
   )

Understanding the Metrics
~~~~~~~~~~~~~~~~~~~~~~~~~~

**K-anonymity ≥ 5** (generally acceptable):
   Each quasi-identifier combination appears at least 5 times. An attacker cannot narrow down an individual to fewer than 5 candidates.

**L-diversity ≥ 2** (good):
   For each quasi-identifier group, there are at least 2 diverse values in the sensitive attribute. Prevents attribute inference.

**T-closeness < 0.1** (good):
   Masked distribution is close to the original. Less statistical distortion.

**Information loss < 20%** (good):
   Most data utility is preserved.

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
       "method": "numeric_range",
       "ranges": [[0, 18], [18, 30], [30, 50], [50, 65], [65, 120]]
     },
     "postal_code": {
       "strategy": "generalize",
       "method": "keep_prefix",
       "prefix_length": 2
     },
     "diagnosis": {"strategy": "hash", "salt": "healthcare-2026"},
     "visit_date": {
       "strategy": "generalize",
       "method": "date",
       "level": "year"
     },
     "medication": "keep"
   }

**Run anonymization**:

.. code-block:: bash

   maskme --rules healthcare_rules.json --input visits.csv --output visits_masked.csv

**Measure privacy**:

.. code-block:: python

   from maskme.analytics.metrics import kanonymity

   # Load original and masked data
   import csv

   with open("visits.csv") as f:
       original = list(csv.DictReader(f))

   with open("visits_masked.csv") as f:
       masked = list(csv.DictReader(f))

   # Check k-anonymity on quasi-identifiers
   k = kanonymity.compute(
       masked,
       quasi_identifiers=["age", "postal_code", "visit_date"]
   )

   if k >= 5:
       print(f"✓ Privacy OK: K-anonymity = {k}")
   else:
       print(f"✗ Privacy insufficient: K-anonymity = {k} (need ≥5)")

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
